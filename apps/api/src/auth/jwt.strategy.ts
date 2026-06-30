import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { UserRole } from '@violeteyes/shared';

export interface JwtPayload {
  sub: string; // userId
  username: string;
  role: UserRole;
  iat?: number;
  exp?: number;
}

/**
 * JWT 校验策略（ §6.1 高危修复：expiresIn 与 service 必须一致）。
 * 与 auth.service.ts 的 ACCESS_TOKEN_MS（15 分钟）保持一致。
 */
@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor() {
    const secret = process.env.JWT_SECRET;
    if (!secret) {
      throw new Error('JWT_SECRET not set');
    }
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: secret,
    });
  }

  async validate(payload: JwtPayload): Promise<JwtPayload> {
    if (!payload.sub || !payload.role) {
      throw new UnauthorizedException('invalid jwt payload');
    }
    return payload;
  }
}