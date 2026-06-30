import { PipeTransform, BadRequestException } from '@nestjs/common';
import { ZodSchema } from 'zod';

/**
 * Zod 校验 pipe。在 controller 用 @Body(new ZodValidationPipe(MySchema)) 替代 class-validator。
 * 与全局 ValidationPipe 并行使用：DTO 字段用 class-validator，复杂逻辑用 zod。
 */
export class ZodValidationPipe implements PipeTransform {
  constructor(private readonly schema: ZodSchema) {}

  transform(value: unknown) {
    const result = this.schema.safeParse(value);
    if (!result.success) {
      throw new BadRequestException({
        message: 'Validation failed',
        errors: result.error.flatten(),
      });
    }
    return result.data;
  }
}