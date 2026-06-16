#!/usr/bin/env python3
"""
VioletEyes — Dependency CVE Lookup (V1.2)

Reads ``third_party_deps.json`` (produced by ``framework_detect.py
--emit-deps-json``) and looks up public advisories for every package using
**OSV.dev** as the primary source (free, no auth, broad ecosystem coverage).
If the network is unavailable, falls back to the offline mirror at
``payloads/vulnerable-ranges.json``.

Outputs:
  - ``dependency_cve.json`` — full structured report (matches
    ``templates/dependency_cve.schema.json``)
  - optionally appends Critical/High CVE findings to ``findings.json``
    using the existing ``finding-schema.json`` shape (vuln_class =
    "dangerous-deps" / "log4shell" / "spring4shell").

Usage:
    python3 scripts/cve_lookup.py <repo_root> \\
        [--deps-json <path>]        # from framework_detect --emit-deps-json
        [--output dependency_cve.json]
        [--findings findings.json]   # optional: append findings
        [--min-severity High]        # finding promotion floor (Low/Medium/High/Critical)
        [--cache payloads/vulnerable-ranges.json]
        [--online | --offline]       # mode (default: auto)
        [--refresh-cache]            # write back newly fetched entries
        [--rate 4] [--timeout 8]
        [--ecosystem npm,Maven]      # filter
        [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import sibling modules without requiring a package layout
import importlib.util

_THIS_DIR = Path(__file__).resolve().parent


def _import_sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, _THIS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ecosystems_mod = _import_sibling("ecosystems")
_parsers_mod = _import_sibling("manifest_parsers")
# Expose parse_manifest / collect_dependencies at module top-level so the
# inline dispatcher in main() can call them without prefix noise.
collect_dependencies = _parsers_mod.collect_dependencies
parse_manifest = _parsers_mod.parse_manifest

OSV_QUERY_URL = _ecosystems_mod.OSV_QUERY_URL
NVD_VULN_URL  = "https://nvd.nist.gov/vuln/detail/{cve}"


# ---------------------------------------------------------------------------
# Severity bucketing
# ---------------------------------------------------------------------------

SEVERITY_FROM_CVSS = [
    (9.0, "Critical"),
    (7.0, "High"),
    (4.0, "Medium"),
    (0.1, "Low"),
    (0.0, "Unknown"),
]


def cvss_to_severity(score: Optional[float]) -> str:
    if score is None:
        return "Unknown"
    for threshold, label in SEVERITY_FROM_CVSS:
        if score >= threshold:
            return label
    return "Unknown"


SEVERITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Unknown": 4}


# ---------------------------------------------------------------------------
# Offline cache I/O
# ---------------------------------------------------------------------------

def load_cache(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def cache_key(ecosystem: str, name: str, version: str) -> str:
    """Stable lookup key. PyPI + npm names lowercased; others preserved."""
    if ecosystem in ("PyPI", "npm"):
        return f"{ecosystem}:{name.lower()}:{version}"
    return f"{ecosystem}:{name}:{version}"


def lookup_offline(cache: Dict, ecosystem: str, name: str, version: str) -> Tuple[List[Dict], int]:
    """Return (advisories, queries_cached_increment)."""
    key = cache_key(ecosystem, name, version)
    entry = cache.get("advisories", {}).get(key)
    if not entry:
        return [], 0
    out = []
    for a in entry.get("advisories", []):
        adv = dict(a)
        adv["source"] = "offline-cache"
        out.append(adv)
    return out, 1


# ---------------------------------------------------------------------------
# OSV.dev online lookup
# ---------------------------------------------------------------------------

def _parse_cvss_score_from_vector(vector: str) -> Optional[float]:
    """Pull the base score from a CVSS:3.x vector string is non-trivial
    without a calculator. We only set the score when OSV gives us a number
    directly (e.g. via database_specific.cvss.score). For vectors without
    a numeric score we return None."""
    return None


def _parse_cvss_vector(severity_list: List[Dict]) -> Tuple[Optional[float], Optional[str]]:
    """Extract a (score, vector) tuple from OSV's severity[] array."""
    if not severity_list:
        return None, None
    # Prefer database_specific.cvss.score if present (OSV adds this for
    # vulnerabilities where NVD/GHSA provides a numeric score).
    score: Optional[float] = None
    vector: Optional[str] = None
    for entry in severity_list:
        s = entry.get("score")
        t = entry.get("type", "")
        if not s:
            continue
        if t == "CVSS_V3" or s.startswith("CVSS:3"):
            vector = s
            # OSV sometimes encodes the vector only (no numeric score)
            score = None  # explicit vector-only
        if t == "CVSS_V4":
            vector = s
    return score, vector


