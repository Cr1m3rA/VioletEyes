import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { api } from '../lib/api';
import { authApi } from '../lib/api';
import { useAuthStore } from '../lib/auth-store';

const ChangePasswordSchema = z.object({
  oldPassword: z.string().min(1),
  newPassword: z.string().min(12, '至少 12 字符'),
});

export function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const { register, handleSubmit, formState: { errors }, reset } = useForm<{ oldPassword: string; newPassword: string }>({
    resolver: zodResolver(ChangePasswordSchema),
  });

  const onSubmit = async (data: { oldPassword: string; newPassword: string }) => {
    setSubmitting(true);
    try {
      await api('/auth/change-password', { method: 'POST', body: data });
      toast.success('密码已修改，请重新登录');
      try { await authApi.logout(); } catch {}
      clearAuth();
      navigate('/login');
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setSubmitting(false);
      reset();
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">设置</h1>

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="font-semibold text-slate-900">账号</h2>
        <p className="mt-1 text-sm text-slate-500">
          用户名：{user?.username} · 角色：{user?.role}
        </p>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="font-semibold text-slate-900">修改密码</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-4 space-y-3">
          <div>
            <label className="mb-1 block text-sm text-slate-700">旧密码</label>
            <input {...register('oldPassword')} type="password" autoComplete="current-password"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            {errors.oldPassword && <p className="mt-1 text-xs text-rose-600">{errors.oldPassword.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-700">新密码（≥12 字符）</label>
            <input {...register('newPassword')} type="password" autoComplete="new-password"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            {errors.newPassword && <p className="mt-1 text-xs text-rose-600">{errors.newPassword.message}</p>}
          </div>
          <button type="submit" disabled={submitting}
            className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50">
            {submitting ? '提交中…' : '提交'}
          </button>
        </form>
      </section>
    </div>
  );
}