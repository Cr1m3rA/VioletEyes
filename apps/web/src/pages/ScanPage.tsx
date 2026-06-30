import { Link } from 'react-router-dom';

export function ScanPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <p className="text-slate-600">扫描详情（实时进度 / skill 执行 / logs）— Phase 3 实施</p>
      <Link to="/projects" className="text-violet-600 underline text-sm">← 返回项目列表</Link>
    </div>
  );
}