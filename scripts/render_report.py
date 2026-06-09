#!/usr/bin/env python3
"""
VioletEyes — Report Renderer

读取 findings.json / assets.json / framework_profile.json / execution.log
与 templates/report.html 模板，生成 code-audit-report.html。

Usage:
    python3 scripts/render_report.py \\
        --findings findings.json \\
        --assets assets.json \\
        --profile framework_profile.json \\
        --execution-log execution.log \\
        --output code-audit-report.html \\
        --report-template templates/report.html \\
        [--project-name "my-project"] \\
        [--target "/path/to/repo"] \\
        [--mode full] \\
        [--severity-floor low] \\
        [--partial]
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Informational"]
SEVERITY_COLOR = {
    "Critical": "#dc3545",
    "High":     "#fd7e14",
    "Medium":   "#ffc107",
    "Low":      "#17a2b8",
    "Informational": "#6c757d",
}
SEVERITY_CLASS = {
    "Critical": "critical",
    "High":     "high",
    "Medium":   "medium",
    "Low":      "low",
    "Informational": "info",
}


def redact(text: str) -> str:
    """脱敏：保留前后字符，中间 ***。"""
    if not text:
        return text
    # Bearer / Basic token
    text = re.sub(
        r"(Bearer|Basic|Token)\s+[A-Za-z0-9._\-+/=]{6,}",
        lambda m: f"{m.group(1)} {m.group(0).split()[-1][:6]}***{m.group(0).split()[-1][-4:]}",
        text,
    )
    # 长 base64-ish
    text = re.sub(
        r"([A-Za-z0-9+/=_-]{32,})",
        lambda m: f"{m.group(0)[:6]}***{m.group(0)[-4:]}",
        text,
    )
    # 内部 IP
    text = re.sub(
        r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b",
        "<internal-ip>",
        text,
    )
    return text


def esc(s: Any) -> str:
    """HTML escape."""
    if s is None:
        return ""
    s = str(s)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s


def prism_lang(language: str) -> str:
    """Map language to Prism.js hint."""
    m = {
        "java": "java",
        "kotlin": "kotlin",
        "scala": "scala",
        "groovy": "groovy",
        "python": "python",
        "php": "php",
        "javascript": "javascript",
        "typescript": "typescript",
        "go": "go",
        "ruby": "ruby",
        "csharp": "csharp",
        "rust": "rust",
        "vue": "markup",
        "react": "jsx",
        "jsx": "jsx",
        "tsx": "tsx",
        "html": "markup",
        "css": "css",
        "sql": "sql",
        "yaml": "yaml",
        "json": "json",
        "toml": "yaml",
        "ini": "ini",
        "bash": "bash",
        "shell": "bash",
    }
    return m.get(language.lower(), "plaintext")


# ---------------------------------------------------------------------------
# Finding rendering
# ---------------------------------------------------------------------------


def render_finding(f: Dict, idx: int) -> str:
    severity = f.get("severity", "Informational")
    sev_class = SEVERITY_CLASS.get(severity, "info")
    lang = f.get("language", "plaintext")
    lang_p = prism_lang(lang)

    # 标题
    title = esc(f.get("title", "(untitled)"))
    fid = esc(f.get("id", f"FND-{idx+1:04d}"))

    # 徽章
    badges = []
    badges.append(f'<span class="badge severity-{sev_class}">{esc(severity)}</span>')
    if f.get("confidence"):
        badges.append(f'<span class="badge confidence">{esc(f["confidence"])}</span>')
    if f.get("cvss_score") is not None:
        badges.append(f'<span class="badge cvss">CVSS {f["cvss_score"]}</span>')
    if f.get("cwe"):
        cwe = f["cwe"][0] if isinstance(f["cwe"], list) else f["cwe"]
        badges.append(f'<span class="badge cwe">{esc(cwe)}</span>')
    if f.get("owasp_2021"):
        badges.append(f'<span class="badge owasp">OWASP {esc(f["owasp_2021"])}</span>')
    if f.get("language"):
        badges.append(f'<span class="badge language">{esc(lang)}</span>')
    if f.get("framework"):
        badges.append(f'<span class="badge framework">{esc(f["framework"])}</span>')
    if f.get("human_review"):
        badges.append('<span class="badge confidence">⚠ Human Review Required</span>')

    # Meta
    meta = []
    if f.get("file_path"):
        line = f.get("file_line", "")
        line_str = f":{line}" if line else ""
        meta.append(f'<span class="label">文件:</span><code>{esc(f["file_path"]+line_str)}</code>')
    if f.get("class_or_route"):
        meta.append(f'<span class="label">类/路由:</span><code>{esc(f["class_or_route"])}</code>')
    if f.get("url_or_path"):
        meta.append(f'<span class="label">URL:</span><code>{esc(f["url_or_path"])}</code>')
    if f.get("method") and f.get("method") != "N/A":
        meta.append(f'<span class="label">HTTP 方法:</span><code>{esc(f["method"])}</code>')
    if f.get("parameter"):
        meta.append(f'<span class="label">参数:</span><code>{esc(f["parameter"])}</code>')
    if f.get("discovered_at"):
        meta.append(f'<span class="label">发现时间:</span><code>{esc(f["discovered_at"])}</code>')

    # 调用链
    call_chain_html = ""
    if f.get("call_chain"):
        lines = []
        for i, c in enumerate(f["call_chain"]):
            indent = "  " * i
            sym = esc(c.get("symbol", "?"))
            file = esc(c.get("file", "?"))
            line = c.get("line", "?")
            lines.append(f"{indent}└─ {sym}  ({file}:{line})")
        call_chain_html = f'<pre><code class="language-yaml">{"\\n".join(lines)}</code></pre>'

    # 代码片段
    code_html = ""
    if f.get("code_snippet"):
        snippet = redact(f["code_snippet"])
        if len(snippet.splitlines()) > 30:
            # 截断
            lines = snippet.splitlines()
            snippet = "\n".join(lines[:15] + ["  ... (truncated) ..."] + lines[-15:])
        code_html = f'<pre><code class="language-{lang_p}">{esc(snippet)}</code></pre>'

    # 修复代码
    fix_html = ""
    if f.get("remediation"):
        rem = f["remediation"]
        fix_html += f'<p><strong>{esc(rem.get("summary", ""))}</strong></p>'
        if rem.get("code_before"):
            fix_html += '<h5>修复前</h5>'
            fix_html += f'<pre><code class="language-{lang_p}">{esc(redact(rem["code_before"]))}</code></pre>'
        if rem.get("code_after"):
            fix_html += '<h5>修复后</h5>'
            fix_html += f'<pre><code class="language-{lang_p}">{esc(redact(rem["code_after"]))}</code></pre>'
        if rem.get("reference"):
            fix_html += f'<p>参考: <a href="{esc(rem["reference"])}" style="color: var(--code-audit-accent);">{esc(rem["reference"])}</a></p>'

    # PoC
    poc_html = ""
    if f.get("evidence"):
        ev = f["evidence"]
        if ev.get("poc_curl"):
            poc_html += '<h5>PoC (curl)</h5>'
            poc_html += f'<pre><code class="language-bash">{esc(redact(ev["poc_curl"]))}</code></pre>'
        if ev.get("poc_python"):
            poc_html += '<h5>PoC (Python)</h5>'
            poc_html += f'<pre><code class="language-python">{esc(redact(ev["poc_python"]))}</code></pre>'
        if ev.get("poc_java"):
            poc_html += '<h5>PoC (Java)</h5>'
            poc_html += f'<pre><code class="language-java">{esc(redact(ev["poc_java"]))}</code></pre>'
        if ev.get("poc_unit_test"):
            poc_html += '<h5>PoC (Unit Test)</h5>'
            poc_html += f'<pre><code class="language-{lang_p}">{esc(redact(ev["poc_unit_test"]))}</code></pre>'

    # 复现步骤
    repro_html = ""
    if f.get("reproduction_steps"):
        items = "".join(f"<li>{esc(redact(s))}</li>" for s in f["reproduction_steps"])
        repro_html = f'<ol class="repro-steps">{items}</ol>'

    # 参考 (CWE / OWASP)
    refs = []
    if f.get("cwe"):
        for c in f["cwe"]:
            cid = c.replace("CWE-", "")
            refs.append(f'<li>CWE-{esc(cid)}: <a href="https://cwe.mitre.org/data/definitions/{cid}.html">{esc(c)}</a></li>')
    if f.get("owasp_2021"):
        refs.append(f'<li>OWASP Top 10 2021: {esc(f["owasp_2021"])}</li>')
    if f.get("owasp_api_2023"):
        refs.append(f'<li>OWASP API Security 2023: {esc(f["owasp_api_2023"])}</li>')
    if f.get("cve"):
        for c in f["cve"]:
            refs.append(f'<li>{esc(c)}</li>')
    refs_html = "<ul>" + "".join(refs) + "</ul>" if refs else ""

    return f"""
