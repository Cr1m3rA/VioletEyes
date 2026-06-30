import { Module } from '@nestjs/common';
import { MulterModule } from '@nestjs/platform-express';
import { CodeVersionsController } from './code-versions.controller';
import { CodeVersionsService } from './code-versions.service';

@Module({
  imports: [MulterModule.register({ limits: { fileSize: 500 * 1024 * 1024 } })],
  controllers: [CodeVersionsController],
  providers: [CodeVersionsService],
  exports: [CodeVersionsService],
})
export class CodeVersionsModule {}