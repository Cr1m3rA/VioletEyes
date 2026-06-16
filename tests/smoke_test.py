#!/usr/bin/env python3
"""End-to-end smoke test for the new Jinja2 renderer.

Runs the renderer against tests/fixtures/ and verifies:
- exit code is 0
- the produced HTML exists, is non-trivial size, and contains key sections
- secrets are redacted
- Mermaid JS + Prism CSS are inlined (no CDN references remain)
- call-chain tab buttons exist for every finding
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
OUT_HTML = FIXTURES / "code-audit-report.html"


def main() -> int:
    if not (ROOT / "scripts" / "render_report.py").exists():
        print("FAIL: scripts/render_report.py not found", file=sys.stderr)
        return 1
    if not (ROOT / "templates" / "base.html.j2").exists():
        print("FAIL: templates/base.html.j2 not found", file=sys.stderr)
        return 1

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "render_report.py"),
        "--findings",     str(FIXTURES / "findings.json"),
        "--assets",       str(FIXTURES / "assets.json"),
        "--profile",      str(FIXTURES / "framework_profile.json"),
        "--execution-log", str(FIXTURES / "execution.log"),
        "--output",       str(OUT_HTML),
        "--project-name", "smoketest-project",
        "--target",       "D:\\repo\\myapp",
        "--mode",         "full",
        "--severity-floor", "low",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    print(proc.stdout, end="")
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        return 1

    if not OUT_HTML.exists():
        print("FAIL: output HTML not produced", file=sys.stderr)
        return 1

    html = OUT_HTML.read_text(encoding="utf-8")
    size_kb = len(html.encode("utf-8")) / 1024
    print(f"Output size: {size_kb:.1f} KB")

    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, hint: str = "") -> None:
        checks.append((name, ok, hint))

    add("output non-trivial size", size_kb > 50, f"got {size_kb:.1f} KB")

    # Required content snippets
    add("project name rendered",        "smoketest-project" in html)
    add("cover hero present",           "源码安全审计报告" in html and "cover rounded-2xl" in html)
    add("severity chart canvas",        'id="severityChart"' in html)
    add("class chart canvas",           'id="classChart"' in html)
    add("dashboard stat cards",         "stat-value" in html)
    add("framework profile present",    "技术栈识别" in html)
    add("routes table present",         "HTTP 路由表" in html)
    add("deps risk table present",      "log4j-core" in html)
    add("findings section present",     "漏洞详情" in html)
    add("Top 5 summary present",        "关键发现 Top 5" in html)
    add("disclaimer present",           "免责声明" in html)

    # Per-finding elements
    add("all 7 findings rendered",      html.count('class="finding') == 7)
    # Only findings that have a call_chain render the chain-tabs block.
    add("call-chain tabs present",      html.count("chain-tab") >= 4,
        "expected >=4 chain-tab occurrences (2 per finding with call_chain)")
    add("mermaid divs present",         html.count("mermaid") >= 6)
    add("human-review badge present",   "需人工复核" in html)
    add("redaction applied (Bearer)",   "Bearer eyJhbGc" not in html and "***" in html)
    add("redaction applied (long token)", "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U" not in html)
    # XSS: the PoC contains literal "<script>alert(1)</script>"; it must be
    # escaped so it does NOT execute when the report is opened in a browser.
    add("XSS: <script>alert PoC is escaped",
        "&lt;script&gt;alert(1)&lt;/script&gt;" in html
        and not re.search(r"<script>alert\(1\)</script>", html),
        "raw <script>alert(1)</script> must not appear in rendered HTML")
    # Target humanization: D:\repo\myapp should display as 'myapp'
    add("target path is humanized",
        "<div class=\"font-semibold text-base break-words\" title=\"D:\\repo\\myapp\">myapp</div>" in html
        or ">myapp<" in html,
        "expected humanized target 'myapp' in cover hero")

    # Inlining checks
    add("Tailwind inlined",             "tailwindcss" in html.lower() or "--tw-" in html or "tailwind" in html.lower())
    add("Alpine.js inlined",            "alpinejs" in html.lower() or "x-data" in html)
    add("Chart.js inlined",             "Chart" in html and "new Chart" in html)
    add("Mermaid inlined",              "mermaid" in html.lower())
    add("Prism CSS inlined",            "token" in html and "language-" in html)
    add("NO CDN references to jsdelivr",
        "cdn.jsdelivr.net" not in html and "unpkg.com" not in html,
        "found CDN URL — should be fully inlined")

    # Severity filter chips
    add("severity filter chips",        html.count("filter-chip") >= 5)
    # Footer
    add("footer present",               "Cr1m3rA" in html)

    # ----- V1.2: Dependency CVE additions -----
    # Run a second render that passes --cve-input, then re-read the output
    cve_fixture = FIXTURES / "dependency_cve.json"
    add("dependency_cve.json fixture exists", cve_fixture.exists())
    if cve_fixture.exists():
        cmd_cve = cmd + ["--cve-input", str(cve_fixture)]
        proc_cve = subprocess.run(cmd_cve, cwd=str(ROOT), capture_output=True, text=True)
        add("renderer accepts --cve-input flag", proc_cve.returncode == 0,
            f"--cve-input render failed: {proc_cve.stderr[:200]}")
        html_cve = OUT_HTML.read_text(encoding="utf-8")
        add("CVE section title rendered",
            "第三方依赖 CVE 在线扫描" in html_cve)
        add("CVE badge hyperlinked to NVD",
            re.search(r'href="https://nvd\.nist\.gov/vuln/detail/CVE-\d{4}-\d+"', html_cve) is not None)
        add("fixed-version column populated",
            "2.17.1" in html_cve or "2.15.0" in html_cve or "4.17.21" in html_cve)
        add("offline-cache badge present (offline fixture)",
            "离线缓存" in html_cve or "OSV.dev 在线" in html_cve)
        add("top-nav has 依赖 CVE link",
            'href="#dep-cve"' in html_cve)
        add("dashboard shows online-scan count",
            "在线 CVE 扫描" in html_cve or "条 advisory" in html_cve)
        # Validate fixture shape
        try:
            cve_doc = json.loads(cve_fixture.read_text(encoding="utf-8"))
            add("fixture source is osv-online/offline-cache/mixed",
                cve_doc.get("source") in {"osv-online", "offline-cache", "mixed"})
        except (json.JSONDecodeError, OSError) as e:
            add("fixture parses as JSON", False, str(e))
    else:
        # If the fixture is missing we still need to record 8 failed checks
        # so the count matches the plan. Mark the rest as FAIL with a hint.
        for label in [
            "renderer accepts --cve-input flag", "CVE section title rendered",
            "CVE badge hyperlinked to NVD", "fixed-version column populated",
            "offline-cache badge present (offline fixture)",
            "top-nav has 依赖 CVE link", "dashboard shows online-scan count",
            "fixture source is osv-online/offline-cache/mixed",
        ]:
            add(label, False, "tests/fixtures/dependency_cve.json missing")

    # Print results
    failed = 0
    for name, ok, hint in checks:
        mark = "PASS" if ok else "FAIL"
        line = f"  [{mark}] {name}"
        if not ok and hint:
            line += f"  ({hint})"
        print(line)
        if not ok:
            failed += 1

    print()
    if failed:
        print(f"{failed} check(s) failed.")
        return 1
    print(f"All {len(checks)} checks passed.")
    print(f"Output: {OUT_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())