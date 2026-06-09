#!/usr/bin/env python3
"""
VioletEyes — Extract For Blackbox (Planned)

从 code-audit-report.html 中提取可移交黑盒层验证的目标列表。
**当前状态：待开发。** 配套的黑盒方向 Skill 尚未实现，本脚本仅作接口占位，
不会自动调用任何外部黑盒服务；运行结果可作为将来联动的输入参考。

保留字段：
  - url_or_path / method / parameter
  - file_path / severity / finding id

Usage:
    python3 scripts/extract_for_blackbox.py code-audit-report.html \\
        --min-severity High \\
        --output targets.txt
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Dict


def parse_args():
    p = argparse.ArgumentParser(
        description="VioletEyes 抽取脚本（黑盒联动接口占位，待开发）"
    )
    p.add_argument("report", default="code-audit-report.html")
    p.add_argument("--findings", default="findings.json",
                   help="Source findings.json (alternative to parsing HTML)")
    p.add_argument("--min-severity", default="Medium",
                   choices=["Informational", "Low", "Medium", "High", "Critical"])
    p.add_argument("--output", default="targets.txt")
    p.add_argument("--format", default="text",
                   choices=["text", "json", "blackbox-input"])
    return p.parse_args()


SEVERITY_ORDER = ["Informational", "Low", "Medium", "High", "Critical"]


def load_findings(path: Path) -> List[Dict]:
    """优先从 findings.json 读，回退到 HTML 解析。"""
    if path.exists() and path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix == ".html":
        return parse_html(path)
    return []


def parse_html(html_path: Path) -> List[Dict]:
    """简易 HTML 解析（regex）。"""
    text = html_path.read_text(encoding="utf-8")
    # 找所有 finding section
    findings = []
    for m in re.finditer(
        r'<section id="(FND-\d+)" class="finding severity-(\w+)">(.*?)</section>',
        text, re.DOTALL
    ):
        fid, sev, body = m.group(1), m.group(2), m.group(3)
        # 提取关键字段
        url = re.search(r'URL:</span><code>([^<]+)</code>', body)
        method = re.search(r'HTTP 方法:</span><code>([^<]+)</code>', body)
        param = re.search(r'参数:</span><code>([^<]+)</code>', body)
        file_ = re.search(r'文件:</span><code>([^<]+)</code>', body)
        findings.append({
            "id": fid,
            "severity": sev,
            "url_or_path": url.group(1) if url else "",
            "method": method.group(1) if method else "",
            "parameter": param.group(1) if param else "",
            "file_path": file_.group(1) if file_ else "",
        })
    return findings


def main():
    args = parse_args()
    findings_path = Path(args.findings)
    if not findings_path.exists():
        findings_path = Path(args.report)

    findings = load_findings(findings_path)

    min_idx = SEVERITY_ORDER.index(args.min_severity)
    targets = []
    for f in findings:
        sev = f.get("severity", "Informational")
        if SEVERITY_ORDER.index(sev) < min_idx:
            continue
        url = f.get("url_or_path") or ""
        method = f.get("method") or "N/A"
        param = f.get("parameter") or ""
        if not url:
            continue
        if args.format == "text":
            targets.append(f"{method} {url} (param={param})  # {f.get('id','')} {sev}")
        elif args.format == "json":
            targets.append({
                "id": f.get("id"),
                "severity": sev,
                "method": method,
                "url": url,
                "parameter": param,
                "file": f.get("file_path", ""),
            })
        elif args.format == "blackbox-input":
            # 待开发：抽出后可移交未来配套黑盒 Skill 验证
            targets.append(
                f"- [{sev}] {method} {url} (parameter={param}) — "
                f"file: {f.get('file_path','?')}"
            )

    if args.format == "text":
        Path(args.output).write_text("\n".join(targets), encoding="utf-8")
    elif args.format == "json":
        Path(args.output).write_text(json.dumps(targets, indent=2, ensure_ascii=False), encoding="utf-8")
    elif args.format == "blackbox-input":
        header = (
            "# Extracted from code-audit-report.html (VioletEyes)\n"
            "# Min severity: {sev}\n"
            "# Total: {n} target(s)\n"
            "# Note: 配套黑盒 Skill 尚未实现，仅作接口占位\n\n"
        ).format(sev=args.min_severity, n=len(targets))
        Path(args.output).write_text(header + "\n".join(targets), encoding="utf-8")

    print(f"[OK] extracted {len(targets)} target(s) to {args.output}")
    print("[NOTE] 黑盒联动 Skill 处于待开发状态，本次抽取结果仅作接口占位。")


if __name__ == "__main__":
    main()
