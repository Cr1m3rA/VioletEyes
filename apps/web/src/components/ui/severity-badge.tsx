import clsx from 'clsx';
import type { Severity } from '@violeteyes/shared';

const SEV_HEX: Record<Severity, string> = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#ca8a04',
  low: '#0891b2',
  info: '#64748b',
};

const SEV_INITIAL: Record<Severity, string> = {
  critical: 'C',
  high: 'H',
  medium: 'M',
  low: 'L',
  info: 'I',
};

interface SeverityBadgeProps {
  severity: Severity;
  className?: string;
  size?: 'sm' | 'md';
}

/**
 * 严重度徽章 —— 圆形 + 首字母 + 严重度色。
 * 与 VioletEyes 报告 finding.html.j2:7-13 视觉一致。
 */
export function SeverityBadge({ severity, className, size = 'md' }: SeverityBadgeProps) {
  const color = SEV_HEX[severity];
  const sz = size === 'sm' ? 'h-5 w-5 text-[10px]' : 'h-6 w-6 text-xs';
  return (
    <span
      className={clsx(
        'inline-flex items-center justify-center rounded-full font-bold text-white',
        sz,
        className,
      )}
      style={{ backgroundColor: color }}
      title={severity}
    >
      {SEV_INITIAL[severity]}
    </span>
  );
}

interface SeverityBarProps {
  severity: Severity;
  className?: string;
  children: React.ReactNode;
}

/**
 * 严重度色条 —— 左侧 4px 色条 + 内容。
 * 与 VioletEyes 报告 finding 卡片视觉一致（base.css:60-71）。
 */
export function SeverityBar({ severity, className, children }: SeverityBarProps) {
  return (
    <div
      className={clsx(
        'severity-bar rounded-lg bg-white p-4 shadow-sm border border-slate-200',
        `severity-bar--${severity}`,
        className,
      )}
    >
      {children}
    </div>
  );
}