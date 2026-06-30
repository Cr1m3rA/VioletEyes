"""
SKILL.md front-matter schema — Python 等价实现（与 src/schema.ts 一一对应）。
跨进程一致性：apps/agent 用此模块校验 SKILL.md，避免 TS/Python 不一致导致 lint 误判。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

import yaml

# ── 枚举 ──

SKILL_KINDS = (
    "orchestrator",
    "framework",
    "entry-point",
    "sink",
    "vuln-class",
    "supply-chain",
)

SEVERITIES = ("info", "low", "medium", "high", "critical")

RUNTIME_MODELS = (
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    "gpt-4o",
)


# ── 错误 ──


class SkillFrontmatterError(ValueError):
    """Raised when SKILL.md front-matter fails validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("SKILL.md front-matter invalid: " + "; ".join(errors))


# ── 数据类 ──


@dataclass
class CapabilityMode:
    name: str
    tools_count: int
    enables: list[str]


@dataclass
class SkillInput:
    name: str
    type: str
    required: bool = False
    description: str | None = None
    enum: list[str] | None = None
    default: Any = None
    min: int | float | None = None
    max: int | float | None = None


@dataclass
class SkillOutput:
    name: str
    type: str
    schema_ref: str | None = None


@dataclass
class Runtime:
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    max_iterations: int | None = None


@dataclass
class SkillFrontmatter:
    name: str
    display_name: str
    version: str
    author: str
    license: str
    description: str
    kind: str
    target_languages: list[str] = field(default_factory=list)
    target_frameworks: list[str] = field(default_factory=list)
    target_vuln_classes: list[str] = field(default_factory=list)
    target_manifests: list[str] = field(default_factory=list)
    inputs: list[SkillInput] = field(default_factory=list)
    outputs: list[SkillOutput] = field(default_factory=list)
    capability_modes: list[CapabilityMode] = field(default_factory=list)
    mcp_dependencies: list[str] = field(default_factory=list)
    runtime: Runtime | None = None
    tags: list[str] = field(default_factory=list)
    homepage: str | None = None
    repository: str | None = None


# ── 校验 ──


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[a-z0-9.]+)?$")
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_CWE_RE = re.compile(r"^CWE-\d+$")


def _validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    # 必填 + 长度
    for key in ("name", "displayName", "version", "author", "license", "description", "kind"):
        if key not in data:
            errors.append(f"missing required field: {key}")
    # name 格式
    name = data.get("name", "")
    if name and not _NAME_RE.match(name):
        errors.append(f"name must be kebab-case, got {name!r}")
    # version semver
    version = data.get("version", "")
    if version and not _SEMVER_RE.match(version):
        errors.append(f"version must be semver, got {version!r}")
    # kind enum
    kind = data.get("kind")
    if kind and kind not in SKILL_KINDS:
        errors.append(f"kind must be one of {SKILL_KINDS}, got {kind!r}")
    # targetVulnClasses CWE 格式
    for cwe in data.get("targetVulnClasses", []):
        if not _CWE_RE.match(cwe):
            errors.append(f"targetVulnClasses entry must match CWE-\\d+, got {cwe!r}")
    # capability_modes 至少 1 个
    if not data.get("capability_modes"):
        errors.append("capability_modes must have at least 1 entry")
    # runtime.model
    runtime = data.get("runtime") or {}
    if isinstance(runtime, dict) and runtime.get("model") and runtime["model"] not in RUNTIME_MODELS:
        errors.append(f"runtime.model must be one of {RUNTIME_MODELS}, got {runtime['model']!r}")
    return errors


