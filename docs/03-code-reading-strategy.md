# 03 — 步进式代码读取策略

> 本文档是 VioletEyes 与"普通读代码"最大的区别——**如何不一次性拉全仓库**。

## 3.1 为什么不能 Read 整个仓库？

| 风险 | 影响 |
|---|---|
| Token 爆炸 | 一个 1 万行 Java 项目 → ~5M tokens → 单轮 Read 失败 |
| 上下文丢失 | LLM 在长上下文中注意力衰减，关键 sink 容易被忽略 |
| 噪声淹没信号 | 90% 代码与安全无关，混入后反而干扰 |
| 性能 | Read 整个目录会触发 IDE 等待 + Agent 多次重试 |

## 3.2 Read Queue 模型

```
read_queue = [入口文件, 配置文件, manifest]
              ↓ 读取
read_set   = {已读}
read_state = {file: {lines_read: [...], sinks: [...], imports: [...]}}
              ↓ 入队
read_queue += import(未读) + 同包扫描
              ↓ 重复
... 直到 token 预算耗尽或 read_queue 空
```

伪代码（Agent 实际推理时内化执行）：

```python
def audit(root):
    profile = recon(root)                    # Phase 1
    entry_points = find_entries(profile)     # Phase 2
    queue = entry_points + profile.configs
    read_set, findings = set(), []
    while queue and budget_left():
        path = queue.pop(0)
        if path in read_set: continue
        content = read(path, max=1500)
        read_set.add(path)
        new_sinks = match_sinks(content, path)
        findings += new_sinks
        for imp in extract_imports(content):
            if imp not in read_set and not is_test(imp):
                queue.append(imp)
    return findings
```

## 3.3 读取优先级

| 优先级 | 文件类型 | 理由 |
|---|---|---|
| P0 | `Application.java` / `app.py` / `main.go` / `server.js` / `public/index.php` | 入口 |
| P0 | `*Controller.java` / `views.py` / `router.go` / `*Controller.cs` | HTTP 入口 |
| P0 | `routes/web.php` / `urls.py` / `config/routes.rb` / `routes.go` | 路由表 |
| P1 | `*Service.java` / `services/*.py` / `services/*.js` | 业务逻辑 |
| P1 | `*Repository.java` / `models.py` / `models/*.js` | 数据访问层 |
| P1 | `application.yml` / `settings.py` / `.env` / `config.yaml` | 配置（密钥、DB、debug） |
| P2 | 自写工具类 / 中间件 / filter / interceptor | 共享逻辑 |
| P2 | `templates/*.html` / `*.vue` / `*.jsx` | 模板 / 前端组件 |
| P3 | `*Mapper.xml` (MyBatis) | SQL 集中地 |
| P3 | `*.proto` / `*.graphql` | API schema |
| P3 | `Dockerfile` / `docker-compose.yml` | 部署配置 |
| 跳过 | `node_modules/` / `target/` / `build/` / `dist/` / `__pycache__/` | 第三方/编译产物 |
| 跳过 | `*Test.java` / `*test.py` / `__tests__/` | 测试代码 |
| 跳过 | `*.md` / `LICENSE` / `CHANGELOG.md` / `docs/` | 文档 |
| 跳过 | `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` | 锁文件（巨大且与审计无关） |
| 跳过 | `*.min.js` / `*.map` | 压缩/SourceMap |
| 跳过 | `*.jar` / `*.class` / `*.pyc` / `*.so` / `*.dll` | 编译产物 |

## 3.4 文件分块读取

```python
def read_chunked(path, max_lines=1500, max_total=10000):
    chunks = []
    offset = 0
    while offset < max_total:
        try:
            chunk = read_file(path, offset=offset, limit=max_lines)
        except FileTooLarge:
            break
        if not chunk or not chunk.strip():
            break
        chunks.append((offset, chunk))
        offset += max_lines
    return chunks
```

读取后 LLM 对每块做局部 sink 匹配 + 跨块 import 追溯。

## 3.5 调用图展开策略

读到 `UserController.java` 后：

```java
package com.x.controller;
import com.x.service.UserService;        // → 入队 UserService.java
import com.x.dto.UserDTO;                 // → 入队 UserDTO.java
import org.springframework.web.bind.annotation.*;

@RestController
public class UserController {
    @Autowired
    private UserService userService;      // 字段类型 → 强化入队
    
    @GetMapping("/user/{id}")
    public UserDTO getUser(@PathVariable Long id) {
        return userService.findById(id);  // 调用 → 已入队
    }
    
    @PostMapping("/user")
    public UserDTO create(@RequestBody UserDTO dto) {
        return userService.create(dto);
    }
}
```

