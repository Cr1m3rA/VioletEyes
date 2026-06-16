#!/usr/bin/env python3
"""
VioletEyes — Ecosystem Mapping & Version Normalization

Single source of truth for:
  - Manifest filename → OSV.dev ecosystem string
  - Package-name quirks per ecosystem (npm scope, Go module path, Maven artifactId)
  - Loose version-string normalization (strip ^, ~, >=, =, etc.)

Used by both ``scripts/manifest_parsers.py`` (offline parsing) and
``scripts/cve_lookup.py`` (online + offline CVE lookup).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Manifest → OSV.dev ecosystem
# ---------------------------------------------------------------------------

# Exact OSV ecosystem strings — see https://ossf.github.io/osv-schema/
OSV_ECOSYSTEMS = (
    "npm",
    "PyPI",
    "Maven",
    "Go",
    "Packagist",
    "RubyGems",
    "crates.io",
    "NuGet",
    "Hex",
)


# Filename (or suffix for *.csproj) → OSV ecosystem string.
# Multiple entries map to the same ecosystem (e.g. requirements.txt + Pipfile → PyPI).
MANIFEST_TO_ECOSYSTEM: Dict[str, str] = {
    # Java / JVM
    "pom.xml": "Maven",
    "build.gradle": "Maven",
    "build.gradle.kts": "Maven",
    # Python
    "requirements.txt": "PyPI",
    "pyproject.toml": "PyPI",
    "setup.py": "PyPI",
    "Pipfile": "PyPI",
    # PHP
    "composer.json": "Packagist",
    # Node
    "package.json": "npm",
    # Go
    "go.mod": "Go",
    # Ruby
    "Gemfile": "RubyGems",
    # Rust
    "Cargo.toml": "crates.io",
    # C# / .NET (csproj + packages.config)
    ".csproj": "NuGet",
    "packages.config": "NuGet",
}


def ecosystem_for_manifest(path: Path) -> Optional[str]:
    """Return the OSV ecosystem for a manifest ``Path``, or None if unsupported."""
    name = path.name
    # Exact filename match first (cheap, common)
    if name in MANIFEST_TO_ECOSYSTEM:
        return MANIFEST_TO_ECOSYSTEM[name]
    # .csproj files vary by project name (Foo.csproj / FooBar.csproj)
    if name.endswith(".csproj"):
        return "NuGet"
    return None


# ---------------------------------------------------------------------------
# Package-name normalization
# ---------------------------------------------------------------------------

def normalize_package_name(name: str, ecosystem: str) -> str:
    """Return the canonical package name OSV.dev expects.

    Quirks handled:
      - npm: ``@scope/name`` is case-sensitive and must NOT be lowercased.
      - PyPI: lowercased + hyphen-to-underscore canonicalisation (PEP 503).
      - Maven: artifactId only (OSV uses artifactId; groupId is metadata).
      - Go: full module path (``github.com/gin-gonic/gin``), NOT last segment.
      - Composer, RubyGems, crates.io, NuGet: case-insensitive but OSV is
        case-sensitive in URLs — keep as-is from the manifest.
    """
    name = (name or "").strip()
    if not name:
        return name
    if ecosystem == "PyPI":
        return re.sub(r"[-_.]+", "-", name).lower()
    if ecosystem == "npm":
        # npm scopes (@scope/name) are case-sensitive — preserve as-is
        return name
    if ecosystem == "Go":
        return name  # full module path, never truncated
    # Maven, Composer, RubyGems, crates.io, NuGet — keep raw
    return name


# ---------------------------------------------------------------------------
# Version normalization
# ---------------------------------------------------------------------------

# Strip common PEP-440 / semver / npm-range / maven-range prefixes & suffixes
_VERSION_PREFIX_RE = re.compile(r"^[\s*vV]*")
_VERSION_OP_RE = re.compile(r"^\s*(<=|<<|>=|>>|<|>|==|!=|~=|~|\^|=)\s*")
_VERSION_RANGE_END_RE = re.compile(r"[,;\s].*$")
_VERSION_CHARS_RE = re.compile(r"[^\w.+-]")


def normalize_version(version: str) -> str:
    """Return a best-effort clean version string suitable for OSV.dev queries.

    Strips leading ``v``/``V``, npm range operators (``^``, ``~``, ``>=``,
    ``<=``, ``==``, etc.), and trailing metadata (anything after the first
    whitespace or comma). Preserves the actual digits+dots segment.
    """
    if not version:
        return ""
    v = version.strip()
    v = _VERSION_PREFIX_RE.sub("", v)
    v = _VERSION_OP_RE.sub("", v)
    v = _VERSION_RANGE_END_RE.sub("", v)
    # Stop at the first non-version char (e.g. "1.2.3-SNAPSHOT" → "1.2.3")
    m = re.match(r"^\d+([._-][\w]+)*", v)
    if m:
        v = m.group(0)
    else:
        v = _VERSION_CHARS_RE.sub("", v)
    return v.strip()


# ---------------------------------------------------------------------------
# OSV.dev endpoint
# ---------------------------------------------------------------------------

OSV_API_BASE = "https://api.osv.dev"
OSV_QUERY_URL = f"{OSV_API_BASE}/v1/query"
OSV_VULN_URL = f"{OSV_API_BASE}/v1/vulns"
