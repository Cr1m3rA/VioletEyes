#!/usr/bin/env python3
"""
VioletEyes — Build Offline CVE Cache (V1.2, maintainer-only)

Re-populates ``payloads/vulnerable-ranges.json`` from OSV.dev for a list of
seed packages. This script is run by the Skill maintainer (CI / cron),
NEVER by the Agent at audit time. The Agent uses ``scripts/cve_lookup.py``
which reads the cache and may refresh individual entries online.

Usage:
    python3 scripts/build_cve_cache.py \\
        [--seeds scripts/seed_packages.json] \\
        [--cache payloads/vulnerable-ranges.json] \\
        [--rate 6] [--timeout 10] \\
        [--progress] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Reuse the OSV query + normalization from cve_lookup
_THIS_DIR = Path(__file__).resolve().parent
import importlib.util
_spec = importlib.util.spec_from_file_location("cve_lookup", _THIS_DIR / "cve_lookup.py")
_cve_lookup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cve_lookup)


def main() -> int:
    p = argparse.ArgumentParser(description="VioletEyes — Build Offline CVE Cache")
    p.add_argument("--seeds", default=str(_THIS_DIR / "seed_packages.json"))
    p.add_argument("--cache", default=str(_THIS_DIR.parent / "payloads" / "vulnerable-ranges.json"))
    p.add_argument("--rate", type=int, default=6, help="Max concurrent OSV requests")
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--progress", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    seeds_path = Path(args.seeds)
    if not seeds_path.exists():
        print(f"[ERR] seeds file not found: {seeds_path}", file=sys.stderr)
        return 1

    seeds = json.loads(seeds_path.read_text(encoding="utf-8"))
    pkgs = seeds.get("packages") or []
    if not pkgs:
        print(f"[ERR] no packages in {seeds_path}", file=sys.stderr)
        return 1

    # Load existing cache (preserve entries we don't touch)
    cache_path = Path(args.cache)
    existing_cache: dict = {}
    if cache_path.exists():
        try:
            existing_cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing_cache = {}

    existing_advisories = existing_cache.get("advisories", {}) if isinstance(existing_cache, dict) else {}

    rate = max(1, min(10, args.rate))
    now_iso = datetime.now(timezone.utc).isoformat()

    new_count = 0
    total = len(pkgs)

    def fetch_one(pkg: dict) -> tuple:
        eco = pkg["ecosystem"]
        name = pkg["name"]
        ver = pkg["version"]
        key = _cve_lookup.cache_key(eco, name, ver)
        raw = _cve_lookup.osv_query(eco, name, ver, timeout=args.timeout)
        if raw is None:
            return key, [], "failed"
        advs = [_cve_lookup.normalize_osv_vuln(v) for v in raw]
        return key, advs, "ok"

    print(f"[INFO] refreshing cache for {total} packages (rate={rate})")
    with ThreadPoolExecutor(max_workers=rate) as ex:
        futures = {ex.submit(fetch_one, pkg): pkg for pkg in pkgs}
        done = 0
        for fut in as_completed(futures):
            done += 1
            key, advs, status = fut.result()
            if status == "ok" and advs:
                existing_advisories[key] = {
                    "matched_at": now_iso,
                    "advisories": advs,
                }
                new_count += len(advs)
            if args.progress:
                print(f"[{done}/{total}] {key}: {len(advs)} advisories ({status})", file=sys.stderr)

    out = {
        "schema_version": "1.0.0",
        "generated_at": now_iso,
        "source": "osv.dev (build_cve_cache.py)",
        "advisories": existing_advisories,
    }

    if args.dry_run:
        print(f"[DRY-RUN] would write {new_count} advisories to {cache_path}")
    else:
        cache_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        size_kb = cache_path.stat().st_size / 1024
        print(f"[OK] wrote {cache_path} ({size_kb:.1f} KB, {len(existing_advisories)} keys, "
              f"{new_count} new advisories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
