import { Link } from 'react-router-dom';

export function ProjectDetailPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <p className="text-slate-600">项目详情 — Phase 1 实施</p>
      <Link to="/projects" className="text-violet-600 underline text-sm">← 返回项目列表</Link>
    </div>
  );
}