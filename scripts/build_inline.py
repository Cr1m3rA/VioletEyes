#!/usr/bin/env python3
"""Download all third-party static assets into templates/inline/.

Run once with network access; afterwards the renderer can produce
fully-offline single-file HTML reports.

Usage:
    python scripts/build_inline.py [--output-dir templates/inline]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ASSETS = {
# CSS
    "prism.css":       "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css",
    # JS — Tailwind v4 browser bundle (JIT-in-browser, ~50KB minified)
    "tailwind.js":     "https://cdn.jsdelivr.net/npm/@tailwindcss/browser/dist/index.global.min.js",
    # JS
    "alpine.js":       "https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js",
    "chart.umd.js":    "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js",
    "mermaid.js":      "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js",
    "prism.core.js":   "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-core.min.js",
    # Prism languages — keep aligned with prism_lang() in render_report.py
    "prism.clike.js":  "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-clike.min.js",
    "prism.markup.js": "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-markup.min.js",
    "prism.java.js":   "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-java.min.js",
    "prism.python.js": "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-python.min.js",
    "prism.js.js":     "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-javascript.min.js",
    "prism.ts.js":     "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-typescript.min.js",
    "prism.php.js":    "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-php.min.js",
    # PHP (and other markup-templating languages) depends on this plugin
    "prism.markup_templating.js": "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-markup-templating.min.js",
    "prism.go.js":     "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-go.min.js",
    "prism.ruby.js":   "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-ruby.min.js",
    "prism.cs.js":     "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-csharp.min.js",
    "prism.bash.js":   "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-bash.min.js",
    "prism.sql.js":    "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-sql.min.js",
    "prism.yaml.js":   "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-yaml.min.js",
    "prism.json.js":   "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-json.min.js",
    "prism.kt.js":     "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-kotlin.min.js",
}


def fetch(url: str, timeout: int = 30) -> bytes:
    req = Request(url, headers={"User-Agent": "VioletEyes-build_inline/1.0"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="templates/inline",
                        help="Where to write the inlined assets")
    parser.add_argument("--force", action="store_true",
                        help="Re-download even if file exists")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    for name, url in ASSETS.items():
        target = out_dir / name
        if target.exists() and not args.force and target.stat().st_size > 0:
            print(f"[skip] {name} (existing {target.stat().st_size} bytes)")
            continue
        try:
            data = fetch(url)
            target.write_bytes(data)
            print(f"[ok]   {name} -> {len(data):,} bytes")
        except (URLError, TimeoutError, OSError) as e:
            print(f"[FAIL] {name}: {e}", file=sys.stderr)
            failed.append(name)

    if failed:
        print(f"\n{len(failed)} asset(s) failed: {failed}", file=sys.stderr)
        return 1
    print(f"\nAll {len(ASSETS)} assets ready under {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())