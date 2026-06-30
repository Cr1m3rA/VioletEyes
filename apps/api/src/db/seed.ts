import { eq } from 'drizzle-orm';
import { randomBytes } from 'node:crypto';
import * as argon2 from 'argon2';
import { DB_TOKEN, type DB } from './db.module';
import { users, skillBundles, skillBundleVersions } from './schema';
import { SkillKind } from '@violeteyes/shared';

/**
 * 初始 seed：创建 admin/admin123 用户 + 内置 violeteyes-full skill。
 *
 * 仅在 DB 为空时执行；已存在则跳过。
 *
 * 默认密码：admin123（首次登录**必须**改密）。
 */
export async function seedDatabase(db: DB): Promise<void> {
  // ── admin user ──
  const existingAdmin = await db
    .select()
    .from(users)
    .where(eq(users.username, 'admin'))
    .limit(1)
    .then((r) => r[0]);

  if (!existingAdmin) {
    const id = `usr-${randomBytes(8).toString('hex')}`;
    const passwordHash = await argon2.hash('admin123', {
      type: argon2.argon2id,
      timeCost: 2,
      memoryCost: 19456,
      parallelism: 1,
    });
    await db.insert(users).values({
      id,
      username: 'admin',
      email: 'admin@violeteyes.local',
      passwordHash,
      displayName: 'Administrator',
      role: 'admin',
      mustChangePassword: true,
      lastLoginAt: null,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
    // eslint-disable-next-line no-console
    console.info('[seed] admin user created (admin / admin123 — must change on first login)');
  } else {
    // eslint-disable-next-line no-console
    console.info('[seed] admin user already exists, skipping');
  }

  // ── builtin violeteyes-full skill ──
  const existingBundle = await db
    .select()
    .from(skillBundles)
    .where(eq(skillBundles.name, 'violeteyes-full'))
    .limit(1)
    .then((r) => r[0]);

  if (!existingBundle) {
    const bundleId = `sb-${randomBytes(8).toString('hex')}`;
    await db.insert(skillBundles).values({
      id: bundleId,
      name: 'violeteyes-full',
      displayName: 'VioletEyes 全量扫描',
      kind: SkillKind.ORCHESTRATOR,
      builtin: true,
      description: 'VioletEyes v1.2 原版 orchestrator skill',
      createdAt: Date.now(),
    });

    const versionId = `sbv-${randomBytes(8).toString('hex')}`;
    await db.insert(skillBundleVersions).values({
      id: versionId,
      bundleId,
      version: '1.2.0',
      manifest: {
        name: 'violeteyes-full',
        displayName: 'VioletEyes 全量扫描',
        version: '1.2.0',
        author: 'Cr1m3rA',
        license: 'Authorized-Testing-Only',
        description: 'VioletEyes v1.2 原版',
        kind: 'orchestrator',
        targetLanguages: [],
        targetFrameworks: [],
        capability_modes: [
          { name: 'smart', tools_count: 8, enables: ['filesystem.read', 'grep.search', 'framework.detect', 'cve.lookup'] },
        ],
      },
      manifestHash: '',
      snapshotPath: '../../skills/violeteyes-full',
      sizeBytes: 0,
      signature: null,
      reviewStatus: 'approved',
      reviewNote: 'builtin',
      reviewedBy: null,
      reviewedAt: Date.now(),
      publishedAt: Date.now(),
      isActive: true,
      isDefault: true,
      createdBy: '',
      createdAt: Date.now(),
    });

    // eslint-disable-next-line no-console
    console.info(`[seed] violeteyes-full skill seeded: ${versionId}`);
  }
}