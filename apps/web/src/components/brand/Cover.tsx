import clsx from 'clsx';
import type { ReactNode } from 'react';
import { Logo } from './Logo';

interface CoverProps {
  title?: string;
  subtitle?: ReactNode;
  badges?: Array<{ label: string; tone?: 'violet' | 'slate' }>;
  children?: ReactNode;
  className?: string;
  showLogo?: boolean;
}

/**
 * VioletEyes Cover hero —— 紫光径向渐变 + 线性渐变 + 网格纹理 + 毛玻璃徽章。
 * 与 VioletEyes 报告 cover.html.j2:2-65 视觉一致。
 */
export function Cover({ title, subtitle, badges, children, className, showLogo = true }: CoverProps) {
  return (
    <section
      className={clsx(
        'cover-hero relative overflow-hidden text-white px-8 py-12',
        className,
      )}
    >
      <div className="relative z-10 mx-auto max-w-7xl">
        {showLogo && (
          <div className="mb-6">
            <Logo size="lg" variant="image-transparent" showText={false} />
          </div>
        )}
        {badges && badges.length > 0 && (
          <div className="mb-6 flex flex-wrap gap-2">
            {badges.map((b, i) => (
              <span
                key={i}
                className="glass-badge rounded-full px-3 py-1 text-xs font-medium text-white"
              >
                {b.label}
              </span>
            ))}
          </div>
        )}
        {title && <h1 className="text-4xl md:text-5xl font-bold tracking-tight">{title}</h1>}
        {subtitle && <div className="mt-3 text-violet-200 text-lg">{subtitle}</div>}
        {children && <div className="mt-8">{children}</div>}
      </div>
    </section>
  );
}