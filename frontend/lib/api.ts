const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface ApiErrorDetail {
  code: string;
  message: string;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, detail: ApiErrorDetail | string) {
    const parsed: ApiErrorDetail =
      typeof detail === "string"
        ? { code: "ERROR", message: detail }
        : detail;
    super(parsed.message);
    this.status = status;
    this.code = parsed.code;
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const detail = data?.detail ?? "요청에 실패했습니다.";
    throw new ApiError(res.status, detail);
  }

  return data as T;
}

export interface User {
  id: string;
  email: string;
  provider: string;
  email_verified_at: string | null;
  created_at: string;
}

export const authApi = {
  requestSignupCode: (email: string) =>
    apiFetch<void>("/auth/signup/request-code", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  verifySignup: (email: string, code: string, password: string) =>
    apiFetch<User>("/auth/signup/verify", {
      method: "POST",
      body: JSON.stringify({ email, code, password }),
    }),

  login: (email: string, password: string) =>
    apiFetch<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),

  me: () => apiFetch<User>("/auth/me"),

  googleStartUrl: () => `${API_BASE}/auth/google/start`,
};
