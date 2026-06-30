import 'reflect-metadata';
import { NestFactory, Reflector } from '@nestjs/core';
import { ValidationPipe, Logger, INestApplication } from '@nestjs/common';
import cookieParser from 'cookie-parser';
import { AppModule } from './app.module';
import { JwtAuthGuard } from './auth/jwt-auth.guard';
import { RolesGuard } from './auth/roles.guard';
import { validateSecretsOrThrow } from './common/secret-strength';
import { AllExceptionsFilter } from './common/all-exceptions.filter';
import { setupBullBoard } from './admin/queue-board/queue-board.setup';
import { DB_TOKEN, type DB } from './db/db.module';
import { seedDatabase } from './db/seed';

/**
 * VioletEyes-neo API 入口。
 *
 * 关键安全约束：
 *  - 启动校验：JWT_SECRET / APP_MASTER_KEY / SESSION_SECRET 长度 ≥ 32 且高熵
 *  - JwtAuthGuard / RolesGuard 全局挂载（除 @Public()）
 *  - 全局 ValidationPipe（whitelist + forbidNonWhitelisted + transform）
 *  - cookie parser（refresh token 走 HttpOnly cookie）
 *  - Bull-Board 必须 Basic Auth 守护（env 强制）
 *  - CORS 白名单
 *  - 统一异常过滤器（不暴露 stacktrace 给客户端）
 */
async function bootstrap(): Promise<void> {
  // 1. 启动前校验密钥（需求 NFR-SEC-06）
  validateSecretsOrThrow();

  const app = await NestFactory.create(AppModule, {
    logger: ['error', 'warn', 'log'],
  });

  // 2. 全局 ValidationPipe（安全修复）
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
      transformOptions: { enableImplicitConversion: false },
      stopAtFirstError: false,
    }),
  );

  // 3. cookie parser（refresh token HttpOnly）
  app.use(cookieParser());

  // 4. 全局 Guards（安全修复）
  const reflector = app.get(Reflector);
  app.useGlobalGuards(new JwtAuthGuard(reflector), new RolesGuard(reflector));

  // 5. 统一异常过滤器（不暴露 stacktrace）
  app.useGlobalFilters(new AllExceptionsFilter());

  // 6. CORS 白名单（安全修复）
  const origins = (process.env.CORS_ORIGINS ?? '').split(',').filter(Boolean);
  app.enableCors({
    origin: origins.length > 0 ? origins : false, // false = 同源；白名单为空时拒绝所有跨域
    credentials: true,
    methods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Project-Id'],
    maxAge: 86400,
  });

  // 7. Bull-Board（admin only）
  await setupBullBoard(app);

  // 8. 全局 prefix
  app.setGlobalPrefix('api', {
    exclude: ['health', 'metrics'],
  });

  // 9. DB seed（仅在 DB 为空时执行）
  const db = app.get<DB>(DB_TOKEN);
  await seedDatabase(db);

  const port = Number(process.env.PORT ?? 3030);
  await app.listen(port, process.env.HOST ?? '0.0.0.0');
  Logger.log(`🟣 VioletEyes-neo API ready on http://localhost:${port}`, 'Bootstrap');
}

bootstrap().catch((err) => {
  Logger.error(`Fatal bootstrap error: ${err?.stack ?? err}`, 'Bootstrap');
  process.exit(1);
});