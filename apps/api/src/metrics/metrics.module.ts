import { Module } from '@nestjs/common';
import { PrometheusModule } from '@willsoto/nestjs-prometheus';

/** Placeholder — full metrics in Phase 6. */
@Module({
  imports: [PrometheusModule.register()],
})
export class MetricsModule {}