/**
 * SKILL.md front-matter schema (TS, zod-based).
 * 对应 spec §5.2 + Python 等价实现 src/py/skill_schema.py。
 */

import { z } from 'zod';

// ── 枚举（与 packages/shared/src/enums.ts 对齐；这里重新定义避免循环依赖）──

export const SKILL_KINDS = [
  'orchestrator',
  'framework',
  'entry-point',
  'sink',
  'vuln-class',
  'supply-chain',
] as const;

export const SEVERITIES = ['info', 'low', 'medium', 'high', 'critical'] as const;

export const RUNTIME_MODELS = ['claude-opus-4-8', 'claude-sonnet-4-6', 'claude-haiku-4-5', 'gpt-4o'] as const;

// ── 子 schema ──

const CapabilityModeSchema = z.object({
  name: z.string().min(1).max(64),
  tools_count: z.number().int().min(0).max(100),
  enables: z.array(z.string().min(1).max(64)).max(100),
});

const InputSchema = z.object({
  name: z.string().min(1).max(64),
  type: z.enum(['path', 'string', 'integer', 'enum', 'boolean', 'array', 'object']),
  required: z.boolean().optional().default(false),
  description: z.string().max(512).optional(),
  enum: z.array(z.string()).optional(),
  default: z.unknown().optional(),
  min: z.number().optional(),
  max: z.number().optional(),
});

const OutputSchema = z.object({
  name: z.string().min(1).max(64),
  type: z.enum(['path', 'string', 'integer', 'enum', 'boolean', 'array', 'object']),
  schemaRef: z.string().optional(),
});

const RuntimeSchema = z.object({
  model: z.enum(RUNTIME_MODELS).optional(),
  temperature: z.number().min(0).max(2).optional(),
  max_tokens: z.number().int().min(256).max(200_000).optional(),
  max_iterations: z.number().int().min(1).max(100).optional(),
});

const AuthorSchema = z
  .object({
    name: z.string().min(1).max(128),
    email: z.string().email().optional(),
  })
  .or(z.string().min(1).max(128)); // 简写："name <email>"

// ── 主 schema ──

export const SkillFrontmatterSchema = z.object({
  name: z
    .string()
    .min(1)
    .max(64)
    .regex(/^[a-z0-9][a-z0-9-]*$/, 'name must be kebab-case'),
  displayName: z.string().min(1).max(128),
  version: z
    .string()
    .regex(/^\d+\.\d+\.\d+(-[a-z0-9.]+)?$/, 'version must be semver'),
  author: AuthorSchema,
  license: z.string().min(1).max(64),
  description: z.string().min(1).max(1024),

  kind: z.enum(SKILL_KINDS),

  targetLanguages: z.array(z.string().min(1).max(32)).max(50).default([]),
  targetFrameworks: z.array(z.string().min(1).max(64)).max(200).default([]),
  targetVulnClasses: z.array(z.string().regex(/^CWE-\d+$/)).max(200).default([]),
  targetManifests: z.array(z.string().min(1).max(64)).max(50).default([]),

  inputs: z.array(InputSchema).max(50).default([]),
  outputs: z.array(OutputSchema).max(50).default([]),

  capability_modes: z.array(CapabilityModeSchema).min(1).max(10),

  mcp_dependencies: z.array(z.string()).max(20).default([]),
  runtime: RuntimeSchema.optional(),

  tags: z.array(z.string().min(1).max(32)).max(20).default([]),
  homepage: z.string().url().optional(),
  repository: z.string().url().optional(),
});

export type SkillFrontmatter = z.infer<typeof SkillFrontmatterSchema>;

/**
 * 危险模式检测（spec §5.3.1 "自动审核 — Lint 阶段"）
 * 用于检查 scripts/*.py 里是否调用了高危函数。
 */
export const DANGEROUS_PATTERNS = [
  { pattern: /\beval\s*\(/g, name: 'eval', severity: 'critical' },
  { pattern: /\bexec\s*\(/g, name: 'exec', severity: 'critical' },
  { pattern: /\bos\.system\s*\(/g, name: 'os.system', severity: 'critical' },
  { pattern: /\bsubprocess\.[a-zA-Z_]+\s*\([^)]*shell\s*=\s*True/g, name: 'subprocess-shell-true', severity: 'critical' },
  { pattern: /\bchild_process\.exec\s*\(/g, name: 'child_process.exec', severity: 'critical' },
  { pattern: /\bcurl\s+/g, name: 'curl', severity: 'medium' },
  { pattern: /\bwget\s+/g, name: 'wget', severity: 'medium' },
  { pattern: /\bnc\s+-l/g, name: 'netcat-listen', severity: 'critical' },
] as const;

export interface LintFinding {
  rule: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  file: string;
  line?: number;
  snippet?: string;
  message: string;
}

/**
 * 跑一遍 lint 检查 skill 包内容。
 */
export function lintSkillPackage(
  files: Array<{ path: string; content: string }>,
  frontmatter: SkillFrontmatter,
): LintFinding[] {
  const findings: LintFinding[] = [];

  // 1. front-matter 必填字段已在 schema 校验
  if (frontmatter.targetLanguages.length === 0 && frontmatter.kind !== 'orchestrator') {
    findings.push({
      rule: 'missing-target-languages',
      severity: 'low',
      file: 'SKILL.md',
      message: 'non-orchestrator skills should declare targetLanguages',
    });
  }

  // 2. 危险模式扫描（只扫 scripts/*.py / *.sh / *.js）
  for (const file of files) {
    const isScript = /\.(py|sh|js|ts)$/.test(file.path) && file.path.includes('/scripts/');
    if (!isScript) continue;

    for (const rule of DANGEROUS_PATTERNS) {
      const matches = file.content.matchAll(rule.pattern);
      for (const match of matches) {
        const lineNumber = file.content.substring(0, match.index ?? 0).split('\n').length;
        findings.push({
          rule: `dangerous-pattern:${rule.name}`,
          severity: rule.severity as LintFinding['severity'],
          file: file.path,
          line: lineNumber,
          snippet: match[0],
          message: `dangerous pattern detected: ${rule.name}`,
        });
      }
    }
  }

  return findings;
}