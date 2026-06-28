import { createTheme } from '@mui/material/styles'
import type { CSSProperties } from 'react'

const bodyFont = '"Hanken Grotesk", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
const monoFont = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace'

export const tokens = {
  bg: '#0A0E13',
  surface: '#121821',
  surface2: '#1A2230',
  border: '#242C3A',
  innerBorder: 'rgba(255,255,255,0.04)',
  text: '#E7ECF2',
  text2: '#9AA6B5',
  text3: '#6A7686',
  accent: '#7FE7C4',
  onAccent: '#0A0E13',
  ok: '#4ADE80',
  warn: '#FBBF24',
  err: '#EF4444',
  info: '#60A5FA',
} as const

declare module '@mui/material/styles' {
  interface Palette {
    tokens: typeof tokens
  }
  interface PaletteOptions {
    tokens?: typeof tokens
  }
  interface TypographyVariants {
    numeric: CSSProperties
  }
  interface TypographyVariantsOptions {
    numeric?: CSSProperties
  }
}

declare module '@mui/material/Typography' {
  interface TypographyPropsVariantOverrides {
    numeric: true
  }
}

export const theme = createTheme({
  palette: {
    mode: 'dark',
    tokens,
    primary: { main: tokens.accent, contrastText: tokens.onAccent },
    background: { default: tokens.bg, paper: tokens.surface },
    text: { primary: tokens.text, secondary: tokens.text2, disabled: tokens.text3 },
    divider: tokens.border,
    success: { main: tokens.ok },
    warning: { main: tokens.warn },
    error: { main: tokens.err },
    info: { main: tokens.info },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: bodyFont,
    h1: { fontSize: '1.75rem', fontWeight: 600, lineHeight: 1.3, letterSpacing: '-0.01em' },
    h2: { fontSize: '1.375rem', fontWeight: 600, lineHeight: 1.3 },
    h3: { fontSize: '1.125rem', fontWeight: 600, lineHeight: 1.3 },
    button: { textTransform: 'none', fontWeight: 600 },
    numeric: {
      fontFamily: monoFont,
      fontVariantNumeric: 'tabular-nums',
      letterSpacing: '-0.01em',
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: tokens.bg,
          WebkitFontSmoothing: 'antialiased',
          WebkitTapHighlightColor: 'transparent',
        },
        '::selection': { background: 'rgba(127,231,196,0.25)' },
        '::-webkit-scrollbar': { width: 0, height: 0 },
        code: { fontFamily: monoFont },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          border: `1px solid ${tokens.innerBorder}`,
        },
      },
    },
    MuiAppBar: {
      defaultProps: { elevation: 0, color: 'transparent' },
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(10,14,19,0.7)',
          backdropFilter: 'blur(12px)',
          borderBottom: `1px solid ${tokens.border}`,
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { borderRadius: 999, fontSize: '0.9375rem' },
        sizeSmall: { minHeight: 36, fontSize: '0.8125rem' },
        sizeMedium: { minHeight: 44 },
        sizeLarge: { minHeight: 48 },
        outlined: { borderColor: 'currentColor' },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 999, fontWeight: 500 },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          '& fieldset': { borderColor: tokens.border },
          '&:hover fieldset': { borderColor: tokens.text3 },
          '&.Mui-focused fieldset': { borderColor: tokens.accent },
        },
      },
    },
    MuiDivider: {
      styleOverrides: { root: { borderColor: tokens.border } },
    },
    MuiBottomNavigation: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(10,14,19,0.92)',
          backdropFilter: 'blur(16px)',
          borderTop: `1px solid ${tokens.border}`,
        },
      },
    },
    MuiBottomNavigationAction: {
      styleOverrides: {
        root: {
          color: tokens.text3,
          '&.Mui-selected': { color: tokens.accent },
        },
        label: { fontSize: '0.6875rem', '&.Mui-selected': { fontSize: '0.6875rem' } },
      },
    },
  },
})
