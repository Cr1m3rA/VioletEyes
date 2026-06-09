#!/usr/bin/env python3
"""
VioletEyes — Framework Detector

扫描仓库根目录，输出 framework_profile.json。
由 Agent 在 Phase 1 (Recon) 调用。

Usage:
    python3 scripts/framework_detect.py <repo_root> [--output framework_profile.json]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# 框架 manifest 特征
FRAMEWORK_SIGNATURES: Dict[str, Dict[str, Any]] = {
    # Java
    "spring-boot": {
        "manifests": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "content_patterns": [
            r"spring-boot-starter",
            r"org\.springframework\.boot",
        ],
        "language": "java",
        "build_tool": "maven",
        "entry_signature": r"@SpringBootApplication",
    },
    "spring-mvc": {
        "manifests": ["pom.xml", "build.gradle"],
        "content_patterns": [r"spring-webmvc", r"spring-web"],
        "language": "java",
        "build_tool": "maven",
    },
    "spring-webflux": {
        "manifests": ["pom.xml", "build.gradle"],
        "content_patterns": [r"spring-webflux"],
        "language": "java",
        "build_tool": "maven",
    },
    "quarkus": {
        "manifests": ["pom.xml", "build.gradle"],
        "content_patterns": [r"io\.quarkus", r"quarkus-bom"],
        "language": "java",
        "build_tool": "maven",
    },
    "mybatis": {
        "manifests": ["pom.xml", "build.gradle"],
        "content_patterns": [r"mybatis", r"mybatis-plus"],
        "language": "java",
    },
    "hibernate": {
        "manifests": ["pom.xml", "build.gradle"],
        "content_patterns": [r"hibernate-core", r"hibernate-entitymanager"],
        "language": "java",
    },
    "struts2": {
        "manifests": ["pom.xml", "build.gradle"],
        "content_patterns": [r"struts2-core"],
        "language": "java",
    },
    "dubbo": {
        "manifests": ["pom.xml", "build.gradle"],
        "content_patterns": [r"<artifactId>dubbo</artifactId>", r"org\.apache\.dubbo"],
        "language": "java",
    },
    # Python
    "django": {
        "manifests": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
        "content_patterns": [r"^Django(\s*[>=<~]|$)", r'"Django"'],
        "language": "python",
    },
    "flask": {
        "manifests": ["requirements.txt", "pyproject.toml"],
        "content_patterns": [r"^Flask(\s*[>=<~]|$)"],
        "language": "python",
    },
    "fastapi": {
        "manifests": ["requirements.txt", "pyproject.toml"],
        "content_patterns": [r"^fastapi(\s*[>=<~]|$)"],
        "language": "python",
    },
    "tornado": {
        "manifests": ["requirements.txt", "pyproject.toml"],
        "content_patterns": [r"^tornado(\s*[>=<~]|$)"],
        "language": "python",
    },
    "sanic": {
        "manifests": ["requirements.txt", "pyproject.toml"],
        "content_patterns": [r"^sanic(\s*[>=<~]|$)"],
        "language": "python",
    },
    "aiohttp": {
        "manifests": ["requirements.txt", "pyproject.toml"],
        "content_patterns": [r"^aiohttp(\s*[>=<~]|$)"],
        "language": "python",
    },
    # PHP
    "laravel": {
        "manifests": ["composer.json"],
        "content_patterns": [r'"laravel/framework"'],
        "language": "php",
    },
    "symfony": {
        "manifests": ["composer.json"],
        "content_patterns": [r'"symfony/framework-bundle"'],
        "language": "php",
    },
    "thinkphp": {
        "manifests": ["composer.json"],
        "content_patterns": [r'"topthink/framework"', r'"topthink/think"'],
        "language": "php",
    },
    "yii": {
        "manifests": ["composer.json"],
        "content_patterns": [r'"yiisoft/yii2"'],
        "language": "php",
    },
    "codeigniter": {
        "manifests": ["composer.json"],
        "content_patterns": [r'"codeigniter4/framework"'],
        "language": "php",
    },
    "slim": {
        "manifests": ["composer.json"],
        "content_patterns": [r'"slim/slim"'],
        "language": "php",
    },
    "wordpress": {
        "manifests": [],
        "file_patterns": ["wp-config.php"],
        "language": "php",
    },
    # Node.js
    "express": {
        "manifests": ["package.json"],
        "content_patterns": [r'"express"\s*:\s*"'],
        "language": "javascript",
    },
    "koa": {
        "manifests": ["package.json"],
        "content_patterns": [r'"koa"\s*:\s*"'],
        "language": "javascript",
    },
    "fastify": {
        "manifests": ["package.json"],
        "content_patterns": [r'"fastify"\s*:\s*"'],
        "language": "javascript",
    },
    "nestjs": {
        "manifests": ["package.json"],
        "content_patterns": [r'"@nestjs/core"'],
        "language": "typescript",
    },
    "next": {
        "manifests": ["package.json"],
        "content_patterns": [r'"next"\s*:\s*"'],
        "language": "javascript",
    },
    "nuxt": {
        "manifests": ["package.json"],
        "content_patterns": [r'"nuxt"\s*:\s*"'],
        "language": "javascript",
    },
    "react": {
        "manifests": ["package.json"],
        "content_patterns": [r'"react"\s*:\s*"'],
        "language": "javascript",
    },
    "vue": {
        "manifests": ["package.json"],
        "content_patterns": [r'"vue"\s*:\s*"'],
        "language": "javascript",
    },
    "angular": {
        "manifests": ["package.json"],
        "content_patterns": [r'"@angular/core"'],
        "language": "typescript",
    },
    "svelte": {
        "manifests": ["package.json"],
        "content_patterns": [r'"svelte"\s*:\s*"'],
        "language": "javascript",
    },
    "electron": {
        "manifests": ["package.json"],
        "content_patterns": [r'"electron"\s*:\s*"'],
        "language": "javascript",
    },
    # Go
    "gin": {
        "manifests": ["go.mod"],
        "content_patterns": [r"github\.com/gin-gonic/gin"],
        "language": "go",
    },
    "echo": {
        "manifests": ["go.mod"],
        "content_patterns": [r"github\.com/labstack/echo"],
        "language": "go",
    },
    "fiber": {
        "manifests": ["go.mod"],
        "content_patterns": [r"github\.com/gofiber/fiber"],
        "language": "go",
    },
    "beego": {
        "manifests": ["go.mod"],
        "content_patterns": [r"github\.com/beego/beego"],
        "language": "go",
    },
    "chi": {
        "manifests": ["go.mod"],
        "content_patterns": [r"github\.com/go-chi/chi"],
        "language": "go",
    },
    # Ruby
    "rails": {
        "manifests": ["Gemfile"],
        "content_patterns": [r"^gem\s+['\"]rails['\"]"],
        "language": "ruby",
    },
    "sinatra": {
        "manifests": ["Gemfile"],
        "content_patterns": [r"^gem\s+['\"]sinatra['\"]"],
        "language": "ruby",
    },
    "hanami": {
        "manifests": ["Gemfile"],
        "content_patterns": [r"^gem\s+['\"]hanami['\"]"],
        "language": "ruby",
    },
    "grape": {
        "manifests": ["Gemfile"],
        "content_patterns": [r"^gem\s+['\"]grape['\"]"],
        "language": "ruby",
    },
    # C#
    "aspnet-mvc": {
        "manifests": [],
        "file_patterns": ["Global.asax"],
        "language": "csharp",
    },
    "aspnet-core": {
        "manifests": ["*.csproj"],
        "content_patterns": [r"Microsoft\.AspNetCore\.App"],
        "language": "csharp",
    },
    "webapi": {
        "manifests": ["*.csproj"],
        "content_patterns": [r"Microsoft\.AspNet\.WebApi"],
        "language": "csharp",
    },
    # Rust
    "actix-web": {
        "manifests": ["Cargo.toml"],
        "content_patterns": [r'^actix-web\s*='],
        "language": "rust",
    },
    "rocket": {
        "manifests": ["Cargo.toml"],
        "content_patterns": [r'^rocket\s*='  ],
        "language": "rust",
    },
    "axum": {
        "manifests": ["Cargo.toml"],
        "content_patterns": [r'^axum\s*='],
        "language": "rust",
    },
}


# 已知危险依赖 + CVE（节选）
KNOWN_VULN_DEPS = {
    "log4j-core": [
        ("2.0-beta9", "2.14.1", "CVE-2021-44228", "Critical", "Log4Shell"),
        ("2.0-beta9", "2.15.0", "CVE-2021-45046", "Critical", "Log4j DoS"),
    ],
    "log4j-api": [
        ("2.0-beta9", "2.14.1", "CVE-2021-44228", "Critical", "Log4Shell"),
    ],
    "spring-core": [
        ("0", "5.3.17", "CVE-2022-22965", "Critical", "Spring4Shell"),
        ("0", "5.2.19", "CVE-2022-22965", "Critical", "Spring4Shell"),
    ],
    "spring-web": [
        ("0", "5.3.17", "CVE-2022-22965", "Critical", "Spring4Shell"),
    ],
    "fastjson": [
        ("0", "1.2.82", "multiple", "Critical", "Fastjson deserialization RCE"),
    ],
    "jackson-databind": [
        ("0", "2.9.10.6", "multiple", "High", "Jackson polymorphic deserialization"),
    ],
    "snakeyaml": [
        ("0", "1.32", "CVE-2022-1471", "High", "SnakeYaml RCE"),
    ],
    "shiro-core": [
        ("0", "1.7.0", "CVE-2020-17510", "High", "Apache Shiro bypass"),
        ("0", "1.7.0", "CVE-2020-17523", "High", "Apache Shiro bypass"),
    ],
    "shiro-web": [
        ("0", "1.7.0", "CVE-2020-17510", "High", "Apache Shiro bypass"),
    ],
    "struts2-core": [
        ("0", "2.5.29", "multiple", "High", "Struts2 OGNL RCE"),
    ],
    "thinkphp": [
        ("0", "6.0.13", "CVE-2022-47945", "Critical", "ThinkPHP multi-lang RCE"),
    ],
    "pyyaml": [
        ("0", "5.0", "CVE-2020-14343", "High", "PyYAML RCE"),
    ],
    "pillow": [
        ("0", "8.3.1", "CVE-2021-23437", "High", "Pillow ReDoS"),
    ],
    "lodash": [
        ("0", "4.17.20", "CVE-2021-23337", "High", "Lodash command injection"),
    ],
    "js-yaml": [
        ("0", "3.13.1", "CVE-2020-8203", "Medium", "js-yaml prototype pollution"),
    ],
    "axios": [
        ("0", "0.27.2", "CVE-2023-45857", "Medium", "Axios CSRF token leakage"),
    ],
    "jsonwebtoken": [
        ("0", "8.5.1", "CVE-2022-23529", "High", "JWT alg confusion"),
    ],
    "minimist": [
        ("0", "1.2.5", "CVE-2021-44906", "Medium", "minimist prototype pollution"),
    ],
    "node-serialize": [
        ("0", "0.0.4", "CVE-2017-16137", "Critical", "node-serialize RCE"),
    ],
}


def version_in_range(version: str, lo: str, hi: str) -> bool:
    """简单版本比较（不处理 semver 全部细节）。"""
    def parse(v):
        out = []
        for x in v.split("."):
            try:
                out.append(int(x))
            except ValueError:
                # 处理 2.0-beta9
                m = re.match(r"^(\d+)", x)
                out.append(int(m.group(1)) if m else 0)
        return tuple(out)

    v = parse(version)
    return parse(lo) <= v <= parse(hi)


def detect_manifests(root: Path) -> List[Path]:
    """查找所有 manifest 文件。"""
    manifests = []
    for name in [
        "pom.xml", "build.gradle", "build.gradle.kts",
        "requirements.txt", "pyproject.toml", "setup.py", "Pipfile",
        "composer.json",
        "package.json",
        "go.mod",
        "Gemfile",
        "Cargo.toml",
    ]:
        for p in root.rglob(name):
            # 排除 node_modules / target / build / dist / venv
            parts = p.parts
            if any(x in parts for x in ["node_modules", "target", "build", "dist", "venv", ".venv", "vendor", "__pycache__"]):
                continue
            manifests.append(p)
    return manifests


def detect_frameworks(root: Path, manifests: List[Path]) -> List[Dict]:
    """根据 manifest 内容匹配框架。"""
    detected = []
    for fw_name, sig in FRAMEWORK_SIGNATURES.items():
        for m in manifests:
            if m.name not in sig.get("manifests", []):
                continue
            try:
                content = m.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pat in sig.get("content_patterns", []):
                if re.search(pat, content, re.MULTILINE):
                    detected.append({
                        "framework": fw_name,
                        "language": sig["language"],
                        "build_tool": sig.get("build_tool", ""),
                        "evidence": m.name,
                    })
                    break
            else:
                continue
            break
    return detected


def find_entry_files(root: Path, frameworks: List[Dict]) -> List[Dict]:
    """根据框架特征找入口文件。"""
    entries = []
    fw_names = {f["framework"] for f in frameworks}

    # Spring Boot
    if any(fw in fw_names for fw in ["spring-boot", "spring-mvc", "spring-webflux", "quarkus"]):
        for java_file in root.rglob("*.java"):
            parts = java_file.parts
            if any(x in parts for x in ["node_modules", "target", "build", "dist"]):
                continue
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "@SpringBootApplication" in content and "public static void main" in content:
                # 提取 class 名
                m = re.search(r"public\s+class\s+(\w+).*?public\s+static\s+void\s+main", content, re.DOTALL)
                sym = m.group(1) if m else java_file.stem
                entries.append({
                    "path": str(java_file.relative_to(root)).replace("\\", "/"),
                    "symbol": sym,
                    "framework": "spring-boot",
                    "annotations": ["@SpringBootApplication"],
                })

    # Django
    if "django" in fw_names:
        for py_file in root.rglob("urls.py"):
            parts = py_file.parts
            if any(x in parts for x in ["venv", ".venv", "__pycache__", "migrations"]):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "urlpatterns" in content:
                entries.append({
                    "path": str(py_file.relative_to(root)).replace("\\", "/"),
                    "symbol": "urls.urlpatterns",
                    "framework": "django",
                    "annotations": ["urlpatterns"],
                })
                break  # 通常只有一个

    # Flask / FastAPI
    if any(fw in fw_names for fw in ["flask", "fastapi"]):
        for py_file in root.rglob("*.py"):
            parts = py_file.parts
            if any(x in parts for x in ["venv", ".venv", "__pycache__", "migrations", "tests", "test"]):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "Flask(__name__" in content or "FastAPI()" in content:
                m = re.search(r"(app)\s*=\s*(Flask|FastAPI)\(", content)
                sym = m.group(1) if m else "app"
                entries.append({
                    "path": str(py_file.relative_to(root)).replace("\\", "/"),
                    "symbol": sym,
                    "framework": list(fw_names & {"flask", "fastapi"})[0],
                    "annotations": [],
                })

    # Express / Koa / Fastify / NestJS / Next / Nuxt / React / Vue / Angular / Svelte / Electron
    if any(fw in fw_names for fw in ["express", "koa", "fastify", "nestjs", "next", "nuxt", "react", "vue", "angular", "svelte", "electron"]):
        pkg = root / "package.json"
        if pkg.exists():
            try:
                pkg_data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pkg_data = {}
            # 找 main / module
            main = pkg_data.get("main") or "index.js"
            for js_file in root.rglob(main):
                if "node_modules" in js_file.parts:
                    continue
                entries.append({
                    "path": str(js_file.relative_to(root)).replace("\\", "/"),
                    "symbol": pkg_data.get("main", "index"),
                    "framework": list(fw_names & {"express", "koa", "fastify", "nestjs", "next", "nuxt", "react", "vue", "angular", "svelte", "electron"})[0],
                    "annotations": [],
                })
                break

    # Go (Gin/Echo/Fiber/Beego/Chi)
    if any(fw in fw_names for fw in ["gin", "echo", "fiber", "beego", "chi"]):
        for go_file in root.rglob("main.go"):
            parts = go_file.parts
            if any(x in parts for x in ["vendor", "test", "tests", "examples"]):
                continue
            try:
                content = go_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "func main()" in content:
                entries.append({
                    "path": str(go_file.relative_to(root)).replace("\\", "/"),
                    "symbol": "main.main",
                    "framework": list(fw_names & {"gin", "echo", "fiber", "beego", "chi"})[0],
                    "annotations": [],
                })

    # Rails
    if "rails" in fw_names:
        routes = root / "config" / "routes.rb"
        if routes.exists():
            entries.append({
                "path": "config/routes.rb",
                "symbol": "routes.draw",
                "framework": "rails",
                "annotations": [],
            })

    # ASP.NET
    if any(fw in fw_names for fw in ["aspnet-core", "aspnet-mvc", "webapi"]):
        for cs_file in root.rglob("Program.cs"):
            try:
                content = cs_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "WebApplication" in content or "CreateBuilder" in content:
                entries.append({
                    "path": str(cs_file.relative_to(root)).replace("\\", "/"),
                    "symbol": "Program.Main",
                    "framework": "aspnet-core",
                    "annotations": [],
                })
                break

    return entries


def find_config_files(root: Path) -> List[str]:
    """找关键配置文件。"""
    configs = []
    candidates = [
        "application.yml", "application.yaml", "application.properties",
        "settings.py", ".env", ".env.example",
        "config/database.yml", "config/secrets.yml",
        "config/app.php", ".env.example",
        "web.config", "appsettings.json",
        "vite.config.js", "vite.config.ts",
        "next.config.js", "next.config.ts", "nuxt.config.ts",
        "vue.config.js",
    ]
    for c in candidates:
        p = root / c
        if p.exists():
            configs.append(c)
    return configs


def find_dangerous_deps(root: Path, manifests: List[Path]) -> List[Dict]:
    """查 manifest 中的危险依赖。"""
    found = []
    # 解析 manifest
    for m in manifests:
        try:
            content = m.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if m.name == "package.json":
            try:
                pkg = json.loads(content)
            except Exception:
                continue
            for section in ["dependencies", "devDependencies"]:
                for name, version in (pkg.get(section) or {}).items():
                    name_lc = name.lower()
                    if name_lc in KNOWN_VULN_DEPS:
                        for lo, hi, cve, sev, desc in KNOWN_VULN_DEPS[name_lc]:
                            # 简单：>= lo
                            if version_in_range(version.lstrip("^~"), lo, hi):
                                found.append({
                                    "name": name,
                                    "version": version,
                                    "cve": [cve],
                                    "severity": sev,
                                    "description": desc,
                                    "manifest": "package.json",
                                })
                                break
        elif m.name == "pom.xml":
            for art_id, ver in re.findall(r"<artifactId>([^<]+)</artifactId>.*?<version>([^<]+)</version>", content, re.DOTALL):
                if art_id in KNOWN_VULN_DEPS:
                    for lo, hi, cve, sev, desc in KNOWN_VULN_DEPS[art_id]:
                        if version_in_range(ver, lo, hi):
                            found.append({
                                "name": art_id,
                                "version": ver,
                                "cve": [cve],
                                "severity": sev,
                                "description": desc,
                                "manifest": "pom.xml",
                            })
                            break
        elif m.name in ["requirements.txt", "Pipfile"]:
            for match in re.finditer(r"^([A-Za-z0-9._\-]+)\s*([><=~!]+\s*[\d.]+)", content, re.MULTILINE):
                name, ver = match.group(1), match.group(2)
                ver = re.search(r"[\d.]+", ver).group(0) if re.search(r"[\d.]+", ver) else ""
                if name in KNOWN_VULN_DEPS:
                    for lo, hi, cve, sev, desc in KNOWN_VULN_DEPS[name]:
                        if version_in_range(ver, lo, hi):
                            found.append({
                                "name": name,
                                "version": ver,
                                "cve": [cve],
                                "severity": sev,
                                "description": desc,
                                "manifest": m.name,
                            })
                            break
        elif m.name == "composer.json":
            try:
                comp = json.loads(content)
            except Exception:
                continue
            for section in ["require", "require-dev"]:
                for name, ver in (comp.get(section) or {}).items():
                    if name in KNOWN_VULN_DEPS:
                        for lo, hi, cve, sev, desc in KNOWN_VULN_DEPS[name]:
                            v = re.search(r"[\d.]+", ver).group(0) if re.search(r"[\d.]+", ver) else ""
                            if version_in_range(v, lo, hi):
                                found.append({
                                    "name": name,
                                    "version": ver,
                                    "cve": [cve],
                                    "severity": sev,
                                    "description": desc,
                                    "manifest": "composer.json",
                                })
                                break
        elif m.name == "go.mod":
            for match in re.finditer(r"^\s*(\S+)\s+v([\d.]+)", content, re.MULTILINE):
                mod, ver = match.group(1), match.group(2)
                # 提取包名最后一段
                name = mod.split("/")[-1]
                if name in KNOWN_VULN_DEPS:
                    for lo, hi, cve, sev, desc in KNOWN_VULN_DEPS[name]:
                        if version_in_range(ver, lo, hi):
                            found.append({
                                "name": mod,
                                "version": ver,
                                "cve": [cve],
                                "severity": sev,
                                "description": desc,
                                "manifest": "go.mod",
                            })
                            break
        elif m.name == "Gemfile":
            for match in re.finditer(r"gem\s+['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?", content):
                name, ver = match.group(1), match.group(2) or ""
                if name in KNOWN_VULN_DEPS:
                    for lo, hi, cve, sev, desc in KNOWN_VULN_DEPS[name]:
                        v = re.search(r"[\d.]+", ver).group(0) if re.search(r"[\d.]+", ver) else ""
                        if version_in_range(v, lo, hi):
                            found.append({
                                "name": name,
                                "version": ver,
                                "cve": [cve],
                                "severity": sev,
                                "description": desc,
                                "manifest": "Gemfile",
                            })
                            break
        elif m.name == "Cargo.toml":
            for match in re.finditer(r'^(\S+)\s*=\s*"([\d.]+)"', content, re.MULTILINE):
                name, ver = match.group(1), match.group(2)
                if name in KNOWN_VULN_DEPS:
                    for lo, hi, cve, sev, desc in KNOWN_VULN_DEPS[name]:
                        if version_in_range(ver, lo, hi):
                            found.append({
                                "name": name,
                                "version": ver,
                                "cve": [cve],
                                "severity": sev,
                                "description": desc,
                                "manifest": "Cargo.toml",
                            })
                            break
    return found


def primary_language(manifests: List[Path], frameworks: List[Dict]) -> str:
    """主语言。"""
    if frameworks:
        from collections import Counter
        c = Counter(f["language"] for f in frameworks)
        return c.most_common(1)[0][0]
    # 启发式：按文件扩展名比例
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description="VioletEyes Framework Detector")
    parser.add_argument("root", help="Path to repo root")
    parser.add_argument("--output", default="framework_profile.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[ERR] {root} not found", file=sys.stderr)
        sys.exit(1)

    manifests = detect_manifests(root)
    frameworks = detect_frameworks(root, manifests)
    entries = find_entry_files(root, frameworks)
    configs = find_config_files(root)
    dangerous = find_dangerous_deps(root, manifests)

    profile = {
        "languages": list({f["language"] for f in frameworks}) or [],
        "primary_language": primary_language(manifests, frameworks),
        "frameworks": [f["framework"] for f in frameworks],
        "build_tool": next((f.get("build_tool", "") for f in frameworks if f.get("build_tool")), ""),
        "entry_points": entries,
        "config_files": configs,
        "third_party_deps_count": len(manifests),
        "has_docker": (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists(),
        "has_ci": any((root / d).exists() for d in [".github/workflows", ".gitlab-ci.yml", ".travis.yml", "Jenkinsfile", ".circleci"]),
        "dangerous_dependencies": dangerous,
    }

    Path(args.output).write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] profile written to {args.output}")
    print(f"     primary_language: {profile['primary_language']}")
    print(f"     frameworks: {profile['frameworks']}")
    print(f"     entry_points: {len(entries)}")
    print(f"     dangerous_dependencies: {len(dangerous)}")


if __name__ == "__main__":
    main()
