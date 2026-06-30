/**
 * Re-export tokens for TS consumers.
 */

export const VIOLET = {
  50: '#f5f3ff',
  100: '#ede9fe',
  200: '#ddd6fe',
  300: '#c4b5fd',
  400: '#a78bfa',
  500: '#8b5cf6',
  600: '#7c3aed',
  700: '#6d28d9',
  800: '#5b21b6',
  900: '#4c1d95',
  950: '#2e1065',
} as const;

export const SEVERITY_COLORS = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#ca8a04',
  low: '#0891b2',
  info: '#64748b',
} as const;

export const COVER_GRADIENT =
  'linear-gradient(135deg, #4c1d95 0%, #1e1b4b 100%)' as const;
export const COVER_RADIAL =
  'radial-gradient(ellipse at top, rgba(167,139,250,0.3), transparent 60%)' as const;