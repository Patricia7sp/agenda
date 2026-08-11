import type { Activity, ActivityCreate, ActivityStats, DaySummary, User } from "./types";

// Em dev o Vite faz proxy de /api; em produção o frontend e a API ficam em
// domínios diferentes, então a base vem de VITE_API_BASE_URL.
const BASE = `${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1`;
const TOKEN_KEY = "agenda_token";
const CACHE_KEY = "agenda_cache";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string) => {
  if (getToken() !== token) localStorage.removeItem(CACHE_KEY);
  localStorage.setItem(TOKEN_KEY, token);
};
export const clearToken = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(CACHE_KEY);
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean } = {},
): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401) clearToken();
    throw new ApiError(data?.detail ?? `Erro ${res.status}`, res.status, data?.code);
  }
  return data as T;
}

export const api = {
  requestMagicLink: (email: string) =>
    request<{ ok: boolean; dev_magic_link: string | null; dev_rate_limited: boolean }>(
      "/auth/magic-link",
      { method: "POST", body: { email }, auth: false },
    ),

  verify: (token: string) =>
    request<{ access_token: string; user: User }>("/auth/verify", {
      method: "POST",
      body: { token },
      auth: false,
    }),

  me: () => request<User>("/auth/me"),

  updateMe: (patch: { name?: string; timezone?: string }) =>
    request<User>("/auth/me", { method: "PATCH", body: patch }),

  listByDate: (date: string) => request<Activity[]>(`/activities?date=${date}`),

  summary: (from: string, to: string) =>
    request<DaySummary[]>(`/activities/summary?from=${from}&to=${to}`),

  stats: (from: string, to: string) =>
    request<ActivityStats>(`/activities/stats?from=${from}&to=${to}`),

  get: (id: string) => request<Activity>(`/activities/${id}`),

  create: (payload: ActivityCreate) =>
    request<Activity>("/activities", { method: "POST", body: payload }),

  update: (id: string, patch: Partial<ActivityCreate> & { status?: string }) =>
    request<Activity>(`/activities/${id}`, { method: "PATCH", body: patch }),

  complete: (id: string) =>
    request<Activity>(`/activities/${id}/complete`, { method: "POST" }),

  postpone: (id: string, scheduled_date: string, scheduled_time: string | null) =>
    request<Activity>(`/activities/${id}/postpone`, {
      method: "POST",
      body: { scheduled_date, scheduled_time },
    }),

  remove: (id: string) => request<void>(`/activities/${id}`, { method: "DELETE" }),
};
