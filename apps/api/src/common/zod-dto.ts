import { z } from 'zod';

/**
 * 把 zod schema 转成 class，让 NestJS 的 ValidationPipe 能识别。
 * 用 class-transformer 透传到 controller。
 */
export function createZodDto<T extends z.ZodTypeAny>(_schema: T) {
  // 简单的"占位类"：运行时只关心 zod schema，class 用于 @Body() 类型推断
  return class {
    constructor(init?: Partial<z.infer<T>>) {
      if (init) Object.assign(this, init);
    }
  } as new (init?: Partial<z.infer<T>>) => z.infer<T>;
}