/**
 * Drizzle schema —— VioletEyes-neo 数据库。
 *
 * 对应 spec §3 数据模型（10 张主表 + 4 张关联表）。
 * 这里给核心表，详细字段在 Phase 1 migration 实施时补全。
 */

import { sqliteTable, text, integer, primaryKey, index, uniqueIndex } from 'drizzle-orm/sqlite-core';
import { sql } from 'drizzle-orm';

// ── Users + Refresh tokens (spec §3.1) ──

export const users = sqliteTable(
  'users',
  {
    id: text('id').primaryKey(),
    username: text('username').notNull(),
    email: text('email'),
    passwordHash: text('password_hash').notNull(),
    displayName: text('display_name'),
    role: text('role').notNull().default('auditor'), // 'admin' | 'auditor' | 'viewer'
    mustChangePassword: integer('must_change_password', { mode: 'boolean' }).notNull().default(false),
    lastLoginAt: integer('last_login_at'),
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
    updatedAt: integer('updated_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    usernameIdx: uniqueIndex('users_username_idx').on(t.username),
    emailIdx: uniqueIndex('users_email_idx').on(t.email),
  }),
);

export const refreshTokens = sqliteTable(
  'refresh_tokens',
  {
    id: text('id').primaryKey(),
    userId: text('user_id')
      .notNull()
      .references(() => users.id, { onDelete: 'cascade' }),
    deviceLabel: text('device_label'),
    userAgent: text('user_agent'),
    ip: text('ip'),
    expiresAt: integer('expires_at').notNull(),
    revokedAt: integer('revoked_at'),
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    userIdIdx: index('refresh_tokens_user_idx').on(t.userId),
  }),
);

// ── Projects + Members (spec §3.2) ──

export const projects = sqliteTable(
  'projects',
  {
    id: text('id').primaryKey(),
    name: text('name').notNull(),
    description: text('description'),
    ownerId: text('owner_id')
      .notNull()
      .references(() => users.id),
    archivedAt: integer('archived_at'),
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
    updatedAt: integer('updated_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    ownerIdx: index('projects_owner_idx').on(t.ownerId),
  }),
);

export const projectMembers = sqliteTable(
  'project_members',
  {
    id: text('id').primaryKey(),
    projectId: text('project_id')
      .notNull()
      .references(() => projects.id, { onDelete: 'cascade' }),
    userId: text('user_id')
      .notNull()
      .references(() => users.id, { onDelete: 'cascade' }),
    role: text('role').notNull(), // 'owner' | 'editor' | 'viewer'
    invitedBy: text('invited_by').references(() => users.id),
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    projectUserIdx: uniqueIndex('project_members_pu_idx').on(t.projectId, t.userId),
  }),
);

// ── Code versions (spec §3.3) ──

export const codeVersions = sqliteTable(
  'code_versions',
  {
    id: text('id').primaryKey(),
    projectId: text('project_id')
      .notNull()
      .references(() => projects.id, { onDelete: 'cascade' }),
    sourceType: text('source_type').notNull(), // 'zip' | 'git' | 'github'
    sourceRef: text('source_ref').notNull(),
    commitSha: text('commit_sha'),
    storagePath: text('storage_path').notNull(),
    sizeBytes: integer('size_bytes').notNull(),
    fileCount: integer('file_count').notNull().default(0),
    locByLang: text('loc_by_lang', { mode: 'json' }).$type<Record<string, number>>(),
    status: text('status').notNull().default('pending'), // 'pending' | 'ready' | 'failed'
    failureReason: text('failure_reason'),
    sha256: text('sha256').notNull(),
    createdBy: text('created_by')
      .notNull()
      .references(() => users.id),
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    projectIdx: index('code_versions_project_idx').on(t.projectId),
  }),
);

// ── Skill bundles (spec §3.4) ──

export const skillBundles = sqliteTable('skill_bundles', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  displayName: text('display_name').notNull(),
  kind: text('kind').notNull(),
  builtin: integer('builtin', { mode: 'boolean' }).notNull().default(false),
  description: text('description'),
  createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
});

