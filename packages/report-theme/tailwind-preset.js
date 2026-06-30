/**
 * VioletEyes Tailwind preset (Tailwind v4 compatible).
 * 对应 spec §6.1 设计 token + §6.2 Tailwind preset。
 * apps/web 在 tailwind.config.ts 里 preset: [require('@violeteyes/report-theme/tailwind-preset')]
 */

module.exports = {
  theme: {
    extend: {
      colors: {
        violet: {
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed', // 主色
          700: '#6d28d9', // 强调
          800: '#5b21b6',
          900: '#4c1d95',
          950: '#2e1065',
        },
        // 严重度色（与 VioletEyes 报告 base.css 一致）
        sev: {
          critical: '#dc2626',
          high: '#ea580c',
          medium: '#ca8a04',
          low: '#0891b2',
          info: '#64748b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', 'monospace'],
      },
      backgroundImage: {
        'cover-gradient': 'linear-gradient(135deg, #4c1d95 0%, #1e1b4b 100%)',
        'cover-radial': 'radial-gradient(ellipse at top, rgba(167,139,250,0.3), transparent 60%)',
        'severity-critical': 'linear-gradient(to right, #dc2626, #fca5a5)',
        'severity-high': 'linear-gradient(to right, #ea580c, #fdba74)',
      },
      boxShadow: {
        'violet-glow': '0 0 24px rgba(124,58,237,0.4)',
        'cover-grid': '0 0 0 1px rgba(255,255,255,0.04)',
      },
      keyframes: {
        'violet-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'violet-pulse': 'violet-pulse 2s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s ease-out',
      },
    },
  },
};