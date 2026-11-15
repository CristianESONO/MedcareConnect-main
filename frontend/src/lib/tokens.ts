/** Design tokens — mirrors sipn_cards.css :root variables */
export const colors = {
  navy:        '#123a63',
  navyLight:   '#1a4f87',
  accent:      '#4fa3c7',
  accentDark:  '#3d8fb3',
  sipnGreen:   '#14b87a',
  sipnGreenDk: '#0fa066',
  white:       '#ffffff',
  gray50:      '#f8fafc',
  gray100:     '#f1f5f9',
  gray200:     '#e2e8f0',
  gray400:     '#94a3b8',
  gray600:     '#475569',
  gray800:     '#1e293b',
  danger:      '#ef4444',
  warning:     '#f59e0b',
  info:        '#3b82f6',
} as const;

export const shadows = {
  sipn:   '0 4px 16px rgba(10,92,138,.07)',
  sipnMd: '0 8px 24px rgba(10,92,138,.12)',
  sipnLg: '0 16px 48px rgba(10,92,138,.18)',
} as const;

export const radius = {
  sm: '8px',
  md: '12px',  // --sipn-r
  lg: '16px',
  xl: '24px',
} as const;

export const fonts = {
  display: "'Syne', sans-serif",
  body:    "'DM Sans', 'Plus Jakarta Sans', sans-serif",
} as const;
