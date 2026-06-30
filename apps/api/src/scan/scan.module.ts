import { Module } from '@nestjs/common';
import { ScanPlannerService } from './scan-planner.service';

/** Partial — ScanController / ScanRunner / ScanQueue in Phase 3. */
@Module({
  providers: [ScanPlannerService],
  exports: [ScanPlannerService],
})
export class ScanModule {}