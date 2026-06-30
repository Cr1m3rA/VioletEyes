import { Injectable, CanActivate, ExecutionContext, ForbiddenException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { UserRole } from '@violeteyes/shared';
import { ROLES_KEY } from './roles.decorator';
import type { JwtPayload } from './jwt.strategy';

@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const required = this.reflector.getAllAndOverride<UserRole[]>(ROLES_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (!required || required.length === 0) return true;

    const req = context.switchToHttp().getRequest<{ user?: JwtPayload }>();
    if (!req.user) throw new ForbiddenException('not authenticated');

    if (!required.includes(req.user.role)) {
      throw new ForbiddenException(`role '${req.user.role}' not in [${required.join(', ')}]`);
    }
    return true;
  }
}