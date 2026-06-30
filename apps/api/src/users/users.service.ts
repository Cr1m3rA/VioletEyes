import { Injectable, Inject, NotFoundException, ConflictException } from '@nestjs/common';
import { eq } from 'drizzle-orm';
import { randomBytes } from 'node:crypto';
import * as argon2 from 'argon2';
import { UserRole } from '@violeteyes/shared';
import { DB_TOKEN, type DB } from '../db/db.module';
import { users } from '../db/schema';

const PASSWORD_MIN_LENGTH = 12;

/**
 * Users 服务。
 *
 * 修复点（ §6.1 高危）：
 *  - updatePassword 强制校验密码强度 + 校验旧密码（已由 AuthService.changePassword 实现）
 *  - 用户列表不返回 passwordHash
 *  - id 用 crypto.randomBytes 而非 Math.random
 */
@Injectable()
export class UsersService {
  constructor(@Inject(DB_TOKEN) private readonly db: DB) {}

  async list(): Promise<Array<typeof users.$inferSelect>> {
    return this.db.select().from(users).all();
  }

  async findById(id: string): Promise<typeof users.$inferSelect> {
    const user = await this.db.select().from(users).where(eq(users.id, id)).limit(1).then((r) => r[0]);
    if (!user) throw new NotFoundException(`user ${id} not found`);
    return user;
  }

  async findByUsernameOrEmail(usernameOrEmail: string): Promise<typeof users.$inferSelect | null> {
    const { or } = await import('drizzle-orm');
    const row = await this.db
      .select()
      .from(users)
      .where(or(eq(users.username, usernameOrEmail), eq(users.email, usernameOrEmail)))
      .limit(1)
      .then((r) => r[0]);
    return row ?? null;
  }

  async create(args: {
    username: string;
    email?: string;
    password: string;
    displayName?: string;
    role?: UserRole;
  }): Promise<typeof users.$inferSelect> {
    if (args.password.length < PASSWORD_MIN_LENGTH) {
      throw new ConflictException(`password must be at least ${PASSWORD_MIN_LENGTH} chars`);
    }

    const existing = await this.findByUsernameOrEmail(args.username);
    if (existing) throw new ConflictException(`username '${args.username}' already taken`);

    if (args.email) {
      const byEmail = await this.db
        .select()
        .from(users)
        .where(eq(users.email, args.email))
        .limit(1)
        .then((r) => r[0]);
      if (byEmail) throw new ConflictException(`email '${args.email}' already taken`);
    }

    const id = `usr-${randomBytes(8).toString('hex')}`;
    const passwordHash = await argon2.hash(args.password, {
      type: argon2.argon2id,
      timeCost: 2,
      memoryCost: 19456,
      parallelism: 1,
    });

    const row = {
      id,
      username: args.username,
      email: args.email ?? null,
      passwordHash,
      displayName: args.displayName ?? null,
      role: args.role ?? UserRole.AUDITOR,
      mustChangePassword: true,
      lastLoginAt: null,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    await this.db.insert(users).values(row);

    return row as typeof users.$inferSelect;
  }

  async update(
    id: string,
    patch: { email?: string; displayName?: string; role?: UserRole },
  ): Promise<typeof users.$inferSelect> {
    await this.findById(id);
    await this.db
      .update(users)
      .set({ ...patch, updatedAt: Date.now() })
      .where(eq(users.id, id));
    return this.findById(id);
  }

  async delete(id: string): Promise<void> {
    await this.findById(id);
    await this.db.delete(users).where(eq(users.id, id));
  }

  /** 强制脱敏：不返回 passwordHash */
  static sanitize<T extends { passwordHash: string }>(u: T): Omit<T, 'passwordHash'> {
    const { passwordHash: _, ...rest } = u;
    return rest;
  }
}