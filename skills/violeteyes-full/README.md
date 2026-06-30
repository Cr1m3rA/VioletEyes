# violeteyes-full

> VioletEyes v1.2.0 原版 orchestrator skill —— 直接迁自仓库根目录的 `SKILL.md` / `skill.json` / `system-prompt.md`。

## 角色

- **kind**: `orchestrator`
- **mandatory**: ✅ —— `violeteyes-full` 不可删除，Deep 模式强制加载
- **bundleVersionId**: `sbv-violeteyes-full-builtin`（系统预置，admin 不可停用）

## 来源说明

本目录的三个文件与仓库根的同名文件**内容完全一致**，定期同步（Phase 6 CI 增加 `pnpm run sync:violeteyes-skill` 脚本）。

修改其中一份必须同步另一份。

## 加载入口

`apps/api/src/skills/builtin/violeteyes-full.service.ts` 加载本目录 `SKILL.md` 并通过 Agent Runtime 调度。

## 文档

- [VioletEyes Skill 文档](../../docs/01-architecture.md)
- [5 阶段流水线](../../docs/03-code-reading-strategy.md)
- [漏洞分类](../../docs/04-vulnerability-catalog.md)