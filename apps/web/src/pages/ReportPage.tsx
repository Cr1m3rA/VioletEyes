import { Link } from 'react-router-dom';

export function ReportPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <p className="text-slate-600">报告页面（嵌入 VioletEyes 模板 HTML）— Phase 4 实施</p>
      <Link to="/projects" className="text-violet-600 underline text-sm">← 返回项目列表</Link>
    </div>
  );
}