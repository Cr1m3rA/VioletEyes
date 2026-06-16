#!/usr/bin/env python3
"""
VioletEyes — Report Renderer (Jinja2 + inlined assets)

Reads findings.json / assets.json / framework_profile.json / execution.log
and renders a fully-offline single-file HTML report using the Jinja2
templates under ``templates/`` (see ``base.html.j2`` and the partials
under ``templates/partials/``).

The output HTML inlines Tailwind v4 (browser JIT), Alpine.js, Chart.js,
Mermaid, Prism + language components, so the rendered report needs no
network access.

Usage:
    python scripts/render_report.py \\
        --findings findings.json \\
        --assets assets.json \\
        --profile framework_profile.json \\
        --execution-log execution.log \\
        --output code-audit-report.html \\
        [--project-name "my-project"] \\
        [--target "/path/to/repo"] \\
        [--mode full] \\
        [--severity-floor low] \\
        [--partial] \\
        [--snippet-mode]

Backwards compatibility
-----------------------
This renderer preserves the CLI flags and JSON input contract of the
previous string-templating renderer. The output HTML structure and
``findings.json`` schema have not changed — only the visuals and the
HTML construction mechanism.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape


VERSION = "1.2-hotfix"

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Informational"]
SEVERITY_FILTERS = ["All", "Critical", "High", "Medium", "Low", "Info"]

# CVE advisory severity order — used to rank dependency_cve items
CVE_SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Unknown"]
CVE_SEVERITY_RANK = {s: i for i, s in enumerate(CVE_SEVERITY_ORDER)}

# ---------------------------------------------------------------------------
# Redaction & escaping
# ---------------------------------------------------------------------------


def redact(text: str) -> str:
    """Mask tokens, base64-ish blobs, and internal IPs."""
    if not text:
        return text
    text = re.sub(
        r"(Bearer|Basic|Token)\s+[A-Za-z0-9._\-+/=]{6,}",
        lambda m: f"{m.group(1)} {m.group(0).split()[-1][:6]}***{m.group(0).split()[-1][-4:]}",
        text,
    )
    text = re.sub(
        r"([A-Za-z0-9+/=_-]{32,})",
        lambda m: f"{m.group(0)[:6]}***{m.group(0)[-4:]}",
        text,
    )
    text = re.sub(
        r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b",
        "<internal-ip>",
        text,
    )
    return text


def prism_lang(language: str) -> str:
    """Map language identifier to Prism.js hint."""
    m = {
        "java": "java", "kotlin": "kotlin", "scala": "scala", "groovy": "groovy",
        "python": "python", "php": "php",
        "javascript": "javascript", "typescript": "typescript",
        "go": "go", "ruby": "ruby", "csharp": "csharp", "rust": "rust",
        "vue": "markup", "react": "jsx", "jsx": "jsx", "tsx": "tsx",
        "html": "markup", "css": "css", "sql": "sql",
        "yaml": "yaml", "json": "json", "toml": "yaml", "ini": "ini",
        "bash": "bash", "shell": "bash", "plaintext": "plaintext",
    }
    return m.get((language or "").lower(), "plaintext")


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def severity_counts(findings: List[Dict]) -> Dict[str, int]:
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        sev = f.get("severity", "Informational")
        if sev in counts:
            counts[sev] += 1
    return counts


def vuln_class_counts(findings: List[Dict], top: int = 10) -> List[tuple]:
    c = Counter()
    for f in findings:
        vc = f.get("vuln_class", "unknown")
        c[vc] += 1
    return c.most_common(top)


def top_findings(findings: List[Dict], n: int = 5) -> List[Dict]:
    sev_rank = {s: i for i, s in enumerate(SEVERITY_ORDER)}
    return sorted(
        findings,
        key=lambda f: (
            sev_rank.get(f.get("severity", "Informational"), 99),
            -(f.get("cvss_score") or 0),
        ),
    )[:n]


def filter_findings(findings: List[Dict], severity_floor: str) -> List[Dict]:
    floor_idx = SEVERITY_ORDER.index(severity_floor) if severity_floor in SEVERITY_ORDER else 4
    return [
        f for f in findings
        if SEVERITY_ORDER.index(f.get("severity", "Informational")) <= floor_idx
    ]


# ---------------------------------------------------------------------------
# Target normalization — turn a local path / Git URL into a clean display name
# ---------------------------------------------------------------------------


_LOCAL_PATH_RE = re.compile(r"^([A-Za-z]:[\\/]|/|[A-Za-z]:$|\\\\)")


def humanize_target(target: str) -> Tuple[str, str]:
    """Return ``(display_name, raw_target)`` from an arbitrary target string.

    The renderer always shows ``display_name`` prominently (cover hero).
    ``raw_target`` is preserved (typically shown in a smaller, secondary
    line / hover tooltip) so the engineer can still see the actual path
    or URL the audit was run against.

    Rules:
    - Git URL ``https://github.com/foo/bar(.git)`` → ``bar`` (the repo name)
    - Local path ``D:\\repo\\myapp`` / ``/home/user/myapp`` → ``myapp`` (last segment)
    - Anything else → returned as-is for both fields.
    """
    if not target:
        return ("", "")
    t = target.strip()

    # Git URL: extract repo name (last path segment, strip ".git")
    m = re.match(r"^https?://[^/]+/([^/]+)/([^/]+?)(?:\.git)?/?$", t)
    if m:
        return (m.group(2), t)

    # Local filesystem path (Windows drive, UNC, or POSIX)
    if _LOCAL_PATH_RE.match(t) or "\\" in t or "/" in t:
        # Use forward slashes for split so both separators work
        cleaned = t.rstrip("\\/").replace("\\", "/")
        last = cleaned.rsplit("/", 1)[-1]
        if last:
            return (last, t)

    return (t, t)


# ---------------------------------------------------------------------------
# Call-chain -> Mermaid
# ---------------------------------------------------------------------------


def _sanitize_mermaid_id(symbol: str, idx: int) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", symbol or f"node{idx}")
    if not s or s[0].isdigit():
        s = "n_" + s
    return f"{s}_{idx}"


def call_chain_to_mermaid(chain: List[Dict]) -> str:
    """Render a call chain as a Mermaid flowchart (top-down).

    Output is raw mermaid source (NOT pre-escaped). The Jinja template
    must mark this value ``| safe`` so autoescape doesn't mangle the
    angle brackets in ``<br/>``.
    """
    if not chain:
        return "flowchart LR\n  empty[No call chain]"
    lines = [
        "flowchart TD",
        "  classDef sinkNode fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d;",
    ]
    last_id = None
    for i, c in enumerate(chain):
        node_id = _sanitize_mermaid_id(c.get("symbol", f"node{i}"), i)
        symbol = (c.get("symbol") or "?").replace('"', "'").replace("[", "(").replace("]", ")")
        file = (c.get("file") or "?").replace('"', "'").replace("[", "(").replace("]", ")")
        line_no = c.get("line", "?")
        if i == len(chain) - 1:
            label = f"{symbol}<br/>{file}:{line_no}"
            lines.append(f'  {node_id}["{label}"]:::sinkNode')
        else:
            label = f"{symbol}<br/>{file}:{line_no}"
            lines.append(f'  {node_id}("{label}")')
        if last_id is not None:
            lines.append(f"  {last_id} --> {node_id}")
        last_id = node_id
    return "\n".join(lines)


def call_chain_to_mermaid_attr(chain: List[Dict]) -> str:
    """Same as ``call_chain_to_mermaid`` but HTML-attribute-safe.

    Produces a string safe to embed inside ``data-source="..."``: only
    ``&`` and ``"`` are escaped, newlines are preserved (HTML attribute
    values allow literal newlines). Browser-side JS will read this back
    via ``el.dataset.source`` and get the raw mermaid source.
    """
    raw = call_chain_to_mermaid(chain)
    return raw.replace("&", "&amp;").replace('"', "&quot;")


# ---------------------------------------------------------------------------
# Finding normalization (used as Jinja context)
# ---------------------------------------------------------------------------


def normalize_finding(f: Dict, idx: int) -> Dict:
    """Return a finding dict enriched with safe defaults the templates expect."""
    out = dict(f)  # shallow copy
    out.setdefault("id", f"FND-{idx+1:04d}")
    out.setdefault("severity", "Informational")
    out["prism_lang"] = prism_lang(out.get("language", ""))
    # Apply redaction to all user-supplied text fields we render
    for key in ("description", "impact", "business_impact", "attacker_capability"):
        if isinstance(out.get(key), str):
            out[key] = redact(out[key])
    if isinstance(out.get("code_snippet"), str):
        snippet = redact(out["code_snippet"])
        lines = snippet.splitlines()
        if len(lines) > 30:
            snippet = "\n".join(lines[:15] + ["  ... (truncated) ..."] + lines[-15:])
        out["code_snippet"] = snippet
    rem = out.get("remediation")
    if isinstance(rem, dict):
        rem = dict(rem)
        for key in ("code_before", "code_after", "summary"):
            if isinstance(rem.get(key), str):
                rem[key] = redact(rem[key])
        out["remediation"] = rem
    ev = out.get("evidence")
    if isinstance(ev, dict):
        ev = {k: redact(v) if isinstance(v, str) else v for k, v in ev.items()}
        out["evidence"] = ev
    return out


# ---------------------------------------------------------------------------
# Dependency CVE flattening (V1.2)
# ---------------------------------------------------------------------------


def flatten_dependency_cve(cve_data: Optional[Dict]) -> Tuple[List[Dict], int, Dict[str, int], str, int, int]:
    """Turn ``dependency_cve.json`` into Jinja-friendly vars.

    Returns ``(cve_findings, cve_findings_count, cve_by_severity,
    cve_source, cve_queries_total, cve_queries_cached)``.

    Each ``cve_findings`` row is one advisory, flattened with package-level
    context (``ecosystem``, ``name``, ``version``, ``manifest``, etc.).
    """
    if not isinstance(cve_data, dict):
        return [], 0, {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Unknown": 0}, "none", 0, 0
    items = cve_data.get("items") or []
    if not isinstance(items, list):
        items = []

    rows: List[Dict] = []
    by_sev: Dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
    for it in items:
        if not isinstance(it, dict):
            continue
        eco = it.get("ecosystem") or "—"
        name = it.get("name") or "—"
        version = it.get("version") or "—"
        manifest = it.get("manifest") or it.get("manifest_path") or "—"
        advisories = it.get("advisories") or []
        if not isinstance(advisories, list):
            advisories = []
        for adv in advisories:
            if not isinstance(adv, dict):
                continue
            sev = adv.get("severity") or "Unknown"
            if sev not in by_sev:
                sev = "Unknown"
            by_sev[sev] += 1
            cve_aliases = [a for a in (adv.get("cve") or []) if isinstance(a, str)]
            ghsa_aliases = [a for a in (adv.get("ghsa") or []) if isinstance(a, str)]
            fixed_versions = [v for v in (adv.get("fixed_versions") or []) if isinstance(v, str)]
            summary = (adv.get("summary") or "")
            # Run redact() over user-supplied summary (defense in depth)
            summary = redact(summary) if summary else ""
            rows.append({
                "ecosystem":        eco,
                "name":             name,
                "version":          version,
                "manifest":         manifest,
                "severity":         sev,
                "cvss_score":       adv.get("cvss_score"),
                "cvss_vector":      adv.get("cvss_vector") or "",
                "cve_id":           cve_aliases[0] if cve_aliases else "",
                "cve":              cve_aliases,
                "ghsa":             ghsa_aliases,
                "summary":          summary,
                "fixed_versions":   fixed_versions,
                "fixed_version":    fixed_versions[0] if fixed_versions else "—",
                "affected_range":   adv.get("affected_range") or "",
                "advisory_url":     adv.get("advisory_url") or "",
                "nvd_url":          adv.get("nvd_url") or "",
                "source":           adv.get("source") or "offline-cache",
            })

    # Sort: worst severity first, then ecosystem/name
    rows.sort(key=lambda r: (
        CVE_SEVERITY_RANK.get(r["severity"], 4),
        r["ecosystem"], r["name"], r["cve_id"],
    ))

    source = cve_data.get("source") or "none"
    if source not in ("osv-online", "offline-cache", "mixed", "none"):
        source = "none"
    q_total = int(cve_data.get("queries_total") or 0)
    q_cached = int(cve_data.get("queries_cached") or 0)
    return rows, len(rows), by_sev, source, q_total, q_cached


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def render(
    findings: List[Dict],
    assets: List[Dict],
    profile: Optional[Dict],
    execution_log: str,
    template_dir: Path,
    project_name: str,
    target: str,
    mode: str,
    severity_floor: str,
    partial: bool,
    snippet_mode: bool,
    test_date_start: str,
    test_date_end: str,
    tool_versions: Dict[str, str],
    cve_data: Optional[Dict] = None,
) -> str:
    findings = filter_findings(findings, severity_floor)

    # Robustness — assets must be a list of dicts, profile a dict
    if not isinstance(assets, list):
        assets = []
    assets = [a for a in assets if isinstance(a, dict)]
    if profile is not None and not isinstance(profile, dict):
        profile = {}
    profile = profile or {}

    # Counts & aggregates
    counts = severity_counts(findings)
    total = sum(counts.values())
    counts_dict = {
        "critical": counts["Critical"],
        "high": counts["High"],
        "medium": counts["Medium"],
        "low": counts["Low"],
        "info": counts["Informational"],
    }

    primary_language = profile.get("primary_language", "unknown")
    frameworks_list = profile.get("frameworks", []) or []
    frameworks_str = ",".join(frameworks_list) or "—"
    build_tool = profile.get("build_tool", "—")

    eps = profile.get("entry_points", []) or []
    entry_file = "—"
    entry_points = []
    if isinstance(eps, list):
        for ep in eps:
            if isinstance(ep, dict):
                entry_points.append(ep)
                if entry_file == "—":
                    entry_file = ep.get("path") or ep.get("file") or "—"
            elif isinstance(ep, str) and entry_file == "—":
                entry_file = ep

    routes = [a for a in assets if isinstance(a, dict) and a.get("type") == "http_api"]
    deps_count = profile.get("third_party_deps_count", 0)
    deps_risk = profile.get("dangerous_dependencies", []) or []
    if not isinstance(deps_risk, list):
        deps_risk = []

    # V1.2: dependency CVE lookup (flattened for Jinja)
    cve_findings, cve_findings_count, cve_by_severity, cve_source, \
        cve_queries_total, cve_queries_cached = flatten_dependency_cve(cve_data)

    total_assets = len(assets)
    tested_assets = sum(1 for a in assets if a.get("tested"))
    coverage_pct = round(tested_assets / total_assets * 100, 1) if total_assets else 0

    top = top_findings(findings, 5)
    top_list = []
    for f in top:
        loc = f.get("file_path", "")
        if f.get("file_line"):
            loc += f":{f['file_line']}"
        top_list.append({
            "id": f.get("id", ""),
            "title": f.get("title", ""),
            "severity": f.get("severity", "Informational"),
            "cvss_score": f.get("cvss_score", ""),
            "file_path": loc,
        })

    # Vuln class chart data
    vc = vuln_class_counts(findings, 10)
    class_labels = [v[0] for v in vc] or ["none"]
    class_counts = [v[1] for v in vc] or [0]

    # Findings (normalized)
    findings_norm = [normalize_finding(f, i) for i, f in enumerate(findings)]

    # Executive summary intro paragraph
    summary_intro = (
        f"本次对 <code>{target}</code> 的源码审计共发现 "
        f"<strong>{total}</strong> 个漏洞，其中 "
        f"<strong class='text-rose-600'>{counts['Critical']}</strong> 个 Critical、"
        f"<strong class='text-orange-600'>{counts['High']}</strong> 个 High、"
        f"<strong class='text-amber-600'>{counts['Medium']}</strong> 个 Medium、"
        f"<strong class='text-cyan-600'>{counts['Low']}</strong> 个 Low、"
        f"<strong class='text-slate-500'>{counts['Informational']}</strong> 个 Info。"
        f"主要语言：<code>{primary_language}</code>，框架：<code>{frameworks_str}</code>，"
        f"识别 HTTP 入口 <strong>{len(routes)}</strong> 个。"
    )

    mode_label_map = {
        "full": "Full Audit", "incremental": "Incremental", "snippet": "Snippet",
        "api-focused": "API Focused", "frontend-focused": "Frontend Focused",
        "diff": "Diff",
    }

    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml", "j2"], default=True),
        trim_blocks=False,
        lstrip_blocks=False,
    )
    env.filters["redact"] = redact

    def escape_attr(value: Any) -> str:
        """HTML attribute escape — minimal, preserves whitespace.

        Used for inline values inside ``data-*`` attributes where the JS
        side needs to recover the raw string (e.g. mermaid source code
        which legitimately contains ``<br/>``). HTML attribute values can
        legally contain newlines and other whitespace, so we keep them.
        Only ``&`` and the wrapping ``"`` need escaping.
        """
        if value is None:
            return ""
        s = str(value)
        return s.replace("&", "&amp;").replace('"', "&quot;")

    env.filters["escape_attr"] = escape_attr
    env.globals["call_chain_to_mermaid"] = call_chain_to_mermaid
    env.globals["call_chain_to_mermaid_attr"] = call_chain_to_mermaid_attr

    # Read inline assets as raw strings (NOT as templates) so the Jinja
    # parser doesn't choke on `{%` / `{{` patterns inside JS bundles.
    inline_dir = template_dir / "inline"

    def _read_inline(name: str) -> str:
        path = inline_dir / name
        if not path.exists():
            return f"/* INLINE ASSET MISSING: {name} */"
        return path.read_text(encoding="utf-8")

    inline_assets = {
        "tailwind_js": _read_inline("tailwind.js"),
        "alpine_js":   _read_inline("alpine.js"),
        "chart_js":    _read_inline("chart.umd.js"),
        "mermaid_js":  _read_inline("mermaid.js"),
        "prism_css":   _read_inline("prism.css"),
        "prism_core_js":   _read_inline("prism.core.js"),
        "prism_clike_js":  _read_inline("prism.clike.js"),
        "prism_markup_js": _read_inline("prism.markup.js"),
        "prism_java_js":   _read_inline("prism.java.js"),
        "prism_python_js": _read_inline("prism.python.js"),
        "prism_js_js":     _read_inline("prism.js.js"),
        "prism_ts_js":     _read_inline("prism.ts.js"),
        "prism_php_js":    _read_inline("prism.php.js"),
        "prism_markup_templating_js": _read_inline("prism.markup_templating.js"),
        "prism_go_js":     _read_inline("prism.go.js"),
        "prism_ruby_js":   _read_inline("prism.ruby.js"),
        "prism_cs_js":     _read_inline("prism.cs.js"),
        "prism_bash_js":   _read_inline("prism.bash.js"),
        "prism_sql_js":    _read_inline("prism.sql.js"),
        "prism_yaml_js":   _read_inline("prism.yaml.js"),
        "prism_json_js":   _read_inline("prism.json.js"),
        "prism_kt_js":     _read_inline("prism.kt.js"),
    }

    template = env.get_template("base.html.j2")

    target_display, target_raw = humanize_target(target)
    # If humanize couldn't derive a better name, fall back to project_name
    if not target_display:
        target_display = project_name

    html = template.render(
        version=VERSION,
        project_name=project_name,
        target=target,
        target_display=target_display,
        target_raw=target_raw,
        target_is_path=bool(target_raw and target_raw != target_display),
        mode=mode,
        mode_label=mode_label_map.get(mode, mode),
        report_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        test_date_start=test_date_start,
        test_date_end=test_date_end,
        partial=partial,
        snippet_mode=snippet_mode,
        primary_language=primary_language,
        frameworks=frameworks_str,
        build_tool=build_tool,
        entry_file=entry_file,
        entry_points=entry_points,
        routes=routes,
        routes_count=len(routes),
        deps_count=deps_count,
        deps_risk=deps_risk,
        deps_risk_count=len(deps_risk),
        cve_findings=cve_findings,
        cve_findings_count=cve_findings_count,
        cve_by_severity=cve_by_severity,
        cve_source=cve_source,
        cve_queries_total=cve_queries_total,
        cve_queries_cached=cve_queries_cached,
        findings=findings_norm,
        findings_count=total,
        counts=counts_dict,
        coverage_pct=f"{coverage_pct:.1f}",
        tested_assets=tested_assets,
        total_assets=total_assets,
        severity_filters=SEVERITY_FILTERS,
        top_findings=top_list,
        class_labels_json=json.dumps(class_labels, ensure_ascii=False),
        class_counts_json=json.dumps(class_counts),
        executive_summary_intro=summary_intro,
        assets=assets,
        execution_log=(execution_log[:50000] if execution_log else "(no log)"),
        tool_versions=tool_versions,
        inline=inline_assets,
        tool_versions_purpose={
            "violeteyes": "白盒源码审计主 Skill",
            "llm": "推理模型",
            "python": "Python 解释器版本",
            "author": "作者署名",
        },
    )

    return html


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="VioletEyes Report Renderer (Jinja2)")
    parser.add_argument("--findings", default="findings.json")
    parser.add_argument("--assets", default="assets.json")
    parser.add_argument("--profile", default="framework_profile.json")
    parser.add_argument("--execution-log", default="execution.log")
    parser.add_argument("--cve-input", default="",
                        help="V1.2: Path to dependency_cve.json (from scripts/cve_lookup.py). "
                             "Default empty → CVE section not rendered.")
    parser.add_argument("--output", default="code-audit-report.html")
    parser.add_argument(
        "--template-dir", default="templates",
        help="Root of Jinja2 templates (default: templates/)",
    )
    parser.add_argument("--project-name", default="code-audit")
    parser.add_argument("--target", default=".")
    parser.add_argument("--mode", default="full",
                        choices=["full", "incremental", "snippet", "api-focused", "frontend-focused", "diff"])
    parser.add_argument("--severity-floor", default="low",
                        choices=["info", "low", "medium", "high", "critical"])
    parser.add_argument("--test-date-start", default=datetime.now().strftime("%Y-%m-%d %H:%M"))
    parser.add_argument("--test-date-end", default=datetime.now().strftime("%Y-%m-%d %H:%M"))
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--snippet-mode", action="store_true")
    args = parser.parse_args()

    template_dir = Path(args.template_dir)
    if not template_dir.exists():
        print(f"[FAIL] template dir not found: {template_dir}", file=sys.stderr)
        return 1
    if not (template_dir / "base.html.j2").exists():
        print(f"[FAIL] base.html.j2 not found in {template_dir}", file=sys.stderr)
        return 1

    def _load(path: str) -> Any:
        p = Path(path)
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[FAIL] {path} is not valid JSON: {e}", file=sys.stderr)
            return []

    # Allow top-level JSON to be either a list (findings list / assets list)
    # or a dict with the conventional "findings" / "assets" key. This keeps
    # backwards compatibility with both flat and nested layouts.
    def _unwrap(obj: Any, *keys: str) -> Any:
        if isinstance(obj, dict):
            for k in keys:
                if k in obj:
                    return obj[k]
        return obj

    findings = _unwrap(_load(args.findings), "findings")
    assets = _unwrap(_load(args.assets), "assets")
    profile = _load(args.profile)
    cve_data = _load(args.cve_input) if args.cve_input else None
    execution_log = Path(args.execution_log).read_text(encoding="utf-8") \
        if Path(args.execution_log).exists() else ""

    tool_versions = {
        "violeteyes": VERSION,
        "author": "Cr1m3rA",
        "llm": "claude-opus-4-8",
        "python": sys.version.split()[0],
    }

    try:
        html = render(
            findings=findings if isinstance(findings, list) else [],
            assets=assets if isinstance(assets, list) else [],
            profile=profile if isinstance(profile, dict) else None,
            execution_log=execution_log,
            template_dir=template_dir,
            project_name=args.project_name,
            target=args.target,
            mode=args.mode,
            severity_floor=args.severity_floor,
            partial=args.partial,
            snippet_mode=args.snippet_mode,
            test_date_start=args.test_date_start,
            test_date_end=args.test_date_end,
            tool_versions=tool_versions,
            cve_data=cve_data,
        )
    except Exception as e:
        print(f"[FAIL] render error: {e}", file=sys.stderr)
        raise

    Path(args.output).write_text(html, encoding="utf-8")
    size_kb = len(html.encode("utf-8")) / 1024
    print(f"[OK] report written to {args.output} ({size_kb:.1f} KB)")
    print(f"     total findings: {sum(1 for _ in findings)}")
    print(f"     after severity-floor ({args.severity_floor}): {sum(1 for f in findings if isinstance(f, dict))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())