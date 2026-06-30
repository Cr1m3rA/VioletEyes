import { Link, NavLink } from 'react-router-dom';
import { useEffect, useState } from 'react';
import clsx from 'clsx';
import { LogOut } from 'lucide-react';
import { Logo } from '../brand/Logo';
import { useAuthStore } from '../../lib/auth-store';
import { authApi } from '../../lib/api';
import { useNavigate } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/projects', label: '项目' },
  { to: '/vulns', label: '漏洞库' },
  { to: '/skills', label: 'Skill 中心' },
  { to: '/settings', label: '设置' },
];

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const navigate = useNavigate();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const onLogout = async () => {
    try {
      await authApi.logout(); // 修复点：调后端吊销 refresh（ §6.1 高危）
    } catch {
      /* 即使 logout 接口失败也要清本地状态 */
    }
    clearAuth();
    navigate('/login');
  };

  return (
    <header className={clsx('header-sticky', scrolled && 'scrolled')}>
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link to="/" className="flex items-center">
          <Logo size="md" variant="image-transparent" />
        </Link>

        {user && (
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-violet-100 text-violet-700'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}

        <div className="flex items-center gap-3">
          {user ? (
            <>
              <span className="text-sm text-slate-600">
                {user.displayName ?? user.username}
              </span>
              <button
                onClick={onLogout}
                className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                title="登出"
              >
                <LogOut size={18} />
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="rounded-md bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700"
            >
              登录
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}