#!/usr/bin/env python3
"""
CodeAuditSkill — Tree Index

构建仓库的轻量级文件树索引（路径 + 扩展名 + 大小），用于 Agent 决定读哪些文件。
不读文件内容，只 `ls` 一下。

Usage:
    python3 scripts/tree_index.py <repo_root> [--depth 3] [--include-tests] [--output tree.json]
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any


# 跳过目录
SKIP_DIRS = {
    "node_modules", "target", "build", "dist", "out",
    "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache",
    "vendor", "bower_components",
    ".git", ".svn", ".hg",
    "tmp", "temp", "logs",
    "coverage", ".nyc_output",
    ".idea", ".vscode",
    "ios/Pods", "android/.gradle",
}

# 关键文件扩展名（按语言分类）
KEY_EXTENSIONS = {
    "java":      {".java", ".kt", ".scala", ".groovy"},
    "python":    {".py"},
    "php":       {".php"},
    "javascript":{".js", ".jsx", ".mjs", ".cjs"},
    "typescript":{".ts", ".tsx"},
    "go":        {".go"},
    "ruby":      {".rb"},
    "csharp":    {".cs"},
    "rust":      {".rs"},
    "frontend":  {".vue", ".svelte"},
    "template":  {".html", ".htm", ".ejs", ".pug", ".jinja", ".jinja2", ".hbs", ".twig", ".blade.php", ".erb"},
    "config":    {".yml", ".yaml", ".json", ".toml", ".ini", ".properties", ".env", ".conf"},
    "sql":       {".sql"},
    "build":     {".gradle", ".pom"},
}


def build_tree(root: Path, depth: int, include_tests: bool) -> List[Dict[str, Any]]:
    """递归构建文件树。"""
    items = []

    def walk(d: Path, current_depth: int, prefix: str):
        if current_depth > depth:
            return
        try:
            entries = sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return
        for entry in entries:
            if entry.name in SKIP_DIRS:
                continue
            if not include_tests and any(t in entry.parts for t in ["test", "tests", "__tests__", "spec", "Test"]):
                continue
            rel = str(entry.relative_to(root)).replace("\\", "/")
            if entry.is_dir():
                items.append({
                    "type": "dir",
                    "path": rel,
                    "name": entry.name,
                })
                walk(entry, current_depth + 1, prefix + "/")
            else:
                size = entry.stat().st_size if entry.exists() else 0
                ext = entry.suffix.lower()
                items.append({
                    "type": "file",
                    "path": rel,
                    "name": entry.name,
                    "ext": ext,
                    "size": size,
                })
    walk(root, 0, "")
    return items


def classify(item: Dict) -> str:
    """按扩展名归类。"""
    ext = item.get("ext", "")
    for lang, exts in KEY_EXTENSIONS.items():
        if ext in exts:
            return lang
    return "other"


def main():
    parser = argparse.ArgumentParser(description="CodeAuditSkill Tree Index")
    parser.add_argument("root")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--output", default="tree.json")
    parser.add_argument("--files-only", action="store_true", help="Only output files")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[ERR] {root} not found", file=sys.stderr)
        sys.exit(1)

    items = build_tree(root, args.depth, args.include_tests)
    if args.files_only:
        items = [i for i in items if i["type"] == "file"]

    # 统计
    by_class = {}
    for i in items:
        if i["type"] == "file":
            c = classify(i)
            by_class[c] = by_class.get(c, 0) + 1

    out = {
        "root": str(root),
        "depth": args.depth,
        "include_tests": args.include_tests,
        "total_entries": len(items),
        "by_class": by_class,
        "items": items,
    }

    Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] tree written to {args.output}")
    print(f"     total: {out['total_entries']}")
    print(f"     by class: {by_class}")


if __name__ == "__main__":
    main()
