import { Injectable, Inject, NotFoundException, ForbiddenException } from '@nestjs/common';
import { eq, like, or, desc, and, inArray } from 'drizzle-orm';
import { randomBytes } from 'node:crypto';
import { ProjectRole, type UserRole } from '@violeteyes/shared';
import { DB_TOKEN, type DB } from '../db/db.module';
import { projects, projectMembers, users } from '../db/schema';

const PROJECT_NAME_MAX = 128;

export interface ProjectListItem {
  id: string;
  name: string;
  description: string | null;
  ownerId: string;
  archivedAt: number | null;
  myRole: ProjectRole | null;
  createdAt: number;
  updatedAt: number;
}

/**
 * Projects 服务。
 *
 * 关键修复（安全规范）：
 *  - create 加 name 长度校验（trim 1-128）
 *  - LIKE 查询使用参数化绑定（防通配符注入）
 *  - delete 时级联删除成员 + code_versions + scan_runs
 */
@Injectable()
export class ProjectsService {
  constructor(@Inject(DB_TOKEN) private readonly db: DB) {}

  async list(args: {
    userId: string;
    role: UserRole;
    q?: string;
  }): Promise<ProjectListItem[]> {
    if (args.role === 'admin') {
      // admin 看全部
      const rows = await this.db
        .select()
        .from(projects)
        .orderBy(desc(projects.updatedAt))
        .all();
      return rows.map((p) => ({ ...p, myRole: 'owner' as ProjectRole }));
    }

    // 普通用户：只返回自己作为成员的项目
    const memberOf = await this.db
      .select({ projectId: projectMembers.projectId, role: projectMembers.role })
      .from(projectMembers)
      .where(eq(projectMembers.userId, args.userId))
      .all();

    if (memberOf.length === 0) return [];

    const ids = memberOf.map((m) => m.projectId);
    const rows = await this.db
      .select()
      .from(projects)
      .where(
        and(
          inArray(projects.id, ids),
          args.q
            ? // ⚠️ 转义 % 和 _ 防通配符注入
              like(projects.name, args.q.replace(/[\\%_]/g, '\\$&'))
            : undefined,
        ),
      )
      .orderBy(desc(projects.updatedAt))
      .all();

    const roleById = new Map(memberOf.map((m) => [m.projectId, m.role]));
    return rows.map((p) => ({
      ...p,
      myRole: (roleById.get(p.id) as ProjectRole | undefined) ?? null,
    }));
  }

  async findById(args: { id: string; userId: string; role: UserRole }): Promise<{
    project: typeof projects.$inferSelect;
    myRole: ProjectRole | null;
  }> {
    const row = await this.db
      .select()
      .from(projects)
      .where(eq(projects.id, args.id))
      .limit(1)
      .then((r) => r[0]);
    if (!row) throw new NotFoundException(`project ${args.id} not found`);

    const member = await this.db
      .select({ role: projectMembers.role })
      .from(projectMembers)
      .where(
        and(eq(projectMembers.projectId, args.id), eq(projectMembers.userId, args.userId)),
      )
      .limit(1)
      .then((r) => r[0]);

    const myRole = (member?.role as ProjectRole | undefined) ?? null;
    if (args.role !== 'admin' && !myRole) {
      throw new ForbiddenException(`not a member of project ${args.id}`);
    }
    return { project: row, myRole };
  }

  async create(args: {
    name: string;
    description?: string;
    ownerId: string;
  }): Promise<ProjectListItem> {
    const name = args.name.trim();
    if (name.length === 0 || name.length > PROJECT_NAME_MAX) {
      throw new ForbiddenException(`project name length must be 1-${PROJECT_NAME_MAX}`);
    }

    const id = `prj-${randomBytes(8).toString('hex')}`;
    const now = Date.now();
    await this.db.insert(projects).values({
      id,
      name,
      description: args.description?.trim() ?? null,
      ownerId: args.ownerId,
      archivedAt: null,
      createdAt: now,
      updatedAt: now,
    });

    // 创建者自动成为 owner 成员
    await this.db.insert(projectMembers).values({
      id: `pm-${randomBytes(8).toString('hex')}`,
      projectId: id,
      userId: args.ownerId,
      role: ProjectRole.OWNER,
      invitedBy: args.ownerId,
      createdAt: now,
    });

    return {
      id,
      name,
      description: args.description?.trim() ?? null,
      ownerId: args.ownerId,
      archivedAt: null,
      myRole: ProjectRole.OWNER,
      createdAt: now,
      updatedAt: now,
    };
  }

