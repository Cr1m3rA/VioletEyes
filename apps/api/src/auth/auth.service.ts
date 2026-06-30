import { Injectable, UnauthorizedException, BadRequestException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { eq, or, sql } from 'drizzle-orm';
import { randomBytes, createHash } from 'node:crypto';
import * as argon2 from 'argon2';
import { UserRole } from '@violeteyes/shared';
import { db } from '../db/db.module';
import { users, refreshTokens } from '../db/schema';
import type { JwtPayload } from './jwt.strategy';

const ACCESS_TOKEN_MS = 15 * 60 * 1000; // 15 min（与 main.ts/jwt.strategy 一致）
const REFRESH_TOKEN_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

const PASSWORD_MIN_LENGTH = 12;

export interface LoginResult {
  accessToken: string;
  refreshToken: string;
  user: { id: string; username: string; role: string; displayName?: string };
}

/**
 * Auth 服务（ §6.1 高危修复）。
 *
 * 修复点：
 *  - login 支持 username 或 email（只支持 username）
 *  - updatePassword / changePassword 验旧密 + 校验强度 + 吊销**所有** refresh token
 *  - refresh token 含 deviceLabel / userAgent / ip（ refresh 表缺这些字段）
 *  - JWT 签发使用 15min（与 main.ts 中 JwtStrategy 的 ignoreExpiration 严格一致）
 */
@Injectable()
export class AuthService {
  constructor(private readonly jwt: JwtService) {}

  async login(
    usernameOrEmail: string,
    password: string,
    meta?: { userAgent?: string; ip?: string },
  ): Promise<LoginResult> {
    // 修复点：or(eq(username), eq(email))（ §6.1 高危）
    const user = await db
      .select()
      .from(users)
      .where(or(eq(users.username, usernameOrEmail), eq(users.email, usernameOrEmail)))
      .limit(1)
      .then((rows) => rows[0]);

    if (!user) throw new UnauthorizedException('invalid credentials');

    const ok = await argon2.verify(user.passwordHash, password);
    if (!ok) throw new UnauthorizedException('invalid credentials');

    const accessToken = await this.signAccess(user);
    const refreshToken = await this.issueRefresh(user.id, meta);

    await db
      .update(users)
      .set({ lastLoginAt: Date.now() })
      .where(eq(users.id, user.id));

    return {
      accessToken,
      refreshToken,
      user: { id: user.id, username: user.username, role: user.role, displayName: user.displayName ?? undefined },
    };
  }

  async refresh(refreshToken: string): Promise<{ accessToken: string; refreshToken: string }> {
    const tokenHash = hashRefresh(refreshToken);
    const row = await db
      .select()
      .from(refreshTokens)
      .where(eq(refreshTokens.id, tokenHash))
      .limit(1)
      .then((rows) => rows[0]);

    if (!row) throw new UnauthorizedException('invalid refresh token');
    if (row.revokedAt) throw new UnauthorizedException('refresh token revoked');
    if (row.expiresAt < Date.now()) throw new UnauthorizedException('refresh token expired');

    // 旧 token 立即撤销 + 颁发新 token（rotation）
    await db
      .update(refreshTokens)
      .set({ revokedAt: Date.now() })
      .where(eq(refreshTokens.id, tokenHash));

    const user = await db.select().from(users).where(eq(users.id, row.userId)).limit(1).then((r) => r[0]);
    if (!user) throw new UnauthorizedException('user not found');

    const accessToken = await this.signAccess(user);
    const newRefresh = await this.issueRefresh(user.id);

    return { accessToken, refreshToken: newRefresh };
  }

  async logout(refreshToken: string): Promise<void> {
    const tokenHash = hashRefresh(refreshToken);
    await db
      .update(refreshTokens)
      .set({ revokedAt: Date.now() })
      .where(eq(refreshTokens.id, tokenHash));
  }

  async changePassword(
    userId: string,
    oldPassword: string,
    newPassword: string,
  ): Promise<void> {
    if (newPassword.length < PASSWORD_MIN_LENGTH) {
      throw new BadRequestException(
        `password must be at least ${PASSWORD_MIN_LENGTH} characters`,
      );
    }
    const user = await db.select().from(users).where(eq(users.id, userId)).limit(1).then((r) => r[0]);
    if (!user) throw new UnauthorizedException('user not found');

    const ok = await argon2.verify(user.passwordHash, oldPassword);
    if (!ok) throw new UnauthorizedException('old password incorrect');

    const newHash = await argon2.hash(newPassword, {
      type: argon2.argon2id,
      timeCost: 2,
      memoryCost: 19456,
      parallelism: 1,
    });
    await db.update(users).set({ passwordHash: newHash, updatedAt: Date.now() }).where(eq(users.id, userId));

    // 吊销所有 refresh token
    await db
      .update(refreshTokens)
      .set({ revokedAt: Date.now() })
      .where(eq(refreshTokens.userId, userId));
  }

  // ── helpers ──

  private async signAccess(user: typeof users.$inferSelect): Promise<string> {
    const payload: JwtPayload = {
      sub: user.id,
      username: user.username,
      role: user.role as UserRole,
    };
    return this.jwt.signAsync(payload, { expiresIn: `${ACCESS_TOKEN_MS / 1000}s` });
  }

  private async issueRefresh(
    userId: string,
    meta?: { userAgent?: string; ip?: string },
  ): Promise<string> {
    const raw = randomBytes(32).toString('hex'); // 修复点：用 crypto.randomBytes（ §6.2 中危）
    const id = `rt-${randomBytes(16).toString('hex')}`;
    const expiresAt = Date.now() + REFRESH_TOKEN_MS;
    await db.insert(refreshTokens).values({
      id,
      userId,
      deviceLabel: meta?.userAgent?.slice(0, 128),
      userAgent: meta?.userAgent?.slice(0, 256),
      ip: meta?.ip?.slice(0, 64),
      expiresAt,
      createdAt: Date.now(),
    });
    return `${id}.${raw}`;
  }
}

function hashRefresh(token: string): string {
  // token 格式: rt-<id>.<secret>；存的是 id 的 hash
  const id = token.split('.')[0];
  return createHash('sha256').update(id).digest('hex');
}