import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Param,
  Body,
  Query,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import { ProjectsService } from './projects.service';
import { CurrentUser } from '../auth/current-user.decorator';
import { CreateProjectDto, UpdateProjectDto, AddMemberDto } from './dto';
import { ProjectRoleGuard, ProjectRoles } from './project-role.guard';
import { ProjectRole } from '@violeteyes/shared';
import type { JwtPayload } from '../auth/jwt.strategy';

/**
 * Projects REST 端点。
 *
 * 权限：
 *  - list / create：所有登录用户
 *  - 单项目操作：ProjectRoleGuard 校验（默认 editor 起步，删除/归档需 owner）
 *  - 成员管理：owner only
 */
@Controller('projects')
@UseGuards(ProjectRoleGuard)
export class ProjectsController {
  constructor(private readonly projects: ProjectsService) {}

  @Get()
  list(
    @CurrentUser() user: JwtPayload,
    @Query('q') q?: string,
  ) {
    return this.projects.list({ userId: user.sub, role: user.role, q });
  }

  @Post()
  @HttpCode(HttpStatus.CREATED)
  create(@CurrentUser() user: JwtPayload, @Body() dto: CreateProjectDto) {
    return this.projects.create({
      name: dto.name,
      description: dto.description,
      ownerId: user.sub,
    });
  }

  @Get(':id')
  @ProjectRoles(ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER)
  findOne(@CurrentUser() user: JwtPayload, @Param('id') id: string) {
    return this.projects.findById({ id, userId: user.sub, role: user.role });
  }

  @Patch(':id')
  @ProjectRoles(ProjectRole.OWNER, ProjectRole.EDITOR)
  update(
    @CurrentUser() user: JwtPayload,
    @Param('id') id: string,
    @Body() dto: UpdateProjectDto,
  ) {
    return this.projects.update({ id, userId: user.sub, role: user.role, ...dto });
  }

  @Post(':id/archive')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ProjectRoles(ProjectRole.OWNER)
  archive(@CurrentUser() user: JwtPayload, @Param('id') id: string) {
    return this.projects.archive({ id, userId: user.sub, role: user.role });
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ProjectRoles(ProjectRole.OWNER)
  delete(@CurrentUser() user: JwtPayload, @Param('id') id: string) {
    return this.projects.delete({ id, userId: user.sub, role: user.role });
  }

  // ── members ──

  @Get(':id/members')
  @ProjectRoles(ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER)
  listMembers(@CurrentUser() user: JwtPayload, @Param('id') id: string) {
    return this.projects.listMembers({ id, userId: user.sub, role: user.role });
  }

  @Post(':id/members')
  @HttpCode(HttpStatus.CREATED)
  @ProjectRoles(ProjectRole.OWNER)
  addMember(
    @CurrentUser() user: JwtPayload,
    @Param('id') id: string,
    @Body() dto: AddMemberDto,
  ) {
    return this.projects.addMember({
      projectId: id,
      userId: dto.userId,
      role: dto.role,
      invitedBy: user.sub,
    });
  }

  @Delete(':id/members/:memberId')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ProjectRoles(ProjectRole.OWNER)
  removeMember(
    @CurrentUser() user: JwtPayload,
    @Param('id') id: string,
    @Param('memberId') memberId: string,
  ) {
    return this.projects.removeMember({
      projectId: id,
      memberId,
      userId: user.sub,
      role: user.role,
    });
  }
}