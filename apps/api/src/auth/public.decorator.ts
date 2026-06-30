import { SetMetadata } from '@nestjs/common';

export const IS_PUBLIC_KEY = 'isPublic';

/**
 * 标记路由为公开，JwtAuthGuard 会跳过。
 * 仅用于：/auth/login, /auth/refresh, /health, /metrics
 */
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);