<section id="{fid}" class="finding severity-{esc(severity)}">
    <header class="finding-header">
        <span class="id">{fid}</span>
        <h3>{title}</h3>
        {"".join(badges)}
    </header>

    <div class="finding-meta">
        {"".join(meta)}
    </div>

    {"<h4>📋 描述</h4><p>" + esc(redact(f.get('description',''))) + "</p>" if f.get('description') else ""}
    {"<h4>💥 影响</h4><p>" + esc(redact(f.get('impact', f.get('business_impact','')))) + "</p>" if f.get('impact') or f.get('business_impact') else ""}
    {"<h4>🎯 攻击者能力</h4><p>" + esc(redact(f.get('attacker_capability',''))) + "</p>" if f.get('attacker_capability') else ""}

    {"<h4>🔗 调用链</h4>" + call_chain_html if call_chain_html else ""}
    {"<h4>📝 vulnerable code</h4>" + code_html if code_html else ""}
    {"<h4>🔬 复现步骤</h4>" + repro_html if repro_html else ""}
    {"<h4>🛠️ PoC</h4>" + poc_html if poc_html else ""}
    {"<h4>🔧 修复建议</h4>" + fix_html if fix_html else ""}
    {"<h4>📚 参考</h4>" + refs_html if refs_html else ""}
