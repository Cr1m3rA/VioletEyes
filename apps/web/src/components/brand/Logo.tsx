import clsx from 'clsx';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'gradient' | 'image-transparent' | 'image-white';
  className?: string;
  showText?: boolean;
}

const SIZE_MAP = {
  sm: { box: 'h-6 w-6 text-xs', img: 'h-6', text: 'text-sm' },
  md: { box: 'h-8 w-8 text-sm', img: 'h-8', text: 'text-base' },
  lg: { box: 'h-10 w-10 text-base', img: 'h-10', text: 'text-lg' },
  xl: { box: 'h-14 w-14 text-xl', img: 'h-14', text: 'text-2xl' },
};

const VARIANT_SRC: Record<NonNullable<LogoProps['variant']>, string> = {
  'gradient': '',
  'image-transparent': '/logo-transparent.png',
  'image-white': '/logo-white.png',
};

/**
 * VioletEyes Logo —— 三种形态：
 *  - gradient: 8×8 渐变方块 + "VE"（与 VioletEyes 报告 base.html.j2:31-33 一致，纯代码实现）
 *  - image-transparent: 透明背景 logo 图（适用于深色 Cover / Header）
 *  - image-white: 白底 logo 图（适用于浅色文档 / README）
 *
 * 图源：C:\Users\Jerome\Documents\CCworkspace\VioletEyes.png / VioletEyes-1.png
 */
export function Logo({
  size = 'md',
  variant = 'gradient',
  className,
  showText = true,
}: LogoProps) {
  const sz = SIZE_MAP[size];

  if (variant === 'gradient') {
    return (
      <div className={clsx('inline-flex items-center gap-2', className)}>
        <div
          className={clsx(
            'flex items-center justify-center rounded-lg font-bold text-white',
            'bg-gradient-to-br from-violet-500 to-violet-700 shadow-violet-glow',
            'transition-transform duration-200 hover:rotate-[3deg]',
            sz.box,
          )}
          aria-label="VioletEyes"
        >
          VE
        </div>
        {showText && (
          <span className={clsx('font-semibold text-violet-900', sz.text)}>
            VioletEyes
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={clsx('inline-flex items-center gap-2', className)}>
      <img
        src={VARIANT_SRC[variant]}
        alt="VioletEyes"
        className={clsx('w-auto transition-transform duration-200 hover:rotate-[3deg]', sz.img)}
      />
      {showText && (
        <span className={clsx('font-semibold text-violet-900', sz.text)}>
          VioletEyes-Neo
        </span>
      )}
    </div>
  );
}