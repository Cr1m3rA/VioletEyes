import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Auth store —— **access token 内存保存**，refresh token 由 HttpOnly cookie 自动带。
 *
 * 修复  §6.1 高危：localStorage 持久化 token 与设计矛盾。
 *
 * 注意：refresh token 由浏览器自动管理 HttpOnly cookie，**前端无法访问**，
 * 所以这里只持久化 access token 的过期判断，不持久化 token 本身。
 */

interface AuthState {
  accessToken: string | null;
  user: { id: string; username: string; role: string; displayName?: string } | null;
  expiresAt: number | null;
  setAuth: (data: { accessToken: string; user: AuthState['user']; ttlMs: number }) => void;
  clearAuth: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      user: null,
      expiresAt: null,

      setAuth: ({ accessToken, user, ttlMs }) =>
        set({
          accessToken,
          user,
          expiresAt: Date.now() + ttlMs,
        }),

      clearAuth: () =>
        set({ accessToken: null, user: null, expiresAt: null }),

      isAuthenticated: () => {
        const { accessToken, expiresAt } = get();
        return !!accessToken && !!expiresAt && expiresAt > Date.now();
      },
    }),
    {
      name: 'violeteyes-auth-meta',
      // ⚠️ 只持久化非敏感字段，避免 token 落 localStorage
      partialize: (state) => ({
        user: state.user,
        // accessToken **不**持久化（refresh 后重新拿）
      }),
    },
  ),
);