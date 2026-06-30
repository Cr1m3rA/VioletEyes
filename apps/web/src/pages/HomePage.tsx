import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { Cover } from '../components/brand/Cover';
import { SeverityBadge } from '../components/ui/severity-badge';

export function HomePage() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api<{ status: string }>('/health'),
  });

  return (
    <>
      <Cover
        subtitle="多语言代码审计平台 · 智能识别 RCE / SSRF / SQLi / XXE 等漏洞"
        badges={[
          { label: '🟣 v0.1.0' },
          { label: '✨ Smart Mode' },
          { label: '🚀 Multi-Language' },
          { label: '🧩 Extensible Skills' },
        ]}
      />

      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link to="/projects" className="group rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
            <h3 className="font-semibold text-slate-900 group-hover:text-violet-700">项目</h3>
            <p className="mt-1 text-sm text-slate-500">创建项目、上传代码、发起扫描</p>
            <div className="mt-4 flex items-center gap-2">
              <SeverityBadge severity="info" size="sm" />
              <span className="text-xs text-slate-400">点击进入 →</span>
            </div>
          </Link>
          <Link to="/skills" className="group rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
            <h3 className="font-semibold text-slate-900 group-hover:text-violet-700">Skill 中心</h3>
            <p className="mt-1 text-sm text-slate-500">导入 / 启用 / 审核代码审计 skill</p>
            <div className="mt-4 flex items-center gap-2">
              <SeverityBadge severity="medium" size="sm" />
              <span className="text-xs text-slate-400">点击进入 →</span>
            </div>
          </Link>
          <Link to="/vulns" className="group rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
            <h3 className="font-semibold text-slate-900 group-hover:text-violet-700">漏洞库</h3>
            <p className="mt-1 text-sm text-slate-500">跨项目漏洞聚合与趋势</p>
            <div className="mt-4 flex items-center gap-2">
              <SeverityBadge severity="high" size="sm" />
              <span className="text-xs text-slate-400">点击进入 →</span>
            </div>
          </Link>
        </div>

        <div className="mt-8 rounded-xl border border-violet-200 bg-violet-50 p-4 text-sm text-violet-900">
          <strong>系统状态：</strong> {health?.status === 'ok' ? '🟢 正常' : '🟡 待启动'}
          <span className="ml-3 text-violet-600">Phase 0 脚手架已完成 · Phase 1 鉴权/项目/代码版本 待实施</span>
        </div>
      </div>
    </>
  );
}