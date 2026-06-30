import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from './lib/auth-store';
import { Header } from './components/layout/Header';
import { LoginPage } from './pages/LoginPage';
import { HomePage } from './pages/HomePage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { ScanPage } from './pages/ScanPage';
import { ReportPage } from './pages/ReportPage';
import { VulnsPage } from './pages/VulnsPage';
import { SkillsPage } from './pages/SkillsPage';
import { SettingsPage } from './pages/SettingsPage';
import { AdminUsersPage } from './pages/admin/AdminUsersPage';
import { AdminSkillsPage } from './pages/admin/AdminSkillsPage';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const isAuthed = useAuthStore((s) => s.isAuthenticated());
  const location = useLocation();
  if (!isAuthed) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header />
      <main>
        <Routes>
          {/* 公开路由 */}
          <Route path="/login" element={<LoginPage />} />

          {/* 受保护路由 */}
          <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
          <Route path="/projects" element={<RequireAuth><ProjectsPage /></RequireAuth>} />
          <Route path="/projects/:id" element={<RequireAuth><ProjectDetailPage /></RequireAuth>} />
          <Route path="/projects/:id/scans/:runId" element={<RequireAuth><ScanPage /></RequireAuth>} />
          <Route path="/projects/:id/scans/:runId/report" element={<RequireAuth><ReportPage /></RequireAuth>} />
          <Route path="/vulns" element={<RequireAuth><VulnsPage /></RequireAuth>} />
          <Route path="/skills" element={<RequireAuth><SkillsPage /></RequireAuth>} />
          <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />

          {/* admin only */}
          <Route path="/admin/users" element={<RequireAuth><RequireAdmin><AdminUsersPage /></RequireAdmin></RequireAuth>} />
          <Route path="/admin/skills" element={<RequireAuth><RequireAdmin><AdminSkillsPage /></RequireAdmin></RequireAuth>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}