import { Module } from '@nestjs/common';
import { ProjectsController } from './projects.controller';
import { ProjectsService } from './projects.service';
import { ProjectRoleGuard } from './project-role.guard';

@Module({
  controllers: [ProjectsController],
  providers: [ProjectsService, ProjectRoleGuard],
  exports: [ProjectsService, ProjectRoleGuard],
})
export class ProjectsModule {}