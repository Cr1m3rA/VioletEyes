import { useAuthStore } from './auth-store';

/**
 * 统一 API 客户端。
 *
 * 关键修复（ §6.1 高危）：
 *  - access token 仅内存（Zustand），**不**localStorage
 *  - refresh token 走 HttpOnly cookie（浏览器自动带）
 *  - 401 自动 silent refresh（只一次，避免无限循环）
 */

const ACCESS_TOKEN_HEADER = 'Authorization';

interface ApiOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  /** 跳过自动 refresh（避免 refresh 接口自身死循环） */
  skipRefresh?: boolean;
}

let refreshingPromise: Promise<string | null> | null = null;

async function silentRefresh(): Promise<string | null> {
  if (refreshingPromise) return refreshingPromise;
  refreshingPromise = (async () => {
    try {
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) return null;
      const data = await res.json();
      const store = useAuthStore.getState();
      store.setAuth({
        accessToken: data.accessToken,
        user: store.user,
        ttlMs: 15 * 60 * 1000,
      });
      return data.accessToken as string;
    } catch {
      return null;
    } finally {
      refreshingPromise = null;
    }
  })();
  return refreshingPromise;
}

export async function api<T = unknown>(
  path: string,
  opts: ApiOptions = {},
): Promise<T> {
  const { body, skipRefresh, headers, ...rest } = opts;

  const doFetch = async (token: string | null): Promise<Response> => {
    const h = new Headers(headers);
    if (token) h.set(ACCESS_TOKEN_HEADER, `Bearer ${token}`);
    if (body !== undefined && !(body instanceof FormData)) {
      h.set('Content-Type', 'application/json');
    }
    return fetch(`/api${path}`, {
      ...rest,
      credentials: 'include',
      headers: h,
      body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let token = useAuthStore.getState().accessToken;
  let res = await doFetch(token);

  // 401 → silent refresh（除 refresh 接口本身）
  if (res.status === 401 && !skipRefresh) {
    const newToken = await silentRefresh();
    if (newToken) {
      res = await doFetch(newToken);
    } else {
      useAuthStore.getState().clearAuth();
    }
  }

  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = typeof body === 'object' ? JSON.stringify(body) : String(body);
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`API ${status}: ${detail}`);
  }
}

// ── 高层封装 ──

export const authApi = {
  login: (usernameOrEmail: string, password: string) =>
    api<{ accessToken: string; user: any }>('/auth/login', {
      method: 'POST',
      body: { usernameOrEmail, password },
      skipRefresh: true,
    }),
  logout: () => api<void>('/auth/logout', { method: 'POST' }),
  me: () => api<any>('/auth/me'),
};