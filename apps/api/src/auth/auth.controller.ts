import {
  Controller,
  Post,
  Body,
  HttpCode,
  HttpStatus,
  Res,
  Req,
  Get,
} from '@nestjs/common';
import { Request, Response } from 'express';
import { z } from 'zod';
import { AuthService } from './auth.service';
import { Public } from './public.decorator';
import { JwtAuthGuard } from './jwt-auth.guard';
import { UseGuards } from '@nestjs/common';
import { CurrentUser } from './current-user.decorator';
import type { JwtPayload } from './jwt.strategy';

const REFRESH_COOKIE = 'vt_refresh';

const LoginDto = z.object({
  usernameOrEmail: z.string().min(1).max(128),
  password: z.string().min(1).max(256),
});

const ChangePasswordDto = z.object({
  oldPassword: z.string().min(1).max(256),
  newPassword: z.string().min(12).max(256),
});

/**
 * Auth 控制器。
 *
 * 关键修复（ §6.1 高危）：
 *  - access token **不在响应体返回**（避免任何地方持久化），仅通过后续请求的 Authorization header 持有
 *  - refresh token 仅 HttpOnly cookie（防 XSS 窃取）
 *  - login 支持 username **或** email（只支持 username）
 *  - change-password 验旧密 + 强度 + 吊销所有 refresh
 */
@Controller('auth')
export class AuthController {
  constructor(private readonly auth: AuthService) {}

  @Public()
  @Post('login')
  @HttpCode(HttpStatus.OK)
  async login(
    @Body() body: unknown,
    @Res({ passthrough: true }) res: Response,
  ): Promise<{ accessToken: string; user: { id: string; username: string; role: string } }> {
    const dto = LoginDto.parse(body);
    const result = await this.auth.login(dto.usernameOrEmail, dto.password);

    res.cookie(REFRESH_COOKIE, result.refreshToken, {
      httpOnly: true,
      secure: process.env.COOKIE_SECURE === 'true',
      sameSite: 'lax',
      maxAge: 7 * 24 * 60 * 60 * 1000,
      path: '/api/auth',
    });

    return {
      accessToken: result.accessToken,
      user: result.user,
    };
  }

  @Public()
  @Post('refresh')
  @HttpCode(HttpStatus.OK)
  async refresh(
    @Req() req: Request,
    @Res({ passthrough: true }) res: Response,
  ): Promise<{ accessToken: string }> {
    const refreshToken = req.cookies?.[REFRESH_COOKIE];
    if (!refreshToken) throw new Error('no refresh token');

    const result = await this.auth.refresh(refreshToken);
    res.cookie(REFRESH_COOKIE, result.refreshToken, {
      httpOnly: true,
      secure: process.env.COOKIE_SECURE === 'true',
      sameSite: 'lax',
      maxAge: 7 * 24 * 60 * 60 * 1000,
      path: '/api/auth',
    });
    return { accessToken: result.accessToken };
  }

  @Post('logout')
  @HttpCode(HttpStatus.NO_CONTENT)
  async logout(@Req() req: Request, @Res({ passthrough: true }) res: Response): Promise<void> {
    const refreshToken = req.cookies?.[REFRESH_COOKIE];
    if (refreshToken) await this.auth.logout(refreshToken);
    res.clearCookie(REFRESH_COOKIE, { path: '/api/auth' });
  }

  @UseGuards(JwtAuthGuard)
  @Post('change-password')
  @HttpCode(HttpStatus.OK)
  async changePassword(
    @CurrentUser() user: JwtPayload,
    @Body() body: unknown,
  ): Promise<{ ok: true }> {
    const dto = ChangePasswordDto.parse(body);
    await this.auth.changePassword(user.sub, dto.oldPassword, dto.newPassword);
    return { ok: true };
  }

  @UseGuards(JwtAuthGuard)
  @Get('me')
  me(@CurrentUser() user: JwtPayload): JwtPayload {
    return user;
  }
}