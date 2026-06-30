import { Link } from 'react-router-dom';

export function SkillsPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <p className="text-slate-600">Skill 中心（上传 zip / 启停 / 审核状态）— Phase 2 实施</p>
      <Link to="/" className="text-violet-600 underline text-sm">← 返回首页</Link>
    </div>
  );
}