export const skillBundleVersions = sqliteTable(
  'skill_bundle_versions',
  {
    id: text('id').primaryKey(),
    bundleId: text('bundle_id')
      .notNull()
      .references(() => skillBundles.id, { onDelete: 'cascade' }),
    version: text('version').notNull(),
    manifest: text('manifest', { mode: 'json' }).notNull(),
    manifestHash: text('manifest_hash').notNull(),
    snapshotPath: text('snapshot_path').notNull(),
    sizeBytes: integer('size_bytes').notNull(),
    signature: text('signature'),
    reviewStatus: text('review_status').notNull().default('pending'),
    reviewNote: text('review_note'),
    reviewedBy: text('reviewed_by').references(() => users.id),
    reviewedAt: integer('reviewed_at'),
    publishedAt: integer('published_at'),
    isActive: integer('is_active', { mode: 'boolean' }).notNull().default(true),
    isDefault: integer('is_default', { mode: 'boolean' }).notNull().default(false),
    createdBy: text('created_by')
      .notNull()
      .references(() => users.id),
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    bundleVersionIdx: uniqueIndex('skill_bundle_versions_bv_idx').on(t.bundleId, t.version),
  }),
);

export const projectSkillBindings = sqliteTable(
  'project_skill_bindings',
  {
    id: text('id').primaryKey(),
    projectId: text('project_id')
      .notNull()
      .references(() => projects.id, { onDelete: 'cascade' }),
    bundleVersionId: text('bundle_version_id')
      .notNull()
      .references(() => skillBundleVersions.id),
    enabled: integer('enabled', { mode: 'boolean' }).notNull().default(true),
    enabledBy: text('enabled_by')
      .notNull()
      .references(() => users.id),
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    projectSkillIdx: uniqueIndex('project_skill_bindings_ps_idx').on(t.projectId, t.bundleVersionId),
  }),
);

// ── Scan runs + executions (spec §3.5) ──

export const scanRuns = sqliteTable(
  'scan_runs',
  {
    id: text('id').primaryKey(),
    projectId: text('project_id')
      .notNull()
      .references(() => projects.id, { onDelete: 'cascade' }),
    codeVersionId: text('code_version_id')
      .notNull()
      .references(() => codeVersions.id),
    triggeredBy: text('triggered_by')
      .notNull()
      .references(() => users.id),
    scanMode: text('scan_mode').notNull(), // 'quick' | 'smart' | 'deep' | 'custom'
    skillPlan: text('skill_plan', { mode: 'json' }).notNull(),
    status: text('status').notNull().default('queued'),
    startedAt: integer('started_at'),
    finishedAt: integer('finished_at'),
    durationSec: integer('duration_sec'),
    cost: text('cost', { mode: 'json' }),
    failureReason: text('failure_reason'),
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    projectIdx: index('scan_runs_project_idx').on(t.projectId),
    statusIdx: index('scan_runs_status_idx').on(t.status),
  }),
);

export const skillExecutions = sqliteTable(
  'skill_executions',
  {
    id: text('id').primaryKey(),
    scanRunId: text('scan_run_id')
      .notNull()
      .references(() => scanRuns.id, { onDelete: 'cascade' }),
    bundleVersionId: text('bundle_version_id')
      .notNull()
      .references(() => skillBundleVersions.id),
    skillName: text('skill_name').notNull(),
    skillType: text('skill_type').notNull(),
    executionStatus: text('execution_status').notNull().default('not_run'),
    findingsStatus: text('findings_status').notNull().default('pending_verification'),
    primaryOutputs: text('primary_outputs', { mode: 'json' }).$type<string[]>(),
    dependsOn: text('depends_on', { mode: 'json' }).$type<string[]>(),
    traceRefs: text('trace_refs', { mode: 'json' }).$type<string[]>(),
    exploitability: text('exploitability'),
    notes: text('notes'),
    startedAt: integer('started_at').notNull(),
    finishedAt: integer('finished_at'),
    durationSec: integer('duration_sec'),
  },
  (t) => ({
    scanRunIdx: index('skill_executions_scan_run_idx').on(t.scanRunId),
  }),
);

// ── Findings + Vulnerability library (spec §3.6) ──

