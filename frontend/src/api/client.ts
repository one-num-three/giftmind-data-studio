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

function formatApiErrorDetail(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (!Array.isArray(detail)) return null;
  const messages = detail.map((item) => {
    if (typeof item === "string") return item;
    if (!item || typeof item !== "object") return "";
    const entry = item as { msg?: unknown; loc?: unknown };
    const message = typeof entry.msg === "string" ? entry.msg : "";
    const location = Array.isArray(entry.loc) ? String(entry.loc.at(-1) ?? "") : "";
    return message && location ? `${location}：${message}` : message;
  }).filter(Boolean);
  return messages.length ? messages.join("；") : null;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, headers, handleUnauthorized = true, ...requestOptions } = options;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    const response = await fetch(path, {
      ...requestOptions,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "include",
      signal: controller.signal,
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
      const message = formatApiErrorDetail(payload?.detail) ?? "请求未能完成。";
      throw new ApiError(message, response.status, payload?.detail);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  } finally {
    clearTimeout(timeout);
  }
}
