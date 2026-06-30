/**
 * VioletEyes-neo shared enums (cross-package: api / web / agent-rpc).
 * Single source of truth — never duplicate in app code.
 */

export const Severity = {
  INFO: 'info',
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const;
export type Severity = (typeof Severity)[keyof typeof Severity];

export const SEVERITY_ORDER: Severity[] = [
  Severity.INFO,
  Severity.LOW,
  Severity.MEDIUM,
  Severity.HIGH,
  Severity.CRITICAL,
];

export const SEVERITY_HEX: Record<Severity, string> = {
  // 与 VioletEyes 报告 base.css 严格一致（spec §6.1）
  [Severity.CRITICAL]: '#dc2626', // rose-600
  [Severity.HIGH]: '#ea580c', // orange-600
  [Severity.MEDIUM]: '#ca8a04', // amber-600
  [Severity.LOW]: '#0891b2', // cyan-600
  [Severity.INFO]: '#64748b', // slate-500
};

export const UserRole = {
  ADMIN: 'admin',
  AUDITOR: 'auditor',
  VIEWER: 'viewer',
} as const;
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const ProjectRole = {
  OWNER: 'owner',
  EDITOR: 'editor',
  VIEWER: 'viewer',
} as const;
export type ProjectRole = (typeof ProjectRole)[keyof typeof ProjectRole];

export const ScanMode = {
  QUICK: 'quick',
  SMART: 'smart',
  DEEP: 'deep',
  CUSTOM: 'custom',
} as const;
export type ScanMode = (typeof ScanMode)[keyof typeof ScanMode];

export const ScanStatus = {
  QUEUED: 'queued',
  RUNNING: 'running',
  SUCCEEDED: 'succeeded',
  FAILED: 'failed',
  CANCELED: 'canceled',
} as const;
export type ScanStatus = (typeof ScanStatus)[keyof typeof ScanStatus];

export const SkillKind = {
  ORCHESTRATOR: 'orchestrator',
  FRAMEWORK: 'framework',
  ENTRY_POINT: 'entry-point',
  SINK: 'sink',
  VULN_CLASS: 'vuln-class',
  SUPPLY_CHAIN: 'supply-chain',
} as const;
export type SkillKind = (typeof SkillKind)[keyof typeof SkillKind];

export const SkillExecutionStatus = {
  NOT_RUN: 'not_run',
  INITIAL_SCREENED: 'initial_screened',
  PARTIAL: 'partial',
  COMPLETED: 'completed',
  NOT_APPLICABLE: 'not_applicable',
} as const;
export type SkillExecutionStatus = (typeof SkillExecutionStatus)[keyof typeof SkillExecutionStatus];

export const SkillReviewStatus = {
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
} as const;
export type SkillReviewStatus = (typeof SkillReviewStatus)[keyof typeof SkillReviewStatus];

export const VulnStatus = {
  OPEN: 'open',
  CONFIRMED: 'confirmed',
  IGNORED: 'ignored',
  FIXED: 'fixed',
} as const;
export type VulnStatus = (typeof VulnStatus)[keyof typeof VulnStatus];

export const ReportFormat = {
  MARKDOWN: 'markdown',
  JSON: 'json',
  HTML: 'html',
  ARCHIVE: 'archive',
} as const;
export type ReportFormat = (typeof ReportFormat)[keyof typeof ReportFormat];

export const SourceType = {
  ZIP: 'zip',
  GIT: 'git',
  GITHUB: 'github',
} as const;
export type SourceType = (typeof SourceType)[keyof typeof SourceType];

export const CodeVersionStatus = {
  PENDING: 'pending',
  READY: 'ready',
  FAILED: 'failed',
} as const;
export type CodeVersionStatus = (typeof CodeVersionStatus)[keyof typeof CodeVersionStatus];

export const AiProvider = {
  ANTHROPIC: 'anthropic',
  OPENAI: 'openai',
  CUSTOM: 'custom',
} as const;
export type AiProvider = (typeof AiProvider)[keyof typeof AiProvider];

export const TraceEventType = {
  LLM_MESSAGE: 'llm.message',
  TOOL_CALL: 'tool.call',
  TOOL_RESULT: 'tool.result',
  PHASE_TRANSITION: 'phase.transition',
  LOG: 'log',
  DECISION: 'decision',
} as const;
export type TraceEventType = (typeof TraceEventType)[keyof typeof TraceEventType];