import { Module } from '@nestjs/common';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { ProjectsModule } from './projects/projects.module';
import { CodeVersionsModule } from './code-versions/code-versions.module';
import { SkillBundlesModule } from './skill-bundles/skill-bundles.module';
import { SkillBindingsModule } from './skill-bindings/skill-bindings.module';
import { ScanModule } from './scan/scan.module';
import { SkillExecutionModule } from './skill-execution/skill-execution.module';
import { VulnerabilitiesModule } from './vulnerabilities/vulnerabilities.module';
import { ReportsModule } from './reports/reports.module';
import { AgentTracesModule } from './agent-traces/agent-traces.module';
import { RealtimeModule } from './realtime/realtime.module';
import { SettingsModule } from './settings/settings.module';
import { AdminModule } from './admin/admin.module';
import { HealthModule } from './health/health.module';
import { MetricsModule } from './metrics/metrics.module';
import { DbModule } from './db/db.module';

@Module({
  imports: [
    DbModule,
    AuthModule,
    UsersModule,
    ProjectsModule,
    CodeVersionsModule,
    SkillBundlesModule,
    SkillBindingsModule,
    ScanModule,
    SkillExecutionModule,
    VulnerabilitiesModule,
    ReportsModule,
    AgentTracesModule,
    RealtimeModule,
    SettingsModule,
    AdminModule,
    HealthModule,
    MetricsModule,
  ],
})
export class AppModule {}