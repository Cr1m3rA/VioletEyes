import { Link } from 'react-router-dom';
import { Cover } from '../components/brand/Cover';

export function ProjectsPage() {
  return (
    <>
      <Cover title="项目" badges={[{ label: 'Phase 1 待实施' }]} />
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="rounded-xl border border-dashed border-violet-300 bg-violet-50/50 p-8 text-center">
          <p className="text-violet-700">项目列表 / 创建 / 上传代码 zip — Phase 1 实施</p>
          <Link to="/" className="mt-4 inline-block text-sm text-violet-600 underline">
            ← 返回首页
          </Link>
        </div>
      </div>
    </>
  );
}