import { z } from 'zod';
import { createZodDto } from '../../common/zod-dto';
import { UserRole } from '@violeteyes/shared';

export const UpdateUserSchema = z.object({
  email: z.string().email().optional(),
  displayName: z.string().min(1).max(128).optional(),
  role: z.enum([UserRole.ADMIN, UserRole.AUDITOR, UserRole.VIEWER]).optional(),
});

export class UpdateUserDto extends createZodDto(UpdateUserSchema) {}