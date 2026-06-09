#!/usr/bin/env python3
"""
CodeAuditSkill — Sink Pattern Detector

读取一个文件，匹配危险函数 sink。Agent 在 Phase 4 调用，作为 LLM 推理的预筛。
不替代 LLM 推理——只是把可能的位置圈出来。

Usage:
    python3 scripts/sink_detect.py <file> [--language java] [--json]
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


# 危险 sink 模式
SINK_PATTERNS: Dict[str, List[Dict[str, Any]]] = {
    "java": [
        {"name": "rce-runtime-exec", "regex": r"Runtime\.getRuntime\(\)\s*\.\s*exec", "cwe": "CWE-78", "severity": "Critical", "class": "cmdi"},
        {"name": "rce-process-builder", "regex": r"new\s+ProcessBuilder\s*\(", "cwe": "CWE-78", "severity": "Critical", "class": "cmdi"},
        {"name": "deser-objectinputstream", "regex": r"ObjectInputStream", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-java"},
        {"name": "deser-xmldecoder", "regex": r"XMLDecoder", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-java"},
        {"name": "deser-xstream", "regex": r"XStream", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-java"},
        {"name": "deser-yaml", "regex": r"new\s+Yaml\s*\(", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-java"},
        {"name": "deser-fastjson", "regex": r"JSON\.parse\s*\(", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-java"},
        {"name": "deser-jackson-typing", "regex": r"ObjectMapper.*\.readValue\s*\([^,]+,\s*Object\.class\s*\)", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-java"},
        {"name": "jndi-lookup", "regex": r"InitialContext|Context\.lookup", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-java"},
        {"name": "spel-injection", "regex": r"SpelExpressionParser|ExpressionParser.*parseExpression", "cwe": "CWE-94", "severity": "Critical", "class": "spel-injection"},
        {"name": "ognl-injection", "regex": r"Ognl\.getValue|OgnlContext", "cwe": "CWE-94", "severity": "Critical", "class": "ognl-injection"},
        {"name": "sqli-statement", "regex": r"createStatement\(\)|Statement\s+\w+\s*=", "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "sqli-jpa-query-concat", "regex": r'@Query\s*\(\s*"[^"]*"\s*\+\s*', "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "sqli-mybatis-dollar", "regex": r'@Select\s*\(\s*"[^"]*\$\{', "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "ssrf-url", "regex": r"new\s+URL\s*\(", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
        {"name": "ssrf-resttemplate", "regex": r"RestTemplate", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
        {"name": "xxe-documentbuilder", "regex": r"DocumentBuilderFactory", "cwe": "CWE-611", "severity": "High", "class": "xxe"},
        {"name": "xxe-saxparser", "regex": r"SAXParserFactory", "cwe": "CWE-611", "severity": "High", "class": "xxe"},
        {"name": "lfi-file", "regex": r"new\s+File\s*\(\s*\".*\"\s*\+|new\s+FileInputStream", "cwe": "CWE-22", "severity": "High", "class": "file-read"},
        {"name": "xss-response-write", "regex": r"response\.getWriter\(\)\.write", "cwe": "CWE-79", "severity": "Medium", "class": "xss-reflected"},
        {"name": "open-redirect", "regex": r"response\.sendRedirect", "cwe": "CWE-601", "severity": "Medium", "class": "open-redirect"},
        {"name": "log4shell", "regex": r"log\.|logger\.|LOGGER\.|LoggerFactory", "cwe": "CVE-2021-44228", "severity": "Critical", "class": "log4shell"},
    ],
    "python": [
        {"name": "rce-eval", "regex": r"\beval\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "code-injection"},
        {"name": "rce-exec", "regex": r"\bexec\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "code-injection"},
        {"name": "rce-os-system", "regex": r"os\.system|os\.popen", "cwe": "CWE-78", "severity": "Critical", "class": "cmdi"},
        {"name": "rce-subprocess-shell", "regex": r"subprocess\.[A-Za-z_]+\([^)]*shell\s*=\s*True", "cwe": "CWE-78", "severity": "Critical", "class": "cmdi"},
        {"name": "deser-pickle", "regex": r"pickle\.(load|loads)\s*\(", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-python"},
        {"name": "deser-yaml-load", "regex": r"yaml\.load\s*\([^,)]+(?!.*Loader\s*=\s*yaml\.SafeLoader)", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-python"},
        {"name": "deser-marshal", "regex": r"marshal\.(load|loads)\s*\(", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-python"},
        {"name": "sqli-cursor-concat", "regex": r"\.execute\s*\(\s*['\"].*['\"]\s*\+\s*", "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "sqli-fstring", "regex": r"\.execute\s*\(\s*f['\"].*SELECT", "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "sqli-orm-raw", "regex": r"\.raw\s*\(\s*['\"].*\{|\.extra\s*\(", "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "nosql-where", "regex": r"\$where", "cwe": "CWE-943", "severity": "High", "class": "nosqli"},
        {"name": "ssti-render-template-string", "regex": r"render_template_string\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "ssti"},
        {"name": "ssti-jinja-template", "regex": r"jinja2\.Template\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "ssti"},
        {"name": "ssrf-requests", "regex": r"requests\.(get|post|put|delete)\s*\(", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
        {"name": "ssrf-urlopen", "regex": r"urllib\.request\.urlopen", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
        {"name": "lfi-open", "regex": r"open\s*\(\s*['\"].*\+|\bopen\s*\(\s*request\.", "cwe": "CWE-22", "severity": "High", "class": "file-read"},
        {"name": "weak-hash-md5", "regex": r"hashlib\.(md5|sha1)\s*\(", "cwe": "CWE-327", "severity": "Low", "class": "weak-crypto"},
        {"name": "weak-random", "regex": r"random\.(random|randint|choice|uniform)\s*\(", "cwe": "CWE-338", "severity": "Low", "class": "insecure-random"},
        {"name": "debug-enabled", "regex": r"DEBUG\s*=\s*True|app\.run\s*\(\s*debug\s*=\s*True", "cwe": "CWE-489", "severity": "Medium", "class": "debug-mode-enabled"},
    ],
    "php": [
        {"name": "rce-eval", "regex": r"\beval\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "code-injection"},
        {"name": "rce-assert", "regex": r"\bassert\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "code-injection"},
        {"name": "rce-system", "regex": r"\b(system|exec|passthru|shell_exec|popen|proc_open)\s*\(\s*\$", "cwe": "CWE-78", "severity": "Critical", "class": "cmdi"},
        {"name": "deser-unserialize", "regex": r"\bunserialize\s*\(\s*\$", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-php"},
        {"name": "lfi-include-var", "regex": r"\b(include|require|include_once|require_once)\s*\(\s*\$", "cwe": "CWE-829", "severity": "Critical", "class": "file-include"},
        {"name": "sqli-mysql-query-concat", "regex": r"mysql_query\s*\(\s*\$.*\+|mysqli_query\s*\(\s*\$", "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "ssrf-file-get-contents", "regex": r"file_get_contents\s*\(\s*\$|fopen\s*\(\s*\$", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
        {"name": "ssrf-curl", "regex": r"curl_setopt|curl_init", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
        {"name": "open-redirect-header", "regex": r"header\s*\(\s*['\"]Location\s*:['\"]?\s*\.?\s*\$", "cwe": "CWE-601", "severity": "Medium", "class": "open-redirect"},
        {"name": "xss-echo", "regex": r"\becho\s+\$_(GET|POST|REQUEST|COOKIE)\[", "cwe": "CWE-79", "severity": "High", "class": "xss-reflected"},
        {"name": "weak-hash-md5", "regex": r"\bmd5\s*\(\s*\$", "cwe": "CWE-327", "severity": "Low", "class": "weak-crypto"},
    ],
    "javascript": [
        {"name": "rce-eval", "regex": r"\beval\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "code-injection"},
        {"name": "rce-function", "regex": r"new\s+Function\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "code-injection"},
        {"name": "rce-settimeout-str", "regex": r"setTimeout\s*\(\s*['\"]", "cwe": "CWE-94", "severity": "High", "class": "code-injection"},
        {"name": "rce-setinterval-str", "regex": r"setInterval\s*\(\s*['\"]", "cwe": "CWE-94", "severity": "High", "class": "code-injection"},
        {"name": "rce-child-exec", "regex": r"child_process\.(exec|execSync)\s*\(", "cwe": "CWE-78", "severity": "Critical", "class": "cmdi"},
        {"name": "proto-pollution-merge", "regex": r"_\.(merge|set|setWith|defaultsDeep)\s*\(", "cwe": "CWE-1321", "severity": "High", "class": "prototype-pollution"},
        {"name": "deser-yaml", "regex": r"yaml\.load\s*\(", "cwe": "CWE-502", "severity": "High", "class": "deserialization-nodejs"},
        {"name": "deser-node-serialize", "regex": r"node-serialize|nodeSerialize|serialize-javascript", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-nodejs"},
        {"name": "xss-innerHTML", "regex": r"\.innerHTML\s*=", "cwe": "CWE-79", "severity": "High", "class": "xss-dom"},
        {"name": "xss-v-html", "regex": r"v-html=", "cwe": "CWE-79", "severity": "High", "class": "xss-dom"},
        {"name": "xss-dangerously-set", "regex": r"dangerouslySetInnerHTML", "cwe": "CWE-79", "severity": "High", "class": "xss-dom"},
        {"name": "xss-bypass-trust", "regex": r"bypassSecurityTrust(Html|Script|Url|ResourceUrl)", "cwe": "CWE-79", "severity": "High", "class": "xss-dom"},
        {"name": "ssrf-fetch", "regex": r"\bfetch\s*\(\s*[a-zA-Z_$][\w$]*\b", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
        {"name": "ssrf-axios", "regex": r"axios\.(get|post|put|delete)\s*\(", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
        {"name": "lfi-fs-read", "regex": r"fs\.(readFile|readFileSync|createReadStream)\s*\(", "cwe": "CWE-22", "severity": "High", "class": "file-read"},
        {"name": "sqli-db-query-concat", "regex": r"\.query\s*\(\s*['\"].*\+\s*", "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "jwt-none", "regex": r"algorithms\s*:\s*\[\s*['\"]none['\"]", "cwe": "CWE-347", "severity": "Critical", "class": "jwt-vuln"},
        {"name": "weak-random", "regex": r"Math\.random\s*\(\s*\)", "cwe": "CWE-338", "severity": "Low", "class": "insecure-random"},
    ],
    "typescript": [
        {"name": "rce-eval", "regex": r"\beval\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "code-injection"},
        {"name": "rce-child-exec", "regex": r"child_process\.(exec|execSync)\s*\(", "cwe": "CWE-78", "severity": "Critical", "class": "cmdi"},
        {"name": "xss-dangerously-set", "regex": r"dangerouslySetInnerHTML", "cwe": "CWE-79", "severity": "High", "class": "xss-dom"},
        {"name": "ssrf-fetch", "regex": r"\bfetch\s*\(", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
    ],
    "go": [
        {"name": "rce-exec-command", "regex": r"exec\.Command\s*\(", "cwe": "CWE-78", "severity": "Critical", "class": "cmdi"},
        {"name": "ssrf-http-get", "regex": r"http\.(Get|Post|NewRequest)\s*\(", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
        {"name": "lfi-os-open", "regex": r"os\.(Open|OpenFile|ReadFile)\s*\(", "cwe": "CWE-22", "severity": "High", "class": "file-read"},
        {"name": "sqli-db-query-concat", "regex": r"db\.(Query|Exec)\s*\(\s*['\"].*\+\s*", "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "ssti-html-template", "regex": r"template\.(HTML|JS|HTMLAttr)\s*\(", "cwe": "CWE-79", "severity": "High", "class": "xss-reflected"},
        {"name": "weak-random", "regex": r"math/rand\.", "cwe": "CWE-338", "severity": "Low", "class": "insecure-random"},
    ],
    "ruby": [
        {"name": "rce-eval", "regex": r"\beval\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "code-injection"},
        {"name": "rce-instance-eval", "regex": r"instance_eval|class_eval|module_eval", "cwe": "CWE-94", "severity": "Critical", "class": "code-injection"},
        {"name": "rce-system", "regex": r"\b(system|exec|spawn)\s*\(", "cwe": "CWE-78", "severity": "Critical", "class": "cmdi"},
        {"name": "rce-backtick", "regex": r"^\s*`[^`]*#\{", "cwe": "CWE-78", "severity": "High", "class": "cmdi"},
        {"name": "deser-yaml", "regex": r"YAML\.load\s*\(", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-ruby"},
        {"name": "deser-marshal", "regex": r"Marshal\.(load|restore)\s*\(", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-ruby"},
        {"name": "sqli-where-concat", "regex": r"\.where\s*\(\s*['\"].*#\{", "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "ssti-erb", "regex": r"ERB\.new\s*\(", "cwe": "CWE-94", "severity": "Critical", "class": "ssti"},
    ],
    "csharp": [
        {"name": "rce-process-start", "regex": r"Process\.Start\s*\(", "cwe": "CWE-78", "severity": "Critical", "class": "cmdi"},
        {"name": "deser-binaryformatter", "regex": r"BinaryFormatter", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-java"},
        {"name": "deser-javascript-serializer", "regex": r"JavaScriptSerializer\s*\(\s*\)\s*\.\s*Deserialize", "cwe": "CWE-502", "severity": "Critical", "class": "deserialization-java"},
        {"name": "sqli-sqlcommand-concat", "regex": r"new\s+SqlCommand\s*\(\s*['\"].*\+\s*", "cwe": "CWE-89", "severity": "High", "class": "sqli"},
        {"name": "ssrf-http-client", "regex": r"new\s+HttpClient\s*\(\s*\)|WebClient", "cwe": "CWE-918", "severity": "High", "class": "ssrf"},
        {"name": "lfi-file-readalltext", "regex": r"File\.(ReadAllText|ReadAllBytes|OpenRead)\s*\(", "cwe": "CWE-22", "severity": "High", "class": "file-read"},
        {"name": "xss-html-raw", "regex": r"@Html\.Raw", "cwe": "CWE-79", "severity": "High", "class": "xss-reflected"},
    ],
    "vue": [
        {"name": "xss-v-html", "regex": r"v-html=", "cwe": "CWE-79", "severity": "High", "class": "xss-dom"},
    ],
    "react": [
        {"name": "xss-dangerously-set", "regex": r"dangerouslySetInnerHTML", "cwe": "CWE-79", "severity": "High", "class": "xss-dom"},
    ],
    "angular": [
        {"name": "xss-bypass-trust", "regex": r"bypassSecurityTrust(Html|Script|Url|ResourceUrl)", "cwe": "CWE-79", "severity": "High", "class": "xss-dom"},
    ],
    "svelte": [
        {"name": "xss-html", "regex": r"\{@html", "cwe": "CWE-79", "severity": "High", "class": "xss-dom"},
    ],
}


def detect_language_from_ext(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".java": "java",
        ".kt": "java",
        ".scala": "java",
        ".py": "python",
        ".php": "php",
        ".js": "javascript",
        ".jsx": "react",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "react",
        ".go": "go",
        ".rb": "ruby",
        ".cs": "csharp",
        ".rs": "rust",
        ".vue": "vue",
        ".html": "html",
        ".htm": "html",
    }.get(ext, "")


def detect_sinks(content: str, language: str, file: Path) -> List[Dict]:
    """匹配危险 sink。"""
    patterns = SINK_PATTERNS.get(language, [])
    sinks = []
    for pat in patterns:
        for m in re.finditer(pat["regex"], content):
            # 计算行号
            line = content[:m.start()].count("\n") + 1
            sink_line = content.split("\n")[line - 1] if line <= len(content.split("\n")) else ""
            sinks.append({
                "file": str(file),
                "language": language,
                "line": line,
                "match": m.group(0),
                "context": sink_line.strip()[:200],
                "name": pat["name"],
                "cwe": pat["cwe"],
                "severity": pat["severity"],
                "vuln_class": pat["class"],
            })
    return sinks


def main():
    parser = argparse.ArgumentParser(description="CodeAuditSkill Sink Detector")
    parser.add_argument("file", help="Path to source file")
    parser.add_argument("--language", default=None, help="Force language (otherwise detect from extension)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    p = Path(args.file)
    if not p.exists():
        print(f"[ERR] {p} not found", file=sys.stderr)
        sys.exit(1)

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[ERR] read failed: {e}", file=sys.stderr)
        sys.exit(1)

    language = args.language or detect_language_from_ext(p)
    if not language:
        print(f"[ERR] cannot detect language from {p.suffix}", file=sys.stderr)
        sys.exit(1)

    sinks = detect_sinks(content, language, p)

    if args.json:
        print(json.dumps(sinks, indent=2, ensure_ascii=False))
    else:
        if not sinks:
            print(f"[OK] No sinks matched in {p} ({language})")
        else:
            print(f"[FOUND] {len(sinks)} sink(s) in {p} ({language}):")
            for s in sinks:
                print(f"  L{s['line']:<4} [{s['severity']}] {s['name']:<35} CWE={s['cwe']}")
                print(f"        {s['context'][:120]}")


if __name__ == "__main__":
    main()
