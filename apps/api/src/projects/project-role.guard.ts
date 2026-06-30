import {
  Injectable,
  CanActivate,
  ExecutionContext,
  ForbiddenException,
  NotFoundException,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Inject } from '@nestjs/common';
import { eq, and } from 'drizzle-orm';
import { ProjectRole, UserRole } from '@violeteyes/shared';
import { DB_TOKEN, type DB } from '../db/db.module';
import { projectMembers } from '../db/schema';
import type { JwtPayload } from '../auth/jwt.strategy';

export const PROJECT_ROLES_KEY = 'projectRoles';
export const ProjectRoles = (...roles: ProjectRole[]) =>
  Reflector.createDecorator<ProjectRole[]>()(roles);

/**
 * 项目成员角色守卫。
 *
 * 用法：
 *   @UseGuards(ProjectRoleGuard)
 *   @ProjectRoles(ProjectRole.OWNER, ProjectRole.EDITOR)
 *   @Post(':id/code-versions/upload')
 *
 * admin 自动拥有所有权限。
 */
@Injectable()
export class ProjectRoleGuard implements CanActivate {
  constructor(
    private reflector: Reflector,
    @Inject(DB_TOKEN) private readonly db: DB,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const required = this.reflector.getAllAndOverride<ProjectRole[] | undefined>(
      PROJECT_ROLES_KEY,
      [context.getHandler(), context.getClass()],
    );
    if (!required || required.length === 0) return true;

    const req = context.switchToHttp().getRequest<{
      user?: JwtPayload;
      params: { id?: string };
    }>();
    const user = req.user;
    if (!user) throw new ForbiddenException('not authenticated');

    // admin bypass
    if (user.role === UserRole.ADMIN) return true;

    const projectId = req.params.id;
    if (!projectId) throw new ForbiddenException('project id missing in route');

    const member = await this.db
      .select()
      .from(projectMembers)
      .where(
        and(eq(projectMembers.projectId, projectId), eq(projectMembers.userId, user.sub)),
      )
      .limit(1)
      .then((r) => r[0]);

    if (!member) throw new NotFoundException(`not a member of project ${projectId}`);

    if (!required.includes(member.role as ProjectRole)) {
      throw new ForbiddenException(
        `project role '${member.role}' not in [${required.join(', ')}]`,
      );
    }
    return true;
  }
}