def parse_skill_frontmatter(text: str) -> SkillFrontmatter:
    """
    从 SKILL.md 文本中提取并校验 YAML front-matter。
    必须以 `---` 开头和结束。
    """
    if not text.startswith("---"):
        raise SkillFrontmatterError(["file does not start with front-matter delimiter `---`"])
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillFrontmatterError(["missing closing front-matter delimiter `---`"])
    raw = parts[1].strip()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise SkillFrontmatterError([f"YAML parse error: {e}"]) from e
    if not isinstance(data, dict):
        raise SkillFrontmatterError(["front-matter must be a YAML mapping"])

    errors = _validate(data)
    if errors:
        raise SkillFrontmatterError(errors)

    # 转 dataclass（与 TS 字段对齐：displayName → display_name 等）
    capability_modes = [
        CapabilityMode(
            name=cm["name"],
            tools_count=cm["tools_count"],
            enables=cm["enables"],
        )
        for cm in data.get("capability_modes", [])
    ]
    inputs = [
        SkillInput(
            name=i["name"],
            type=i["type"],
            required=i.get("required", False),
            description=i.get("description"),
            enum=i.get("enum"),
            default=i.get("default"),
            min=i.get("min"),
            max=i.get("max"),
        )
        for i in data.get("inputs", [])
    ]
    outputs = [
        SkillOutput(
            name=o["name"], type=o["type"], schema_ref=o.get("schemaRef")
        )
        for o in data.get("outputs", [])
    ]
    runtime_data = data.get("runtime") or {}
    runtime = Runtime(
        model=runtime_data.get("model"),
        temperature=runtime_data.get("temperature"),
        max_tokens=runtime_data.get("max_tokens"),
        max_iterations=runtime_data.get("max_iterations"),
    )

    return SkillFrontmatter(
        name=data["name"],
        display_name=data["displayName"],
        version=data["version"],
        author=str(data["author"]),
        license=data["license"],
        description=data["description"],
        kind=data["kind"],
        target_languages=data.get("targetLanguages", []),
        target_frameworks=data.get("targetFrameworks", []),
        target_vuln_classes=data.get("targetVulnClasses", []),
        target_manifests=data.get("targetManifests", []),
        inputs=inputs,
        outputs=outputs,
        capability_modes=capability_modes,
        mcp_dependencies=data.get("mcp_dependencies", []),
        runtime=runtime,
        tags=data.get("tags", []),
        homepage=data.get("homepage"),
        repository=data.get("repository"),
    )


# ── 危险模式（与 TS DANGEROUS_PATTERNS 一致）──

DANGEROUS_PATTERNS = (
    (re.compile(r"\beval\s*\("), "eval", "critical"),
    (re.compile(r"\bexec\s*\("), "exec", "critical"),
    (re.compile(r"\bos\.system\s*\("), "os.system", "critical"),
    (
        re.compile(r"\bsubprocess\.[a-zA-Z_]+\s*\([^)]*shell\s*=\s*True"),
        "subprocess-shell-true",
        "critical",
    ),
    (re.compile(r"\bchild_process\.exec\s*\("), "child_process.exec", "critical"),
    (re.compile(r"\bcurl\s+"), "curl", "medium"),
    (re.compile(r"\bwget\s+"), "wget", "medium"),
    (re.compile(r"\bnc\s+-l"), "netcat-listen", "critical"),
)


@dataclass
class LintFinding:
    rule: str
    severity: str
    file: str
    line: int | None = None
    snippet: str | None = None
    message: str = ""


def lint_skill_package(
    files: list[tuple[str, str]],  # [(path, content), ...]
    frontmatter: SkillFrontmatter,
) -> list[LintFinding]:
    """
    跑一遍 lint 检查 skill 包内容。与 TS lintSkillPackage 行为一致。
    """
    findings: list[LintFinding] = []

    if not frontmatter.target_languages and frontmatter.kind != "orchestrator":
        findings.append(
            LintFinding(
                rule="missing-target-languages",
                severity="low",
                file="SKILL.md",
                message="non-orchestrator skills should declare targetLanguages",
            )
        )

    for path, content in files:
        # 只扫 scripts/*.py / *.sh / *.js
        if "/scripts/" not in path:
            continue
        if not re.search(r"\.(py|sh|js|ts)$", path):
            continue
        for pattern, name, severity in DANGEROUS_PATTERNS:
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                findings.append(
                    LintFinding(
                        rule=f"dangerous-pattern:{name}",
                        severity=severity,
                        file=path,
                        line=line_num,
                        snippet=match.group(0),
                        message=f"dangerous pattern detected: {name}",
                    )
                )
    return findings