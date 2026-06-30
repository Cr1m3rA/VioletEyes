import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
  MessageBody,
  ConnectedSocket,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { Logger, UnauthorizedException, ForbiddenException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { eq, and } from 'drizzle-orm';
import { Inject } from '@nestjs/common';
import { DB_TOKEN, type DB } from '../db/db.module';
import { scanRuns, projectMembers } from '../db/schema';
import type { JwtPayload } from '../auth/jwt.strategy';

/**
 * 实时扫描事件网关（ §6.1 高危修复）。
 *
 * 修复点：
 *  - 关闭 `origin: true`（开放 CORS 已修）
 *  - 显式 origin 白名单
 *  - handleConnection 必须 JWT 鉴权（cookie 或 query token）
 *  - 订阅 `scan:<runId>` 必须验证 user 对 runId 有读权限
 */
@WebSocketGateway({
  namespace: '/scans',
  cors: {
    origin: (process.env.CORS_ORIGINS ?? '').split(',').filter(Boolean),
    credentials: true,
  },
})
export class ScanGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer() server: Server;
  private readonly logger = new Logger(ScanGateway.name);

  constructor(
    private readonly jwt: JwtService,
    @Inject(DB_TOKEN) private readonly db: DB,
  ) {}

  async handleConnection(client: Socket): Promise<void> {
    try {
      const token = this.extractToken(client);
      const payload = await this.verifyToken(token);
      (client.data as { user?: JwtPayload }).user = payload;
      this.logger.log(`socket ${client.id} connected as ${payload.username}`);
    } catch (e) {
      this.logger.warn(`socket ${client.id} auth failed: ${(e as Error).message}`);
      client.emit('auth.error', { message: 'authentication required' });
      client.disconnect(true);
    }
  }

  handleDisconnect(client: Socket): void {
    this.logger.log(`socket ${client.id} disconnected`);
  }

  @SubscribeMessage('subscribe:scan')
  async subscribeScan(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: { runId: string },
  ): Promise<{ ok: true } | { ok: false; error: string }> {
    const user = (client.data as { user?: JwtPayload }).user;
    if (!user) return { ok: false, error: 'not authenticated' };

    try {
      await this.assertCanRead(user, data.runId);
      await client.join(`scan:${data.runId}`);
      this.logger.log(`socket ${client.id} subscribed scan:${data.runId}`);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: (e as Error).message };
    }
  }

  @SubscribeMessage('unsubscribe:scan')
  async unsubscribeScan(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: { runId: string },
  ): Promise<{ ok: true }> {
    await client.leave(`scan:${data.runId}`);
    return { ok: true };
  }

  // ── 推送 API（由 ScanRunnerService 调用）──
  emit(runId: string, event: string, payload: unknown): void {
    this.server.to(`scan:${runId}`).emit(event, payload);
  }

  // ── helpers ──

  private extractToken(client: Socket): string {
    // 优先 cookie（refresh token 走 cookie）；query token 用于测试
    const cookieToken = client.handshake.headers.cookie
      ?.split(';')
      .map((s) => s.trim())
      .find((s) => s.startsWith('vt_access='))
      ?.split('=')[1];
    if (cookieToken) return decodeURIComponent(cookieToken);

    const queryToken = client.handshake.auth?.token ?? client.handshake.query?.token;
    if (typeof queryToken === 'string') return queryToken;

    throw new UnauthorizedException('no token');
  }

  private async verifyToken(token: string): Promise<JwtPayload> {
    const payload = await this.jwt.verifyAsync<JwtPayload>(token);
    if (!payload.sub) throw new UnauthorizedException('invalid payload');
    return payload;
  }

  private async assertCanRead(user: JwtPayload, runId: string): Promise<void> {
    // admin 全权限
    if (user.role === 'admin') return;

    // 检查 user 是否为该项目成员
    const row = await this.db
      .select({ runId: scanRuns.id })
      .from(scanRuns)
      .innerJoin(projectMembers, eq(scanRuns.projectId, projectMembers.projectId))
      .where(and(eq(scanRuns.id, runId), eq(projectMembers.userId, user.sub)))
      .limit(1)
      .all();
    if (row.length === 0) {
      throw new ForbiddenException(`no read access to run ${runId}`);
    }
  }
}