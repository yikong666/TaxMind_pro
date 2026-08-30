export interface AppErrorShape {
  code: string;
  message: string;
  details: unknown;
  retryable: boolean;
  requestId: string | null;
}

export class AppError extends Error implements AppErrorShape {
  public readonly code: string;
  public readonly details: unknown;
  public readonly retryable: boolean;
  public readonly requestId: string | null;

  public constructor(shape: AppErrorShape) {
    super(shape.message);
    this.name = 'AppError';
    this.code = shape.code;
    this.details = shape.details;
    this.retryable = shape.retryable;
    this.requestId = shape.requestId;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function toAppError(status: number, payload: unknown, requestId: string | null): AppError {
  if (isRecord(payload) && isRecord(payload.error)) {
    const error = payload.error;
    return new AppError({
      code: typeof error.code === 'string' ? error.code : `HTTP_${String(status)}`,
      message: typeof error.message === 'string' ? error.message : '请求失败，请稍后重试',
      details: error.details,
      retryable: error.retryable === true,
      requestId,
    });
  }
  return new AppError({
    code: status === 0 ? 'NETWORK_ERROR' : `HTTP_${String(status)}`,
    message: status === 0 ? '无法连接到服务，请检查后端是否启动' : '请求失败，请稍后重试',
    details: null,
    retryable: status === 0 || status >= 500,
    requestId,
  });
}