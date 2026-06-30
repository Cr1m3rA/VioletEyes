import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { Request, Response } from 'express';

/**
 * 统一异常过滤器（需求 NFR-UX-04）。
 *
 * 原则：
 *  - 不暴露 stacktrace 给客户端
 *  - 区分 4xx（业务错误，返回 message）和 5xx（服务器错误，返回 generic message）
 *  - 5xx 详情仅写 server log
 */
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  private readonly logger = new Logger(AllExceptionsFilter.name);

  catch(exception: unknown, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let message: string | object = 'Internal server error';
    let code = 'INTERNAL_ERROR';

    if (exception instanceof HttpException) {
      status = exception.getStatus();
      const body = exception.getResponse();
      message = typeof body === 'string' ? body : (body as { message?: string }).message ?? body;
      code = HttpStatus[status] ?? 'HTTP_ERROR';
    } else if (exception instanceof Error) {
      this.logger.error(`Unhandled: ${exception.message}`, exception.stack);
    } else {
      this.logger.error(`Unknown exception: ${String(exception)}`);
    }

    response.status(status).json({
      ok: false,
      status,
      code,
      message,
      path: request.url,
      timestamp: new Date().toISOString(),
    });
  }
}