/**
 * Finding data shape — 与 VioletEyes v1.2 templates/finding-schema.json 对齐。
 * 与 spec §3.6 findings / vulnerabilities 表字段映射。
 */

import type { Severity } from './enums';

export interface FindingCallChainStep {
  file: string;
  line: number;
  symbol: string;
  kind: 'source' | 'propagation' | 'sink' | 'sanitizer';
  note?: string;
}

export interface Finding {
  id: string; // find-<randomHex(16)>
  scanRunId: string;
  bundleVersionId: string;
  skillName: string;
  fingerprint: string; // sha256(file:line:cwe:snippet[:200])
  title: string;
  severity: Severity;
  cwe?: string; // e.g. "CWE-78"
  vulnClass?: string;
  filePath: string;
  startLine: number;
  endLine: number;
  snippet: string;
  callChain?: FindingCallChainStep[];
  fixBefore?: string;
  fixAfter?: string;
  references?: string[];
  rawMetadata?: Record<string, unknown>;
  createdAt: number; // unix ms
}

export interface Vulnerability {
  id: string;
  fingerprint: string;
  title: string;
  severity: Severity;
  cwe?: string;
  vulnClass?: string;
  firstSeenAt: number;
  lastSeenAt: number;
  occurrenceCount: number;
  status: 'open' | 'confirmed' | 'ignored' | 'fixed';
  confirmedBy?: string;
  confirmedAt?: number;
  ignoredBy?: string;
  ignoredAt?: number;
  ignoreReason?: string;
  fixedAt?: number;
  notes?: string;
}

/**
 * Scan cost aggregation (spec §3.7 "报告 Token 成本展示")
 */
export interface ScanCost {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  costUsd: number;
  byModel: Record<
    string,
    {
      inputTokens: number;
      outputTokens: number;
      costUsd: number;
    }
  >;
  bySkill: Record<
    string,
    {
      inputTokens: number;
      outputTokens: number;
      costUsd: number;
    }
  >;
}

/**
 * Smart 模式决策记录（spec §5.4）
 */
export interface SmartDecision {
  selectedSkills: Array<{
    bundleVersionId: string;
    skillName: string;
    reason: string; // e.g. "framework-matched:spring, vuln-class:CWE-78"
  }>;
  rejectedSkills: Array<{
    bundleVersionId: string;
    skillName: string;
    reason: string; // e.g. "no-xml-parsing-detected"
  }>;
  rationale: string; // 自然语言解释
  decidedAt: number;
  decidedByModel: string; // e.g. "claude-opus-4-8"
}

/**
 * SkillPlan — 写入 scan_runs.skillPlan（JSON 字段）
 */
export interface SkillPlan {
  skills: Array<{
    bundleVersionId: string;
    skillName: string;
    kind: string;
  }>;
  smartDecision?: SmartDecision; // 仅 SMART 模式
}