import { Module } from '@nestjs/common';
import { ScanGateway } from './scan.gateway';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [AuthModule],
  providers: [ScanGateway],
  exports: [ScanGateway],
})
export class RealtimeModule {}