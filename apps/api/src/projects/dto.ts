import { z } from 'zod';
import { createZodDto } from '../../common/zod-dto';

export const CreateProjectSchema = z.object({
  name: z.string().trim().min(1).max(128),
  description: z.string().trim().max(1024).optional(),
});
export class CreateProjectDto extends createZodDto(CreateProjectSchema) {}

export const UpdateProjectSchema = z.object({
  name: z.string().trim().min(1).max(128).optional(),
  description: z.string().trim().max(1024).optional(),
});
export class UpdateProjectDto extends createZodDto(UpdateProjectSchema) {}

export const AddMemberSchema = z.object({
  userId: z.string().min(1).max(64),
  role: z.enum(['owner', 'editor', 'viewer']),
});
export class AddMemberDto extends createZodDto(AddMemberSchema) {}