</section>
"""


# ---------------------------------------------------------------------------
# Aggregations
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
        key=lambda f: (sev_rank.get(f.get("severity", "Informational"), 99), -(f.get("cvss_score") or 0)),
    )[:n]


def filter_findings(findings: List[Dict], severity_floor: str) -> List[Dict]:
    """按 severity_floor 过滤。"""
    floor_idx = SEVERITY_ORDER.index(severity_floor) if severity_floor in SEVERITY_ORDER else 4
    return [f for f in findings
            if SEVERITY_ORDER.index(f.get("severity", "Informational")) <= floor_idx]


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------


def render(
    findings: List[Dict],
    assets: List[Dict],
    profile: Optional[Dict],
    execution_log: str,
    template: str,
    project_name: str,
    target: str,
    mode: str,
    severity_floor: str,
    partial: bool,
    snippet_mode: bool,
    test_date_start: str,
    test_date_end: str,
    tool_versions: Dict,
) -> str:
    findings = filter_findings(findings, severity_floor)
    counts = severity_counts(findings)
    total = sum(counts.values())

    # 鲁棒性：assets 必须是 list
    if not isinstance(assets, list):
        assets = []
    # 鲁棒性：assets 列表中每一项必须是 dict
    assets = [a for a in assets if isinstance(a, dict)]
    # 鲁棒性：profile 必须是 dict
    if profile is not None and not isinstance(profile, dict):
        profile = {}

    # 框架画像
    primary_language = (profile or {}).get("primary_language", "unknown")
    frameworks = ",".join((profile or {}).get("frameworks", [])) or "—"
    build_tool = (profile or {}).get("build_tool", "—")
    entry_file = "—"
    eps = (profile or {}).get("entry_points", [])
    if eps and isinstance(eps, list) and isinstance(eps[0], dict):
        entry_file = eps[0].get("path", "—")
    elif eps:
        entry_file = str(eps[0])
    routes_count = sum(1 for a in assets if a.get("type") == "http_api")
    deps_count = (profile or {}).get("third_party_deps_count", 0)
    deps_risk = (profile or {}).get("dangerous_dependencies", [])
    routes = [a for a in assets if isinstance(a, dict) and a.get("type") == "http_api"]

    # Top findings
    top = top_findings(findings, 5)
    top_rows = []
    for f in top:
        sev = f.get("severity", "Informational")
        sev_class = SEVERITY_CLASS.get(sev, "info")
        file_loc = f.get("file_path", "")
        if f.get("file_line"):
            file_loc += f":{f['file_line']}"
        top_rows.append(
            f"<tr>"
            f"<td><code>{esc(f.get('id',''))}</code></td>"
            f"<td>{esc(f.get('title',''))}</td>"
            f"<td><span class='badge severity-{sev_class}'>{esc(sev)}</span></td>"
            f"<td>{f.get('cvss_score','')}</td>"
            f"<td><code>{esc(file_loc)}</code></td>"
            f"</tr>"
        )
    top_table = "\n".join(top_rows) or "<tr><td colspan='5'>无发现</td></tr>"

    # Findings TOC
    toc_items = []
    for i, f in enumerate(findings):
        toc_items.append(f'<li><a href="#{esc(f.get("id", f"FND-{i+1:04d}"))}">{esc(f.get("title",""))}</a> — <span class="badge severity-{SEVERITY_CLASS.get(f.get("severity",""),"info")}">{esc(f.get("severity",""))}</span></li>')
    findings_toc = "\n".join(toc_items) or "<li>无</li>"

    # Findings list
    findings_list = "\n".join(render_finding(f, i) for i, f in enumerate(findings))

    # Routes table
    route_rows = []
    for r in routes:
        m = "/".join(r.get("method", [])) or "*"
        auth = "✓" if r.get("auth_required") else "—"
        route_rows.append(
            f"<tr>"
            f"<td><code>{esc(m)}</code></td>"
            f"<td><code>{esc(r.get('url_or_path',''))}</code></td>"
            f"<td><code>{esc(r.get('class_or_route',''))}</code></td>"
            f"<td><code>{esc(r.get('file_path',''))}{':'+str(r['file_line']) if r.get('file_line') else ''}</code></td>"
            f"<td>{esc(r.get('auth_mechanism', auth))}</td>"
            f"</tr>"
        )
    routes_table = "\n".join(route_rows) or "<tr><td colspan='5'>无 HTTP 入口</td></tr>"

    # Deps risk table
    dep_rows = []
    for d in deps_risk:
        sev = d.get("severity", "Medium")
        sev_class = SEVERITY_CLASS.get(sev, "medium")
        cve = ", ".join(d.get("cve", []))
        dep_rows.append(
            f"<tr>"
            f"<td><code>{esc(d.get('name',''))}</code></td>"
            f"<td><code>{esc(d.get('version',''))}</code></td>"
            f"<td>{esc(cve)}</td>"
            f"<td><span class='badge severity-{sev_class}'>{esc(sev)}</span></td>"
            f"</tr>"
        )
    deps_risk_table = "\n".join(dep_rows) or "<tr><td colspan='4'>未发现高危依赖</td></tr>"

    # Assets table
    asset_rows = []
    for a in assets:
        if not isinstance(a, dict):
            continue
        m = "/".join(a.get("method", [])) if a.get("method") else a.get("type", "")
        auth = "✓" if a.get("auth_required") else "—"
        asset_rows.append(
            f"<tr>"
            f"<td><code>{esc(a.get('id',''))}</code></td>"
            f"<td>{esc(a.get('type',''))}</td>"
            f"<td>{esc(a.get('language',''))}/{esc(a.get('framework',''))}</td>"
            f"<td><code>{esc(a.get('file_path',''))}</code></td>"
            f"<td><code>{esc(a.get('url_or_path',''))}</code></td>"
            f"<td>{esc(a.get('auth_mechanism', auth))}</td>"
            f"<td>{a.get('findings_count', 0)}</td>"
            f"</tr>"
        )
    assets_table = "\n".join(asset_rows) or "<tr><td colspan='7'>无代码资产</td></tr>"

    # Entry table
    entry_rows = []
    for ep in (profile or {}).get("entry_points", []) if isinstance(profile, dict) else []:
        if isinstance(ep, dict):
            entry_rows.append(
                f"<tr><td><code>{esc(ep.get('symbol',''))}</code></td>"
                f"<td>{esc(ep.get('framework',''))}</td>"
                f"<td><code>{esc(ep.get('path',''))}</code></td></tr>"
            )
    entry_table = "\n".join(entry_rows) or "<tr><td colspan='3'>无</td></tr>"

    # Tool versions
    tool_rows = []
    for k, v in tool_versions.items():
        tool_rows.append(f"<tr><td><code>{esc(k)}</code></td><td>{esc(v)}</td><td>{esc(tool_versions.get(k+'_purpose',''))}</td></tr>")
    tool_table = "\n".join(tool_rows) or "<tr><td colspan='3'>—</td></tr>"

    # Class distribution chart
    vc = vuln_class_counts(findings, 10)
    class_labels = [v[0] for v in vc] or ["none"]
    class_counts = [v[1] for v in vc] or [0]

    # Executive summary
    exec_summary = (
        f"<p>本次对 <code>{esc(target)}</code> 的源码审计共发现 <strong>{total}</strong> 个漏洞，"
        f"其中 <strong style='color:#dc3545'>{counts['Critical']}</strong> 个 Critical、"
        f"<strong style='color:#fd7e14'>{counts['High']}</strong> 个 High、"
        f"<strong style='color:#ffc107'>{counts['Medium']}</strong> 个 Medium、"
        f"<strong style='color:#17a2b8'>{counts['Low']}</strong> 个 Low、"
        f"<strong style='color:#6c757d'>{counts['Informational']}</strong> 个 Info。</p>"
        f"<p>主要语言: <code>{esc(primary_language)}</code>，框架: <code>{esc(frameworks)}</code>，"
        f"识别 HTTP 入口 <strong>{routes_count}</strong> 个。</p>"
    )
    if partial:
        exec_summary += "<p>⚠ <strong>注意：本次审计因 token 预算受限未完成全部代码扫描，结果可能不完整。建议扩大预算后重审。</strong></p>"
    if snippet_mode:
        exec_summary += "<p>⚠ <strong>本次为代码片段审计，仅基于片段内容推理，缺调用链上下文，所有 finding 的 confidence 已自动下调。</strong></p>"

    # Banners
    banner_partial = ""
    if partial:
        banner_partial = '<div class="banner">⚠ <strong>Partial report</strong> — Agent 因 token 预算耗尽停止扩张，结果可能不完整。</div>'
    banner_snippet = ""
    if snippet_mode:
        banner_snippet = '<div class="banner">⚠ <strong>代码片段审计模式</strong> — 没有文件树 / 调用链上下文，confidence 已自动下调。</div>'

    # Coverage
    total_assets = len(assets)
    tested_assets = sum(1 for a in assets if a.get("tested"))
    coverage_pct = round(tested_assets / total_assets * 100, 1) if total_assets else 0

    # Substitute
    html = template
    replacements = {
        "{{PROJECT_NAME}}":    esc(project_name),
        "{{REPORT_DATE}}":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "{{TEST_DATE_START}}":  esc(test_date_start),
        "{{TEST_DATE_END}}":    esc(test_date_end),
        "{{TARGET}}":           esc(target),
        "{{MODE}}":             esc(mode),
        "{{PRIMARY_LANGUAGE}}": esc(primary_language),
        "{{FRAMEWORKS}}":       esc(frameworks),
        "{{BUILD_TOOL}}":       esc(build_tool),
        "{{ENTRY_FILE}}":       esc(entry_file),
        "{{ROUTES_COUNT}}":     str(routes_count),
        "{{DEPS_COUNT}}":       str(deps_count),
        "{{DEPS_RISK_COUNT}}":  str(len(deps_risk)),
        "{{TOTAL_ASSETS}}":     str(total_assets),
        "{{TESTED_ASSETS}}":    str(tested_assets),
        "{{COVERAGE_PCT}}":     f"{coverage_pct:.1f}",
        "{{FINDINGS_COUNT}}":   str(total),
        "{{COUNT_CRITICAL}}":   str(counts["Critical"]),
        "{{COUNT_HIGH}}":       str(counts["High"]),
        "{{COUNT_MEDIUM}}":     str(counts["Medium"]),
        "{{COUNT_LOW}}":        str(counts["Low"]),
        "{{COUNT_INFO}}":       str(counts["Informational"]),
        "{{CLASS_LABELS_JSON}}": json.dumps(class_labels, ensure_ascii=False),
        "{{CLASS_COUNTS_JSON}}": json.dumps(class_counts),
        "{{EXECUTIVE_SUMMARY}}": exec_summary,
        "{{TOP_FINDINGS_TABLE}}": top_table,
        "{{FINDINGS_TOC}}":       findings_toc,
        "{{FINDINGS_LIST}}":      findings_list,
        "{{ROUTES_TABLE}}":       routes_table,
        "{{DEPS_RISK_TABLE}}":    deps_risk_table,
        "{{ASSETS_TABLE}}":       assets_table,
        "{{ENTRY_TABLE}}":        entry_table,
        "{{EXECUTION_LOG}}":      esc(execution_log[:50000] if execution_log else "(no log)"),
        "{{TOOL_VERSIONS}}":      tool_table,
        "{{BANNER_PARTIAL}}":     banner_partial,
        "{{BANNER_SNIPPET}}":     banner_snippet,
    }
    for k, v in replacements.items():
        html = html.replace(k, v)

    return html


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="VioletEyes Report Renderer")
    parser.add_argument("--findings", default="findings.json")
    parser.add_argument("--assets", default="assets.json")
    parser.add_argument("--profile", default="framework_profile.json")
    parser.add_argument("--execution-log", default="execution.log")
    parser.add_argument("--output", default="code-audit-report.html")
    parser.add_argument("--report-template", default="templates/report.html")
    parser.add_argument("--project-name", default="code-audit")
    parser.add_argument("--target", default=".")
    parser.add_argument("--mode", default="full", choices=["full", "incremental", "snippet", "api-focused", "frontend-focused", "diff"])
    parser.add_argument("--severity-floor", default="low", choices=["info", "low", "medium", "high", "critical"])
    parser.add_argument("--test-date-start", default=datetime.now().strftime("%Y-%m-%d %H:%M"))
    parser.add_argument("--test-date-end", default=datetime.now().strftime("%Y-%m-%d %H:%M"))
    parser.add_argument("--partial", action="store_true", help="Mark report as partial (token budget exceeded)")
    parser.add_argument("--snippet-mode", action="store_true")
    args = parser.parse_args()

    # Load
    findings = []
    if Path(args.findings).exists():
        findings = json.loads(Path(args.findings).read_text(encoding="utf-8"))

    assets = []
    if Path(args.assets).exists():
        assets = json.loads(Path(args.assets).read_text(encoding="utf-8"))

    profile = None
    if Path(args.profile).exists():
        profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))

    execution_log = ""
    if Path(args.execution_log).exists():
        execution_log = Path(args.execution_log).read_text(encoding="utf-8")

    template = Path(args.report_template).read_text(encoding="utf-8")

    tool_versions = {
        "violeteyes": "1.0.0",
        "author": "Cr1m3rA",
        "llm": "claude-opus-4-8",
        "python": sys.version.split()[0],
        "purpose": "白盒源码审计",
    }

    html = render(
        findings=findings,
        assets=assets,
        profile=profile,
        execution_log=execution_log,
        template=template,
        project_name=args.project_name,
        target=args.target,
        mode=args.mode,
        severity_floor=args.severity_floor,
        partial=args.partial,
        snippet_mode=args.snippet_mode,
        test_date_start=args.test_date_start,
        test_date_end=args.test_date_end,
        tool_versions=tool_versions,
    )

    Path(args.output).write_text(html, encoding="utf-8")
    print(f"[OK] report written to {args.output}")
    print(f"     total findings: {sum(1 for _ in findings)}")
    print(f"     after severity-floor ({args.severity_floor}): {sum(1 for f in findings)}")


if __name__ == "__main__":
    main()