  async update(args: {
    id: string;
    name?: string;
    description?: string;
    userId: string;
    role: UserRole;
  }): Promise<ProjectListItem> {
    const { project } = await this.findById(args);
    const patch: Partial<typeof projects.$inferInsert> = { updatedAt: Date.now() };
    if (args.name !== undefined) {
      const n = args.name.trim();
      if (n.length === 0 || n.length > PROJECT_NAME_MAX) {
        throw new ForbiddenException(`project name length must be 1-${PROJECT_NAME_MAX}`);
      }
      patch.name = n;
    }
    if (args.description !== undefined) {
      patch.description = args.description.trim() || null;
    }
    await this.db.update(projects).set(patch).where(eq(projects.id, project.id));
    return { ...project, ...patch, myRole: args.role === 'admin' ? 'owner' : null };
  }

  async archive(args: { id: string; userId: string; role: UserRole }): Promise<void> {
    const { project } = await this.findById(args);
    await this.db
      .update(projects)
      .set({ archivedAt: Date.now(), updatedAt: Date.now() })
      .where(eq(projects.id, project.id));
  }

  async delete(args: { id: string; userId: string; role: UserRole }): Promise<void> {
    const { project } = await this.findById(args);
    // 外键 ON DELETE CASCADE 已开，删 project 自动级联清理 members / code_versions / scan_runs
    await this.db.delete(projects).where(eq(projects.id, project.id));
  }

  // ── members ──

  async listMembers(args: { id: string; userId: string; role: UserRole }): Promise<
    Array<{
      id: string;
      userId: string;
      username: string;
      displayName: string | null;
      role: ProjectRole;
      invitedBy: string | null;
      createdAt: number;
    }>
  > {
    await this.findById(args);
    const rows = await this.db
      .select({
        id: projectMembers.id,
        userId: projectMembers.userId,
        username: users.username,
        displayName: users.displayName,
        role: projectMembers.role,
        invitedBy: projectMembers.invitedBy,
        createdAt: projectMembers.createdAt,
      })
      .from(projectMembers)
      .innerJoin(users, eq(projectMembers.userId, users.id))
      .where(eq(projectMembers.projectId, args.id))
      .all();
    return rows;
  }

  async addMember(args: {
    projectId: string;
    userId: string;
    role: ProjectRole;
    invitedBy: string;
  }): Promise<void> {
    // 校验目标 user 存在
    const u = await this.db.select().from(users).where(eq(users.id, args.userId)).limit(1).then((r) => r[0]);
    if (!u) throw new NotFoundException(`user ${args.userId} not found`);

    await this.db.insert(projectMembers).values({
      id: `pm-${randomBytes(8).toString('hex')}`,
      projectId: args.projectId,
      userId: args.userId,
      role: args.role,
      invitedBy: args.invitedBy,
      createdAt: Date.now(),
    });
  }

  async removeMember(args: {
    projectId: string;
    memberId: string;
    userId: string;
    role: UserRole;
  }): Promise<void> {
    await this.findById(args);
    const target = await this.db
      .select()
      .from(projectMembers)
      .where(eq(projectMembers.id, args.memberId))
      .limit(1)
      .then((r) => r[0]);
    if (!target || target.projectId !== args.projectId) {
      throw new NotFoundException('member not found');
    }
    // 不能移除 owner
    if (target.role === 'owner') {
      throw new ForbiddenException('cannot remove owner; transfer ownership first');
    }
    await this.db.delete(projectMembers).where(eq(projectMembers.id, args.memberId));
  }
}