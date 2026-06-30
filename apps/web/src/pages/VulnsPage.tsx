import { Link } from 'react-router-dom';

export function VulnsPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <p className="text-slate-600">全局漏洞库（趋势图 / 批量操作）— Phase 5 实施</p>
      <Link to="/" className="text-violet-600 underline text-sm">← 返回首页</Link>
    </div>
  );
}