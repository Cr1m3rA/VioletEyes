import { Injectable, Inject } from '@nestjs/common';
import { eq, and, inArray } from 'drizzle-orm';
import { ScanMode, type SmartDecision, type SkillPlan } from '@violeteyes/shared';
import { DB_TOKEN, type DB } from '../db/db.module';
import { skillBundleVersions, projectSkillBindings } from '../db/schema';

/**
 * Scan Planner（spec §5.4）。
 *
 * 4 种模式的 skill 决策逻辑：
 *  - QUICK  : user-selectedSkillIds ∩ project.enabledSkills（不加载 violeteyes-full）
 *  - SMART  : violeteyes-full（强制） + LLM 自主从 project.enabledSkills 中挑选（无 user selection）
 *  - DEEP   : violeteyes-full（强制） + project.enabledSkills 全加载
 *  - CUSTOM : user-selectedSkillIds（不自动加载 violeteyes-full）
 *
 * 2026-06-30 拍板：Smart 模式不存在用户勾选，由 LLM 自主决定。
 */
@Injectable()
export class ScanPlannerService {
  constructor(@Inject(DB_TOKEN) private readonly db: DB) {}

  /**
   * QUICK / DEEP / CUSTOM 的静态 plan。
   * SMART 由 LLM 动态决定，需要单独走 planSmart()。
   */
  async planStatic(args: {
    projectId: string;
    codeVersionId: string;
    scanMode: Exclude<ScanMode, 'SMART'>;
    userSelectedSkillIds?: string[]; // 仅 CUSTOM 使用
  }): Promise<SkillPlan> {
    const enabledSkills = await this.loadEnabledSkills(args.projectId);

    switch (args.scanMode) {
      case ScanMode.QUICK: {
        const ids = args.userSelectedSkillIds ?? [];
        const filtered = enabledSkills.filter((s) => ids.includes(s.bundleVersionId));
        return { skills: filtered.map(toSkillEntry) };
      }

      case ScanMode.DEEP: {
        const violeteyes = await this.loadBuiltinVioletEyes();
        const allEnabled = enabledSkills.map(toSkillEntry);
        // violeteyes-full 排第一位，其余按 enabled 顺序
        return {
          skills: [toSkillEntry(violeteyes), ...allEnabled.filter((s) => s.bundleVersionId !== violeteyes.id)],
        };
      }

      case ScanMode.CUSTOM: {
        const ids = args.userSelectedSkillIds ?? [];
        // CUSTOM 可加载任意 skill（不限于 enabled），但需校验 bundleVersion 存在
        if (ids.length === 0) return { skills: [] };
        const found = await this.db
          .select()
          .from(skillBundleVersions)
          .where(inArray(skillBundleVersions.id, ids))
          .all();
        return { skills: found.map(toSkillEntry) };
      }
    }
  }

  /**
   * SMART 模式：先让 LLM 决策，再构造 plan。
   *
   * LLM 仅从 project.enabledSkills 中挑选（2026-06-30 决策）。
   */
  async planSmart(args: {
    projectId: string;
    frameworkProfile?: unknown; // 从 framework-detect skill 产出
    assets?: unknown;
  }): Promise<SkillPlan> {
    const enabledSkills = await this.loadEnabledSkills(args.projectId);
    const violeteyes = await this.loadBuiltinVioletEyes();

    // 调用 LLM 决策（具体实现见 ScanRunnerService.smartDecision）
    // 这里只是占位，实际 LLM call 在 runner 里做，避免 planner 阻塞
    // runner 会回填 decision 后写回 scan_runs.skillPlan.smartDecision
    return {
      skills: [toSkillEntry(violeteyes)], // 先只放 violeteyes-full；runner 会追加 LLM 选中的
      // smartDecision 由 runner 写入
    };
  }

  /**
   * Runner 在拿到 LLM decision 后，构造完整 plan。
   */
  buildSmartPlan(args: {
    violeteyesSkill: { bundleVersionId: string; skillName: string; kind: string };
    enabledSkills: Array<{ bundleVersionId: string; skillName: string; kind: string }>;
    decision: SmartDecision;
  }): SkillPlan {
    const allowedIds = new Set(args.enabledSkills.map((s) => s.bundleVersionId));
    const selected = args.decision.selectedSkills.filter((s) =>
      allowedIds.has(s.bundleVersionId),
    );
    const selectedEntries = selected.map((s) => {
      const e = args.enabledSkills.find((x) => x.bundleVersionId === s.bundleVersionId)!;
      return { bundleVersionId: e.bundleVersionId, skillName: e.skillName, kind: e.kind };
    });

    return {
      skills: [args.violeteyesSkill, ...selectedEntries],
      smartDecision: args.decision,
    };
  }

  // ── helpers ──

  private async loadEnabledSkills(projectId: string): Promise<
    Array<{
      bundleVersionId: string;
      skillName: string;
      kind: string;
    }>
  > {
    const rows = await this.db
      .select({
        bundleVersionId: skillBundleVersions.id,
        skillName: skillBundles.name,
        kind: skillBundles.kind,
      })
      .from(projectSkillBindings)
      .innerJoin(skillBundleVersions, eq(projectSkillBindings.bundleVersionId, skillBundleVersions.id))
      .innerJoin(skillBundles, eq(skillBundleVersions.bundleId, skillBundles.id))
      .where(and(eq(projectSkillBindings.projectId, projectId), eq(projectSkillBindings.enabled, true)))
      .all();

    return rows;
  }

  private async loadBuiltinVioletEyes() {
    const rows = await this.db
      .select({
        bundleVersionId: skillBundleVersions.id,
        skillName: skillBundles.name,
        kind: skillBundles.kind,
      })
      .from(skillBundleVersions)
      .innerJoin(skillBundles, eq(skillBundleVersions.bundleId, skillBundles.id))
      .where(and(eq(skillBundles.builtin, true), eq(skillBundles.name, 'violeteyes-full')))
      .limit(1)
      .all();
    if (rows.length === 0) {
      throw new Error('violeteyes-full builtin skill not found in DB — run seed');
    }
    return rows[0];
  }
}

function toSkillEntry(s: { bundleVersionId: string; skillName: string; kind: string }) {
  return { bundleVersionId: s.bundleVersionId, skillName: s.skillName, kind: s.kind };
}