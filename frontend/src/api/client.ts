export interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  handleUnauthorized?: boolean;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let onUnauthorized: (() => void | Promise<void>) | undefined;

export function setUnauthorizedHandler(handler: () => void | Promise<void>): void {
  onUnauthorized = handler;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, headers, handleUnauthorized = true, ...requestOptions } = options;
  const response = await fetch(path, {
    ...requestOptions,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "include",
    headers: {
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401 && handleUnauthorized) {
      await onUnauthorized?.();
    }

    const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
    const message = typeof payload?.detail === "string" ? payload.detail : "请求未能完成。";
    throw new ApiError(message, response.status, payload?.detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
