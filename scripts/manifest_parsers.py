#!/usr/bin/env python3
"""
VioletEyes — Manifest Parsers

Extract ``(ecosystem, name, version)`` tuples from every supported manifest
format. Used by:
  - ``scripts/framework_detect.py`` (Step 1: --emit-deps-json)
  - ``scripts/cve_lookup.py``    (Step 3.5: CVE scanning)

Each parser function takes the manifest's text content (already read) plus
the manifest ``Path`` and returns a list of dependency dicts:

    [
        {"ecosystem": "Maven", "name": "log4j-core", "version": "2.14.1",
         "manifest": "pom.xml", "manifest_path": "pom.xml"},
        ...
    ]

The ``manifest_path`` is the relative path from the repo root (when available)
or the basename — used by the report's "manifest 位置" column.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from ecosystems import (
    ecosystem_for_manifest,
    normalize_package_name,
    normalize_version,
)


# Match a generic semver-ish version token
_VER_TOKEN_RE = re.compile(r"\d+(?:\.\w+(?:[\.-]\w+)*)*")


# ---------------------------------------------------------------------------
# Generic per-manifest dispatch
# ---------------------------------------------------------------------------

# Manifest basename (or suffix) → parser function
PARSERS: Dict[str, str] = {
    "package.json":     "parse_package_json",
    "pom.xml":          "parse_pom_xml",
    "requirements.txt": "parse_requirements_txt",
    "pyproject.toml":   "parse_pyproject_toml",
    "setup.py":         "parse_setup_py",
    "Pipfile":          "parse_pipfile",
    "composer.json":    "parse_composer_json",
    "go.mod":           "parse_go_mod",
    "Gemfile":          "parse_gemfile",
    "Cargo.toml":       "parse_cargo_toml",
    "build.gradle":     "parse_gradle",
    "build.gradle.kts": "parse_gradle",
    "packages.config":  "parse_packages_config",
}


def parse_manifest(path: Path, content: str, manifest_relpath: Optional[str] = None) -> List[Dict]:
    """Dispatch to the right parser for ``path`` and return dependency dicts.

    ``manifest_relpath`` is what gets stored in the result (defaults to
    ``path.name`` for ad-hoc parses).
    """
    rel = manifest_relpath or path.name
    name = path.name
    parser_name = PARSERS.get(name)
    if parser_name is None and name.endswith(".csproj"):
        parser_name = "parse_csproj"

    if parser_name is None:
        return []

    parser = globals().get(parser_name)
    if parser is None:
        return []

    try:
        rows = parser(content, rel)
    except Exception:
        # A malformed manifest should never crash the audit; just skip
        return []

    out: List[Dict] = []
    eco = ecosystem_for_manifest(path) or "unknown"
    for r in rows:
        if not r.get("name"):
            continue
        version = normalize_version(r.get("version") or "")
        if not version:
            continue
        out.append({
            "ecosystem": eco,
            "name": normalize_package_name(r["name"], eco),
            "version": version,
            "manifest": rel,
            "manifest_path": rel,
        })
    return out


# ---------------------------------------------------------------------------
# Per-format parsers
# ---------------------------------------------------------------------------

def parse_package_json(content: str, manifest: str) -> List[Dict]:
    """Parse dependencies + devDependencies + optionalDependencies + peerDependencies."""
    try:
        pkg = json.loads(content)
    except json.JSONDecodeError:
        return []
    rows: List[Dict] = []
    sections = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
    for section in sections:
        block = pkg.get(section)
        if not isinstance(block, dict):
            continue
        for name, version in block.items():
            if not isinstance(name, str) or not isinstance(version, str):
                continue
            rows.append({"name": name, "version": version})
    return rows


def parse_pom_xml(content: str, manifest: str) -> List[Dict]:
    """Parse <dependency> blocks; emit artifactId + version.

    Regex approach (matches the existing framework_detect.py behaviour) —
    a full XML parser is overkill here since POMs are usually well-formed
    and we're looking for known-vulnerable deps. We use DOTALL to allow
    newlines between tags and to skip past <groupId>.
    """
    rows: List[Dict] = []
    # Match <dependency> ... </dependency> blocks first
    for block in re.findall(r"<dependency\b[^>]*>(.*?)</dependency>", content, re.DOTALL | re.IGNORECASE):
        art = re.search(r"<artifactId>\s*([^<]+?)\s*</artifactId>", block, re.IGNORECASE)
        ver = re.search(r"<version>\s*([^<]+?)\s*</version>", block, re.IGNORECASE)
        # Skip BOM-managed variables like ${...}
        if not art or not ver:
            continue
        version = ver.group(1).strip()
        if version.startswith("${") or "{" in version:
            continue
        rows.append({"name": art.group(1).strip(), "version": version})
    # Fallback: loose artifactId+version pattern (matches <artifactId>X</artifactId>...<version>Y</version>)
    if not rows:
        for art_id, ver in re.findall(
            r"<artifactId>\s*([^<]+?)\s*</artifactId>.*?<version>\s*([^<]+?)\s*</version>",
            content,
            re.DOTALL,
        ):
            if ver.strip().startswith("${"):
                continue
            rows.append({"name": art_id.strip(), "version": ver.strip()})
    return rows


def parse_requirements_txt(content: str, manifest: str) -> List[Dict]:
    """Parse ``name==1.2.3`` / ``name>=1.2.3`` / ``name~=1.2.3`` lines.

    Also handles ``-r other.txt`` (skip) and ``# comment`` (skip).
    """
    rows: List[Dict] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Match name + version operator + version (PEP 440)
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*([<>=!~]+)\s*([\w.+*-]+)", line)
        if m:
            rows.append({"name": m.group(1), "version": m.group(3)})
            continue
        # Bare name (no version pin) — skip; we can't query OSV without a version
    return rows


def parse_pyproject_toml(content: str, manifest: str) -> List[Dict]:
    """Parse ``[tool.poetry.dependencies]`` and ``[project] dependencies``.

    Minimal TOML parser — avoids a hard dependency on ``tomli``.
    """
    rows: List[Dict] = []

    # [project] dependencies = ["foo==1.0", "bar>=2.0"]
    proj_section = re.search(r"^\[project\]\s*(.*?)(?=^\[|\Z)", content, re.DOTALL | re.MULTILINE)
    if proj_section:
        block = proj_section.group(1)
        deps_match = re.search(r"^dependencies\s*=\s*\[(.*?)\]", block, re.DOTALL | re.MULTILINE)
        if deps_match:
            for entry in re.findall(r"['\"]([^'\"]+)['\"]", deps_match.group(1)):
                m = re.match(r"^([A-Za-z0-9_.\-]+)\s*([<>=!~]+)\s*([\w.+*-]+)", entry.strip())
                if m:
                    rows.append({"name": m.group(1), "version": m.group(3)})

    # [tool.poetry.dependencies] — key = "version"
    po_section = re.search(
        r"^\[tool\.poetry\.dependencies\]\s*(.*?)(?=^\[|\Z)",
        content,
        re.DOTALL | re.MULTILINE,
    )
    if po_section:
        block = po_section.group(1)
        for name, ver in re.findall(
            r'^([A-Za-z0-9_.\-]+)\s*=\s*"([^"]+)"',
            block,
            re.MULTILINE,
        ):
            if name == "python":
                continue
            rows.append({"name": name, "version": ver})
    return rows


def parse_setup_py(content: str, manifest: str) -> List[Dict]:
    """Parse ``install_requires=[...]`` list in setup.py.

    Limited to the common simple-quoted form; expressions like
    ``install_requires=requirements_txt`` are skipped.
    """
    rows: List[Dict] = []
    m = re.search(r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not m:
        return rows
    for entry in re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)):
        mm = re.match(r"^([A-Za-z0-9_.\-]+)\s*([<>=!~]+)\s*([\w.+*-]+)", entry.strip())
        if mm:
            rows.append({"name": mm.group(1), "version": mm.group(3)})
    return rows


def parse_pipfile(content: str, manifest: str) -> List[Dict]:
    """Parse ``[packages]`` and ``[dev-packages]`` sections."""
    rows: List[Dict] = []
    for section in ("[packages]", "[dev-packages]"):
        m = re.search(
            rf"^{re.escape(section)}\s*(.*?)(?=^\[|\Z)",
            content,
            re.DOTALL | re.MULTILINE,
        )
        if not m:
            continue
        for name, ver in re.findall(
            r'^([A-Za-z0-9_.\-]+)\s*=\s*"([^"]+)"',
            m.group(1),
            re.MULTILINE,
        ):
            rows.append({"name": name, "version": ver})
    return rows


def parse_composer_json(content: str, manifest: str) -> List[Dict]:
    """Parse ``require`` + ``require-dev`` dicts. Skip ``php`` and ``ext-*``."""
    try:
        pkg = json.loads(content)
    except json.JSONDecodeError:
        return []
    rows: List[Dict] = []
    for section in ("require", "require-dev"):
        block = pkg.get(section)
        if not isinstance(block, dict):
            continue
        for name, ver in block.items():
            if not isinstance(name, str) or not isinstance(ver, str):
                continue
            if name == "php" or name.startswith("ext-"):
                continue
            rows.append({"name": name, "version": ver})
    return rows


def parse_go_mod(content: str, manifest: str) -> List[Dict]:
    """Parse ``require`` blocks in go.mod. Keep the full module path."""
    rows: List[Dict] = []
    # Match both single-line and block-form `require (...)` declarations.
    # Block form: `require (\n    github.com/foo/bar v1.2.3\n)`
    block_re = re.compile(r"require\s*\(([^)]*)\)", re.DOTALL)
    for block in block_re.findall(content):
        for line in block.splitlines():
            m = re.match(r"^\s*(\S+)\s+(v[\w.+-]+)", line)
            if m and not m.group(1).startswith("//"):
                rows.append({"name": m.group(1), "version": m.group(2)})
    # Single-line form: `require github.com/foo/bar v1.2.3`
    for m in re.finditer(r"^require\s+(\S+)\s+(v[\w.+-]+)", content, re.MULTILINE):
        rows.append({"name": m.group(1), "version": m.group(2)})
    return rows


def parse_gemfile(content: str, manifest: str) -> List[Dict]:
    """Parse ``gem 'name', '1.2.3'`` lines."""
    rows: List[Dict] = []
    for m in re.finditer(r"^\s*gem\s+['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?", content, re.MULTILINE):
        name, ver = m.group(1), m.group(2) or ""
        rows.append({"name": name, "version": ver})
    return rows


def parse_cargo_toml(content: str, manifest: str) -> List[Dict]:
    """Parse ``[dependencies]`` and ``[dev-dependencies]`` sections."""
    rows: List[Dict] = []
    for section in ("[dependencies]", "[dev-dependencies]"):
        m = re.search(
            rf"^{re.escape(section)}\s*(.*?)(?=^\[|\Z)",
            content,
            re.DOTALL | re.MULTILINE,
        )
        if not m:
            continue
        for name, ver in re.findall(
            r'^([A-Za-z0-9_.\-]+)\s*=\s*"([^"]+)"',
            m.group(1),
            re.MULTILINE,
        ):
            rows.append({"name": name, "version": ver})
    return rows


def parse_gradle(content: str, manifest: str) -> List[Dict]:
    """Parse Groovy / Kotlin DSL dependency declarations.

    Handles the common short form ``implementation 'group:artifact:1.2.3'``
    and Kotlin DSL's ``implementation("group:artifact:1.2.3")`` form.
    """
    rows: List[Dict] = []
    # Short form: 'group:artifact:version' or "group:artifact:version"
    for m in re.finditer(r"['\"]([A-Za-z0-9_.\-]+):([A-Za-z0-9_.\-]+):([\w.+-]+)['\"]", content):
        rows.append({"name": m.group(2), "version": m.group(3)})
    # Map form: group: 'g', name: 'n', version: 'v' (less common)
    return rows


def parse_csproj(content: str, manifest: str) -> List[Dict]:
    """Parse ``<PackageReference Include="Foo" Version="1.2.3" />`` entries."""
    rows: List[Dict] = []
    for m in re.finditer(
        r'<PackageReference\s+[^>]*Include\s*=\s*"([^"]+)"[^>]*Version\s*=\s*"([^"]+)"',
        content,
        re.IGNORECASE,
    ):
        rows.append({"name": m.group(1), "version": m.group(2)})
    return rows


def parse_packages_config(content: str, manifest: str) -> List[Dict]:
    """Parse legacy ``packages.config`` NuGet format."""
    rows: List[Dict] = []
    for m in re.finditer(
        r'<package\s+[^>]*id\s*=\s*"([^"]+)"[^>]*version\s*=\s*"([^"]+)"',
        content,
        re.IGNORECASE,
    ):
        rows.append({"name": m.group(1), "version": m.group(2)})
    return rows


# ---------------------------------------------------------------------------
# Convenience entrypoint used by framework_detect.py --emit-deps-json
# ---------------------------------------------------------------------------

def collect_dependencies(root: Path) -> List[Dict]:
    """Walk ``root`` and return every direct dependency as a flat list.

    Mirrors ``framework_detect.detect_manifests()`` exactly so callers can
    either pass the manifests in or call this function directly.
    """
    from typing import Iterable

    from framework_detect import detect_manifests
    manifests: Iterable[Path] = detect_manifests(root)
    out: List[Dict] = []
    for m in manifests:
        try:
            content = m.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        try:
            rel = str(m.relative_to(root)).replace("\\", "/")
        except ValueError:
            rel = m.name
        out.extend(parse_manifest(m, content, manifest_relpath=rel))
    return out


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Parse all manifests under a repo root")
    p.add_argument("root")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    args = p.parse_args()
    deps = collect_dependencies(Path(args.root).resolve())
    if args.json:
        print(json.dumps(deps, ensure_ascii=False, indent=2))
    else:
        for d in deps:
            print(f"{d['ecosystem']:10s} {d['name']:35s} {d['version']:20s} {d['manifest']}")