LLM 行为：
1. 标记 `@PathVariable Long id` 为 source（用户输入）
2. 标记 `userService.findById(id)` 为 sink（DB 查询）→ 入队
3. 读取 `UserService.java`：
   ```java
   public UserDTO findById(Long id) {
       return userRepository.findById(id).orElse(null);
   }
   ```
4. 判断：`findById` 是参数化查询 → **安全** → 不产生 finding
5. 检查 `create()` 是否对 `dto` 做权限校验 → 可能产生 IDOR/Mass-Assignment finding

## 3.6 典型 token 消耗

假设一个 Spring Boot 项目：

| 阶段 | 文件数 | 累计行数 | 累计 token (粗估) |
|---|---|---|---|
| Phase 1: 读 manifest + Application.java + application.yml | 3 | 600 | ~3K |
| Phase 2: 读 routes / controllers（自动扫包） | 10 | 3000 | ~18K |
| Phase 3: 展开 services + repositories | 20 | 6000 | ~40K |
| Phase 3: 展开 DTO / utils / 自写中间件 | 15 | 3000 | ~55K |
| Phase 4: 漏洞分析（LLM 推理） | - | - | ~80K |
| Phase 5: 渲染 HTML 报告 | - | - | ~20K |
| **合计** | ~50 | ~13K | **~120K-200K** |

与"Read 整个仓库"相比节省 **70%-80%**。

## 3.7 token 预算管理

```python
class TokenBudget:
    def __init__(self, total=200_000, hard_stop_ratio=0.9):
        self.total = total
        self.used = 0
        self.hard_stop = total * hard_stop_ratio
    
    def spend(self, n):
        self.used += n
        if self.used > self.hard_stop:
            raise BudgetExceeded()
    
    def remaining(self):
        return self.total - self.used
```

Agent 触发 BudgetExceeded 时：
1. 停止 Read
2. 已收 findings + 候选 sink 全部归档
3. 报告标注 `partial=true` / `coverage=<已读文件数>/<估计总文件数>`
4. 列出"未读文件 Top 20"作为附录

## 3.8 反模式（绝对不要做）

- ✗ 一次性 `Read` 整个目录 → 触发 IO 风暴
- ✗ 读 `package-lock.json`（> 100K 行）
- ✗ 读 `node_modules/**`（百万行）
- ✗ 读 `target/classes/**`（编译产物）
- ✗ 读 `*.min.js` / `*.map`
- ✗ 读 `dist/` / `build/`
- ✗ 读所有 `*Test.java` 找漏洞（测试代码不是产品）
- ✗ 读 `README.md` 找漏洞（文档）
- ✗ 多次读同一文件（用 read_set 去重）
- ✗ 不带 offset 读 > 100KB 文件

## 3.9 snippet 模式特殊处理

当 `source` 是文本片段（无目录结构）：

1. **语言识别**：
   - 用 `re` 匹配 import / 关键字 / 缩进风格
   - 兜底：用户输入 `language` 参数
2. **无需 import 追溯**：片段内自洽
3. **sink/source 推测**：
   - 看参数名（`userInput`, `username`, `query`）→ 推测 source
   - 看函数签名（`render_template_string`）→ 推断 sink
4. **confidence 上限**：
   - 缺调用链 → confidence ≤ Medium
   - 缺净化证据 → 标注 "需人工确认净化策略"
5. **报告标题改为"代码片段审计"**

## 3.10 增量 / diff 模式

当 `mode=diff` 或 `incremental`：

1. 优先输入 `git diff HEAD~1` 或 PR patch
2. 仅审计 diff 中的 `+` 行
3. 但**仍可读上下文**（同一函数的未变行）以判断 sink 是否被新引入
4. 报告 `mode=incremental` / `base_commit=...` / `head_commit=...`

## 3.11 失败回退

| 失败 | 回退 |
|---|---|
| 找不到 manifest | 改用扩展名比例：数 `.java` vs `.py` vs `.js` |
| 入口文件过大（>5000 行） | 提示用户指定入口 |
| read_queue 空但未发现 sink | 扩展：扫所有 `*Controller*` / `*router*` / `*handler*` |
| import 解析失败（动态语言） | 用 grep 找 "user_input" / "request" / "params" 关键词 |
| 配置加密 / 二进制 | 跳过 + 标注无法审计 |
