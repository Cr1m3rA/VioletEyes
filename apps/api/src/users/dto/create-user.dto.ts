import { z } from 'zod';
import { createZodDto } from '../../common/zod-dto';
import { UserRole } from '@violeteyes/shared';

export const CreateUserSchema = z.object({
  username: z
    .string()
    .min(3)
    .max(64)
    .regex(/^[a-zA-Z0-9_-]+$/, 'username must be alphanumeric / underscore / dash'),
  email: z.string().email().optional(),
  password: z.string().min(12).max(256),
  displayName: z.string().min(1).max(128).optional(),
  role: z.enum([UserRole.ADMIN, UserRole.AUDITOR, UserRole.VIEWER]).default(UserRole.AUDITOR),
});

export class CreateUserDto extends createZodDto(CreateUserSchema) {}