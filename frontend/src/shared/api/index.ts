/** Shared HTTP helpers will be kept separate from feature business rules. */

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
  };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly body: unknown;

  constructor(status: number, code: string, message: string, body: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.body = body;
  }
}

function readJsonBody(text: string): unknown {
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: init.credentials ?? "include",
  });
  const body = readJsonBody(await response.text());

  if (!response.ok) {
    const errorBody = (body ?? {}) as ApiErrorBody;
    throw new ApiError(
      response.status,
      errorBody.error?.code ?? "request_failed",
      errorBody.error?.message ?? "The request could not be completed.",
      body,
    );
  }

  return body as T;
}
