import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Logo } from '../components/brand/Logo';
import { authApi } from '../lib/api';
import { useAuthStore } from '../lib/auth-store';

const LoginSchema = z.object({
  usernameOrEmail: z.string().min(1, '请输入用户名或邮箱'),
  password: z.string().min(1, '请输入密码'),
});

type LoginForm = z.infer<typeof LoginSchema>;

/**
 * 登录页 —— 紫光背景 + 毛玻璃表单。
 */
export function LoginPage() {
  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();
  const location = useLocation();
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(LoginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setSubmitting(true);
    try {
      const res = await authApi.login(data.usernameOrEmail, data.password);
      setAuth({
        accessToken: res.accessToken,
        user: res.user,
        ttlMs: 15 * 60 * 1000,
      });
      toast.success(`欢迎，${res.user.displayName ?? res.user.username}`);
      const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/';
      navigate(from, { replace: true });
    } catch (e) {
      toast.error((e as Error).message || '登录失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="cover-hero flex min-h-screen items-center justify-center px-4">
      <div className="glass-card w-full max-w-md rounded-2xl border border-white/20 bg-white/95 p-8 shadow-2xl backdrop-blur">
        <div className="mb-8 flex justify-center">
          <Logo size="xl" variant="image-transparent" showText={false} />
        </div>
        <h1 className="mb-2 text-center text-2xl font-bold text-slate-900">登录</h1>
        <p className="mb-6 text-center text-sm text-slate-500">
          VioletEyes-neo 代码审计平台
        </p>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              用户名或邮箱
            </label>
            <input
              {...register('usernameOrEmail')}
              type="text"
              autoComplete="username"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
            />
            {errors.usernameOrEmail && (
              <p className="mt-1 text-xs text-rose-600">{errors.usernameOrEmail.message}</p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">密码</label>
            <input
              {...register('password')}
              type="password"
              autoComplete="current-password"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
            />
            {errors.password && (
              <p className="mt-1 text-xs text-rose-600">{errors.password.message}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-gradient-to-br from-violet-500 to-violet-700 px-4 py-2 text-sm font-medium text-white shadow-violet-glow transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? '登录中…' : '登录'}
          </button>
        </form>
        <p className="mt-6 text-center text-xs text-slate-400">
          Authorized-Testing-Only · v0.1.0
        </p>
      </div>
    </div>
  );
}