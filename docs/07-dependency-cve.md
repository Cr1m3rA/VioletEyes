# 07 — 第三方依赖 CVE 扫描（V1.2）

> 本节定义 VioletEyes V1.2 新增的 **Step 3.5 第三方依赖 CVE 扫描** 子阶段的协议、缓存策略、限流策略与已知边界。

## 7.1 数据流

```
┌──────────────────────────────────────────────────────────────────┐
│   Python 端（一次性）                                              │
│                                                                  │
│   framework_detect.py --emit-deps-json  ──► third_party_deps.json │
│                                                                  │
│   cve_lookup.py                                                   │
│     ├── 查 OSV.dev (POST /v1/query, 4 并发)                       │
│     └── 查 payloads/vulnerable-ranges.json (离线 fallback)         │
│                          │                                       │
│                          ▼                                       │
│                dependency_cve.json                                │
│                findings.json  (Critical/High 升级)                │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│   浏览器侧（运行时）                                                │
│                                                                  │
│   partials/dependency_cve.html.j2                                 │
│     ├── 7 列表（依赖 / 版本 / 严重度 / CVE / 固定版本 / 简介 / 链接）│
│     ├── CVE 徽章 → https://nvd.nist.gov/vuln/detail/<CVE>         │
│     └── 离线来源角标 "离线缓存"                                    │
└──────────────────────────────────────────────────────────────────┘
```

## 7.2 OSV.dev 协议

**请求** `POST https://api.osv.dev/v1/query`
```json
{ "package": { "name": "log4j-core", "ecosystem": "Maven" }, "version": "2.14.1" }
```

**字段映射**（OSV → `dependency_cve.advisories[]`）：

| OSV 字段 | 目标字段 |
|---|---|
| `id` | `id` |
| `aliases` (正则 `^CVE-`) | `cve[]` |
| `aliases` (正则 `^GHSA-`) | `ghsa[]` |
| `summary` | `summary` |
| `severity[].score` (CVSS_V3) | `cvss_score` / `cvss_vector` |
| `affected[0].ranges[0].events` | `affected_range` / `fixed_versions[]` |
| `references[type=WEB][0].url` | `advisory_url` |
| 派生 `https://nvd.nist.gov/vuln/detail/<CVE>` | `nvd_url` |
| `published` | `published_at` |
| `database_specific.cvss.score` | 优先于 `severity[]` |

**严重度分级**（CVSS 缺失时回落到 GHSA severity）：
- 9.0-10.0 → Critical
- 7.0-8.9 → High
- 4.0-6.9 → Medium
- 0.1-3.9 → Low
- 缺失 → Unknown（默认从升级 finding 列表里排除）

**Ecosystem 映射**（在 `scripts/ecosystems.py` 集中管理）：

| Manifest | OSV ecosystem |
|---|---|
| `package.json` | `npm` |
| `requirements.txt` / `pyproject.toml` / `setup.py` / `Pipfile` | `PyPI` |
| `pom.xml` / `build.gradle` / `build.gradle.kts` | `Maven` |
| `composer.json` | `Packagist` |
| `go.mod` | `Go` |
| `Gemfile` | `RubyGems` |
| `Cargo.toml` | `crates.io` |
| `*.csproj` / `packages.config` | `NuGet` |

## 7.3 离线缓存

**位置**：`payloads/vulnerable-ranges.json`（带 schema `vulnerable-ranges.schema.json`）。

**Key 格式**：`<ecosystem>:<name>:<version>` —— PyPI 与 npm 包名 lowercase 后做 key，保证命中稳定。

**刷新机制**：

- 维护者跑 `python scripts/build_cve_cache.py --progress`
- 默认种子文件 `scripts/seed_packages.json` 覆盖 36 个高使用率包
- 可手动编辑 seed 添加自定义包
- 建议每周刷新一次

**陈旧策略**：
- 缓存 `generated_at` > 90 天 → Dashboard 软提示「缓存可能过期」
- 不硬阻断（旧数据 > 无数据）

## 7.4 限流与退避

- OSV.dev 没有公开 rate limit；保守默认 **4 并发** + 1s 间隔
- HTTP 429 / 5xx → 指数退避最多 3 次（间隔 1s / 2s / 4s）
- 包不存在（4xx）静默忽略，`queries_failed++` 不影响其它包
- `--rate 1` 可调更保守，`--rate 10` 调到上限

## 7.5 报告集成

`scripts/render_report.py` 新增 `--cve-input <path>` flag：

- 默认空 → 不渲染「依赖 CVE」section（向后兼容）
- 传入 `dependency_cve.json` → 渲染 `partials/dependency_cve.html.j2` partial
- Jinja 上下文变量：
  - `cve_findings` (list, 一行一 advisory)
  - `cve_findings_count` (int)
  - `cve_by_severity` (dict)
  - `cve_source` ("online" / "offline-cache" / "mixed" / "none")
  - `cve_queries_total` / `cve_queries_cached`

## 7.6 已知边界

1. **lockfile 不解析**（V1.3 计划）—— 可能「过度报告」。
2. **传递依赖不解析**（V1.3 计划）—— 只扫直接依赖。
3. **Maven artifactId 切分**——`com.foo:bar:1.2.3` 取 `bar` 作为 OSV key；OSV 实际也是用 artifactId，匹配良好。
4. **npm scope**——`@scope/name` 保留完整大小写。
5. **Go module path**——保留完整路径（`github.com/gin-gonic/gin` 不截断到 `gin`）。
6. **PyYAML `<5.4`** 等「宽松范围」—— OSV 服务端做匹配，本地不再二次解析。
7. **CVSS 缺失**——回落到 GHSA severity；都没有则标 `Unknown`。
8. **CVE alias 缺失**——`nvd_url` 回落到 OSV advisory URL。

## 7.7 测试

```bash
# 跑全套 smoke test（38 项断言，含 8 项 V1.2 CVE 相关）
python tests/smoke_test.py

# 离线模式跑一遍 sample_repo
python scripts/cve_lookup.py tests/fixtures/sample_repo \
    --offline --output /tmp/dep_cve.json

# 渲染并肉眼检查「依赖 CVE」section
python scripts/render_report.py \
    --findings tests/fixtures/findings.json \
    --assets tests/fixtures/assets.json \
    --profile tests/fixtures/framework_profile.json \
    --execution-log tests/fixtures/execution.log \
    --cve-input /tmp/dep_cve.json \
    --output /tmp/report.html
```
