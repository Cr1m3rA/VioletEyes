import {
  Controller,
  Get,
  Post,
  Param,
  Body,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  HttpCode,
  HttpStatus,
  BadRequestException,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { CurrentUser } from '../auth/current-user.decorator';
import { CodeVersionsService } from './code-versions.service';
import { ProjectRoleGuard, ProjectRoles } from '../projects/project-role.guard';
import { ProjectRole } from '@violeteyes/shared';
import { z } from 'zod';
import { ZodValidationPipe } from '../common/zod-validation.pipe';
import type { JwtPayload } from '../auth/jwt.strategy';

const FromGitSchema = z.object({
  url: z.string().min(1),
  ref: z.string().optional(),
  credentialsLabel: z.string().optional(),
});

const FromGithubSchema = z.object({
  owner: z.string().min(1),
  repo: z.string().min(1),
  ref: z.string().optional(),
  credentialsLabel: z.string().optional(),
});

@Controller('projects/:id/code-versions')
@UseGuards(ProjectRoleGuard)
export class CodeVersionsController {
  constructor(private readonly versions: CodeVersionsService) {}

  @Get()
  @ProjectRoles(ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER)
  list(@CurrentUser() _user: JwtPayload, @Param('id') id: string) {
    return this.versions.list({ projectId: id });
  }

  @Get(':versionId')
  @ProjectRoles(ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER)
  findOne(@CurrentUser() _user: JwtPayload, @Param('id') id: string, @Param('versionId') versionId: string) {
    return this.versions.findById({ id: versionId, projectId: id });
  }

  @Post('upload')
  @HttpCode(HttpStatus.CREATED)
  @ProjectRoles(ProjectRole.OWNER, ProjectRole.EDITOR)
  @UseInterceptors(FileInterceptor('file', { limits: { fileSize: 500 * 1024 * 1024 } }))
  async upload(
    @CurrentUser() user: JwtPayload,
    @Param('id') id: string,
    @UploadedFile() file: { buffer: Buffer; originalname: string } | undefined,
  ) {
    if (!file) throw new BadRequestException('file is required');
    return this.versions.createFromZip({ projectId: id, uploadedBy: user.sub, file });
  }

  @Post('from-git')
  @HttpCode(HttpStatus.CREATED)
  @ProjectRoles(ProjectRole.OWNER, ProjectRole.EDITOR)
  fromGit(
    @CurrentUser() user: JwtPayload,
    @Param('id') id: string,
    @Body(new ZodValidationPipe(FromGitSchema)) body: z.infer<typeof FromGitSchema>,
  ) {
    return this.versions.createFromGit({
      projectId: id,
      sourceRef: body,
      clonedBy: user.sub,
    });
  }

  @Post('from-github')
  @HttpCode(HttpStatus.CREATED)
  @ProjectRoles(ProjectRole.OWNER, ProjectRole.EDITOR)
  fromGithub(
    @CurrentUser() user: JwtPayload,
    @Param('id') id: string,
    @Body(new ZodValidationPipe(FromGithubSchema)) body: z.infer<typeof FromGithubSchema>,
  ) {
    return this.versions.createFromGitHub({ projectId: id, clonedBy: user.sub, ...body });
  }
}