def _extract_cvss_from_db_specific(vuln: Dict) -> Optional[float]:
    db = vuln.get("database_specific") or {}
    cvss = db.get("cvss") or {}
    s = cvss.get("score")
    if isinstance(s, (int, float)):
        return float(s)
    return None


def osv_query(ecosystem: str, name: str, version: str, timeout: float = 8.0) -> Optional[List[Dict]]:
    """POST to OSV.dev and return the list of raw vulns, or None on failure."""
    body = json.dumps({
        "package": {"name": name, "ecosystem": ecosystem},
        "version": version,
    }).encode("utf-8")
    req = urllib.request.Request(
        OSV_QUERY_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "VioletEyes/1.2"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    return data.get("vulns") or []


def normalize_osv_vuln(vuln: Dict) -> Dict:
    """Map an OSV vuln object → our internal advisory shape."""
    aliases = [a for a in (vuln.get("aliases") or []) if isinstance(a, str)]
    cve = [a for a in aliases if a.startswith("CVE-")]
    ghsa = [a for a in aliases if a.startswith("GHSA-")]

    # Severity: prefer database_specific.cvss.score (a number), then the
    # GHSA severity string from database_specific, then derive from CVSS.
    db = vuln.get("database_specific") or {}
    severity_label = db.get("severity")  # GHSA's label, sometimes present
    score = _extract_cvss_from_db_specific(vuln)
    _, vector = _parse_cvss_vector(vuln.get("severity") or [])
    if score is None:
        score = _parse_cvss_score_from_vector(vector or "")
    if severity_label and severity_label in SEVERITY_RANK:
        sev = severity_label
    elif score is not None:
        sev = cvss_to_severity(score)
    elif vector:
        # No numeric score; leave severity Unknown — report will keep but
        # won't auto-promote to findings.
        sev = "Unknown"
    else:
        sev = "Unknown"

    # Affected range + fixed versions from `affected[0].ranges[0]`
    affected_range = ""
    fixed_versions: List[str] = []
    try:
        affected = (vuln.get("affected") or [])
        if affected:
            ranges = affected[0].get("ranges") or []
            if ranges:
                ev = ranges[0].get("events") or []
                parts = []
                fixes = []
                for e in ev:
                    if "introduced" in e:
                        parts.append(f">={e['introduced']}")
                    if "fixed" in e:
                        parts.append(f"<{e['fixed']}")
                        fixes.append(e["fixed"])
                    if "last_affected" in e:
                        parts.append(f"<={e['last_affected']}")
                affected_range = ", ".join(parts) if parts else ""
                fixed_versions = fixes
    except (IndexError, KeyError, TypeError):
        pass

    # First WEB reference is the canonical advisory URL
    advisory_url = ""
    for ref in (vuln.get("references") or []):
        if ref.get("type") == "WEB":
            advisory_url = ref.get("url") or ""
            break
    if not advisory_url:
        advisory_url = f"https://osv.dev/{vuln.get('id', '')}"

    # NVD URL — only if we have at least one CVE alias
    nvd_url = ""
    if cve:
        nvd_url = NVD_VULN_URL.format(cve=cve[0])
    elif advisory_url:
        nvd_url = advisory_url

    return {
        "id": vuln.get("id", ""),
        "aliases": aliases,
        "cve": cve,
        "ghsa": ghsa,
        "summary": (vuln.get("summary") or vuln.get("details") or "")[:300],
        "severity": sev,
        "cvss_score": score,
        "cvss_vector": vector,
        "affected_range": affected_range,
        "fixed_versions": fixed_versions,
        "advisory_url": advisory_url,
        "nvd_url": nvd_url,
        "published_at": vuln.get("published"),
        "source": "osv-online",
    }


# ---------------------------------------------------------------------------
# Lookup dispatch
# ---------------------------------------------------------------------------

def lookup_one(
    dep: Dict,
    cache: Dict,
    online: bool,
    timeout: float,
) -> Tuple[Dict, int, int]:
    """Return (item, cached_count_increment, failed_increment).

    ``item`` is shaped like the ``items[]`` entry in dependency_cve.schema.json.
    """
    eco = dep["ecosystem"]
    name = dep["name"]
    version = dep["version"]
    manifest = dep.get("manifest") or ""
    manifest_path = dep.get("manifest_path") or manifest

    cached_total = 0
    failed = 0
    advisories: List[Dict] = []
    src_used: Optional[str] = None

    # 1. offline lookup first
    advs, n_cached = lookup_offline(cache, eco, name, version)
    if advs:
        advisories.extend(advs)
        cached_total += n_cached
        src_used = "offline-cache"

    # 2. online lookup if requested
    if online:
        raw = osv_query(eco, name, version, timeout=timeout)
        if raw is None:
            failed = 1
        else:
            new_advs = [normalize_osv_vuln(v) for v in raw]
            # Dedup by advisory id
            seen = {a["id"] for a in advisories}
            for a in new_advs:
                if a["id"] not in seen:
                    advisories.append(a)
                    seen.add(a["id"])
            if new_advs:
                if src_used == "offline-cache":
                    src_used = "mixed"
                else:
                    src_used = "osv-online"

    # Always emit the item, even with empty advisories, so the report can
    # show "已扫描 N 个第三方依赖". Only items with advisories count for
    # queries_total, though.
    item = {
        "ecosystem": eco,
        "name": name,
        "version": version,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "ecosystem_resolved_via": "direct",
        "advisories": advisories,
    }
    return item, cached_total, failed


# ---------------------------------------------------------------------------
# Findings injection (Critical/High → findings.json)
# ---------------------------------------------------------------------------

SPECIFIC_VULN_CLASSES = {
    # Map a known advisory id pattern → more specific vuln_class
    ("GHSA", "log4shell"):     "log4shell",
    ("GHSA", "spring4shell"):  "spring4shell",
}


def derive_vuln_class(advisory: Dict) -> str:
    """Pick the most specific vuln_class available; fallback to dangerous-deps."""
    summary_lc = (advisory.get("summary") or "").lower()
    if "log4shell" in summary_lc or any("log4j" in a.lower() for a in advisory.get("aliases", [])):
        return "log4shell"
    if "spring4shell" in summary_lc or "spring shell" in summary_lc:
        return "spring4shell"
    return "dangerous-deps"


def make_finding(item: Dict, advisory: Dict, idx: int) -> Dict:
    """Build a finding that re-uses the existing finding-schema.json shape."""
    eco = item["ecosystem"]
    name = item["name"]
    version = item["version"]
    manifest = item.get("manifest") or "manifest"
    fixed_versions = advisory.get("fixed_versions") or []
    fix_summary = (
        f"升级 {eco}:{name} 至 {' / '.join(fixed_versions)}（{advisory.get('affected_range','')} 区间内存在 {advisory.get('severity','Unknown')} 风险）"
        if fixed_versions
        else f"{eco}:{name}@={version} 存在 {advisory.get('severity','Unknown')} 风险；请参照官方 advisory 升级或应用缓解措施。"
    )
    finding = {
        "id": f"FND-CVE-{idx+1:04d}",
        "title": f"{eco} {name}@{version} — {advisory.get('summary','')[:80]}".strip(),
        "severity": advisory.get("severity", "Unknown"),
        "confidence": "High",
        "cvss_score": advisory.get("cvss_score"),
        "cwe": ["CWE-1104"],   # "Use of Unmaintained Third Party Components" (rough bucket)
        "owasp_2021": "A06:2021",
        "language": _ecosystem_to_language(eco),
        "framework": "",
        "vuln_class": derive_vuln_class(advisory),
        "file_path": manifest,
        "file_line": 1,
        "description": (
            f"{eco} 包 `{name}` 版本 `{version}` 在 OSV.dev 上匹配到 "
            f"{len(advisory.get('cve') or advisory.get('aliases') or [])} 条 advisory。"
            + (f" 摘要：{advisory.get('summary','')}" if advisory.get('summary') else "")
        ),
        "business_impact": (
            f"该依赖的已知漏洞（{advisory.get('severity','Unknown')}）可能被攻击者利用，"
            f"需尽快升级或应用厂商提供的缓解措施。"
        ),
        "reproduction_steps": [
            f"在 {manifest} 中确认 {eco} 依赖 {name} 的版本为 {version}",
            f"查阅 advisory（{advisory.get('advisory_url','')}）确认受影响范围",
            f"按官方建议升级至 {' / '.join(fixed_versions) or '已修复版本'} 或应用缓解措施",
        ],
        "evidence": {
            "context_before": f"{eco}:{name}={version}",
            "context_after":  f"fixed: {' / '.join(fixed_versions) or 'see advisory'}",
        },
        "remediation": {
            "summary": fix_summary,
            "reference": advisory.get("advisory_url", advisory.get("nvd_url", "")),
        },
        "tags": ["dependency-cve", "osv"],
        "human_review": True,
        "verified_by": "framework-default",   # we don't taint-trace deps
        "discovered_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }
    # cve field — only if we have CVE aliases (avoid free-form strings)
    cve_aliases = [a for a in (advisory.get("cve") or []) if a.startswith("CVE-")]
    if cve_aliases:
        finding["cve"] = cve_aliases
    return finding


def _ecosystem_to_language(ecosystem: str) -> str:
    return {
        "Maven":    "java",
        "PyPI":     "python",
        "npm":      "javascript",
        "Go":       "go",
        "Packagist": "php",
        "RubyGems": "ruby",
        "crates.io": "rust",
        "NuGet":    "csharp",
        "Hex":      "elixir",
    }.get(ecosystem, "plaintext")


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------

def assemble_output(
    items: List[Dict],
    queries_total: int,
    queries_cached: int,
    queries_failed: int,
    online: bool = True,
) -> Dict:
    """Determine the overall ``source`` label and return the full output dict.

    Rules:
      - ``offline-cache`` — ``online=False`` was used (everything came from
        the cache, possibly with cache misses).
      - ``osv-online``    — ``online=True`` and no cache hits at all.
      - ``mixed``         — ``online=True`` and at least one cache hit.
      - ``none``          — no dependencies scanned.
    """
    if not items:
        source = "none"
    elif not online:
        source = "offline-cache"
    elif queries_cached == 0:
        source = "osv-online"
    else:
        source = "mixed"
    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "queries_total": queries_total,
        "queries_cached": queries_cached,
        "queries_failed": queries_failed,
        "items": items,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_deps(deps_json: Optional[Path], repo: Optional[Path]) -> List[Dict]:
    """Read deps from --deps-json or by invoking manifest_parsers.collect_dependencies."""
    if deps_json:
        if not deps_json.exists():
            print(f"[ERR] --deps-json not found: {deps_json}", file=sys.stderr)
            sys.exit(2)
        return json.loads(deps_json.read_text(encoding="utf-8"))
    if repo:
        return collect_dependencies(repo)
    print("[ERR] Either --deps-json or a positional <repo_root> is required.", file=sys.stderr)
    sys.exit(2)


def _detect_online(timeout: float = 3.0) -> bool:
    """Light probe: HEAD request to OSV's POST endpoint is unsupported, so
    just try a query for a well-known package (lodash 4.17.20)."""
    try:
        # OSV returns empty vulns for clean packages — we only care about
        # the round-trip succeeding.
        body = json.dumps({
            "package": {"name": "lodash", "ecosystem": "npm"},
            "version": "4.17.20",
        }).encode("utf-8")
        req = urllib.request.Request(
            OSV_QUERY_URL, data=body,
            headers={"Content-Type": "application/json", "User-Agent": "VioletEyes/1.2 (probe)"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def main() -> int:
    p = argparse.ArgumentParser(description="VioletEyes Dependency CVE Lookup")
    p.add_argument("repo_root", nargs="?", help="(optional) — required only when --deps-json is not provided")
    p.add_argument("--deps-json", default="", metavar="PATH")
    p.add_argument("--output", default="dependency_cve.json")
    p.add_argument("--findings", default="", metavar="PATH",
                   help="Append Critical/High CVE findings to this findings.json")
    p.add_argument("--cache", default="payloads/vulnerable-ranges.json")
    p.add_argument("--min-severity", default="High",
                   choices=["Low", "Medium", "High", "Critical"])
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--online", action="store_true", help="Force online mode")
    mode.add_argument("--offline", action="store_true", help="Force offline mode")
    p.add_argument("--refresh-cache", action="store_true",
                   help="Write newly fetched entries back to the offline cache")
    p.add_argument("--rate", type=int, default=4, help="Max concurrent OSV requests (default 4, max 10)")
    p.add_argument("--timeout", type=float, default=8.0, help="Per-request timeout in seconds (default 8)")
    p.add_argument("--ecosystem", default="", help="Comma-separated ecosystem filter, e.g. 'npm,Maven'")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else None
    deps_json = Path(args.deps_json).resolve() if args.deps_json else None

    cache_path = Path(args.cache).resolve() if not Path(args.cache).is_absolute() else Path(args.cache)
    cache = load_cache(cache_path)

    deps = _load_deps(deps_json, repo_root)
    if args.ecosystem:
        keep = {e.strip() for e in args.ecosystem.split(",") if e.strip()}
        deps = [d for d in deps if d.get("ecosystem") in keep]

    if not deps:
        print(f"[WARN] no dependencies to scan", file=sys.stderr)

    # Resolve mode
    if args.online:
        online = True
    elif args.offline:
        online = False
    else:
        online = _detect_online()
    print(f"[INFO] mode: {'online' if online else 'offline'}  ({len(deps)} deps to scan)")

    # Concurrent online lookups
    items: List[Dict] = []
    queries_total = 0
    queries_cached = 0
    queries_failed = 0

    rate = max(1, min(10, args.rate))

    with ThreadPoolExecutor(max_workers=rate) as ex:
        future_to_dep = {
            ex.submit(lookup_one, d, cache, online, args.timeout): d
            for d in deps
        }
        for fut in as_completed(future_to_dep):
            try:
                item, n_cached, n_failed = fut.result()
            except Exception as e:
                # Defensive: never let a worker die silently
                print(f"[WARN] worker failed: {e}", file=sys.stderr)
                continue
            queries_total += 1
            queries_cached += n_cached
            queries_failed += n_failed
            items.append(item)

    # Sort by severity (Critical first), then by ecosystem/name
    def _sort_key(it: Dict):
        worst_sev = min(
            (SEVERITY_RANK.get(a.get("severity", "Unknown"), 4) for a in it.get("advisories", [])),
            default=4,
        )
        return (worst_sev, it["ecosystem"], it["name"])

    items.sort(key=_sort_key)

    output = assemble_output(items, queries_total, queries_cached, queries_failed, online=online)

    # Optional findings injection
    if args.findings:
        floor_rank = SEVERITY_RANK.get(args.min_severity, 1)
        new_findings = []
        idx = 0
        for it in items:
            for adv in it.get("advisories", []):
                sev_rank = SEVERITY_RANK.get(adv.get("severity", "Unknown"), 4)
                if sev_rank > floor_rank:
                    continue
                new_findings.append(make_finding(it, adv, idx))
                idx += 1
        # Merge into existing findings.json (if any)
        findings_path = Path(args.findings).resolve()
        existing: List[Dict] = []
        if findings_path.exists():
            try:
                blob = json.loads(findings_path.read_text(encoding="utf-8"))
                if isinstance(blob, dict):
                    existing = blob.get("findings", []) or []
                elif isinstance(blob, list):
                    existing = blob
            except (json.JSONDecodeError, OSError):
                existing = []
        # Avoid duplicate IDs by suffixing if collision
        existing_ids = {f.get("id") for f in existing if f.get("id")}
        for nf in new_findings:
            base = nf["id"]
            n = 1
            while nf["id"] in existing_ids:
                n += 1
                nf["id"] = f"{base}-{n}"
            existing_ids.add(nf["id"])
            existing.append(nf)
        if not args.dry_run:
            findings_path.write_text(
                json.dumps({"findings": existing}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        print(f"[OK] appended {len(new_findings)} CVE finding(s) to {findings_path}")

    # Refresh-cache write-back (only the entries we newly fetched from OSV)
    if args.refresh_cache and online:
        new_cache_entries = 0
        cache_advisories = cache.setdefault("advisories", {})
        for it in items:
            key = cache_key(it["ecosystem"], it["name"], it["version"])
            existing_adv_ids = {a["id"] for a in cache_advisories.get(key, {}).get("advisories", [])}
            fresh = [a for a in it["advisories"] if a["source"] == "osv-online" and a["id"] not in existing_adv_ids]
            if fresh:
                entry = cache_advisories.setdefault(key, {"matched_at": "", "advisories": []})
                entry["matched_at"] = datetime.now(timezone.utc).isoformat()
                entry["advisories"].extend(fresh)
                new_cache_entries += len(fresh)
        if not args.dry_run and new_cache_entries:
            cache.setdefault("schema_version", "1.0.0")
            cache.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
            cache.setdefault("source", "osv.dev (refreshed)")
            cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[OK] wrote {new_cache_entries} new advisories to cache {cache_path}")

    if args.dry_run:
        print("[DRY-RUN] not writing output")
    else:
        out_path = Path(args.output).resolve()
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        size_kb = out_path.stat().st_size / 1024
        print(f"[OK] wrote {out_path} ({size_kb:.1f} KB, {len(items)} items, "
              f"{sum(len(i['advisories']) for i in items)} advisories, "
              f"source={output['source']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