export const findings = sqliteTable(
  'findings',
  {
    id: text('id').primaryKey(),
    scanRunId: text('scan_run_id')
      .notNull()
      .references(() => scanRuns.id, { onDelete: 'cascade' }),
    bundleVersionId: text('bundle_version_id')
      .notNull()
      .references(() => skillBundleVersions.id),
    skillName: text('skill_name').notNull(),
    fingerprint: text('fingerprint').notNull(),
    title: text('title').notNull(),
    severity: text('severity').notNull(),
    cwe: text('cwe'),
    vulnClass: text('vuln_class'),
    filePath: text('file_path').notNull(),
    startLine: integer('start_line').notNull(),
    endLine: integer('end_line').notNull(),
    snippet: text('snippet').notNull(),
    callChain: text('call_chain', { mode: 'json' }),
    fixBefore: text('fix_before'),
    fixAfter: text('fix_after'),
    references: text('references', { mode: 'json' }).$type<string[]>(),
    rawMetadata: text('raw_metadata', { mode: 'json' }),
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    fingerprintIdx: index('findings_fingerprint_idx').on(t.fingerprint),
    scanRunIdx: index('findings_scan_run_idx').on(t.scanRunId),
  }),
);

export const vulnerabilities = sqliteTable(
  'vulnerabilities',
  {
    id: text('id').primaryKey(),
    fingerprint: text('fingerprint').notNull().unique(),
    title: text('title').notNull(),
    severity: text('severity').notNull(),
    cwe: text('cwe'),
    vulnClass: text('vuln_class'),
    firstSeenAt: integer('first_seen_at').notNull(),
    lastSeenAt: integer('last_seen_at').notNull(),
    occurrenceCount: integer('occurrence_count').notNull().default(1),
    status: text('status').notNull().default('open'), // 'open' | 'confirmed' | 'ignored' | 'fixed'
    confirmedBy: text('confirmed_by').references(() => users.id),
    confirmedAt: integer('confirmed_at'),
    ignoredBy: text('ignored_by').references(() => users.id),
    ignoredAt: integer('ignored_at'),
    ignoreReason: text('ignore_reason'),
    fixedAt: integer('fixed_at'),
    notes: text('notes'),
  },
  (t) => ({
    severityIdx: index('vulnerabilities_severity_idx').on(t.severity),
    statusIdx: index('vulnerabilities_status_idx').on(t.status),
  }),
);

export const findingOccurrences = sqliteTable(
  'finding_occurrences',
  {
    id: text('id').primaryKey(),
    findingId: text('finding_id')
      .notNull()
      .references(() => findings.id, { onDelete: 'cascade' }),
    vulnId: text('vuln_id')
      .notNull()
      .references(() => vulnerabilities.id, { onDelete: 'cascade' }),
    scanRunId: text('scan_run_id')
      .notNull()
      .references(() => scanRuns.id, { onDelete: 'cascade' }),
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    findingVulnIdx: uniqueIndex('finding_occurrences_fv_idx').on(t.findingId, t.vulnId),
  }),
);

// ── Reports + Agent traces (spec §3.7 + §3.8) ──

export const reports = sqliteTable('reports', {
  id: text('id').primaryKey(),
  scanRunId: text('scan_run_id')
    .notNull()
    .references(() => scanRuns.id, { onDelete: 'cascade' }),
  format: text('format').notNull(), // 'markdown' | 'json' | 'html' | 'archive'
  storagePath: text('storage_path').notNull(),
  sizeBytes: integer('size_bytes').notNull(),
  generatedAt: integer('generated_at').notNull().default(sql`(unixepoch() * 1000)`),
  generatedBy: text('generated_by')
    .notNull()
    .references(() => users.id),
});

export const agentTraces = sqliteTable(
  'agent_traces',
  {
    id: text('id').primaryKey(),
    scanRunId: text('scan_run_id')
      .notNull()
      .references(() => scanRuns.id, { onDelete: 'cascade' }),
    skillExecId: text('skill_exec_id').references(() => skillExecutions.id, { onDelete: 'set null' }),
    sequence: integer('sequence').notNull(),
    eventType: text('event_type').notNull(),
    payload: text('payload', { mode: 'json' }).notNull(),
    inputTokens: integer('input_tokens'),
    outputTokens: integer('output_tokens'),
    costUsd: integer('cost_usd'), // store as integer micro-USD to avoid float
    createdAt: integer('created_at').notNull().default(sql`(unixepoch() * 1000)`),
  },
  (t) => ({
    scanRunSeqIdx: index('agent_traces_run_seq_idx').on(t.scanRunId, t.sequence),
  }),
);