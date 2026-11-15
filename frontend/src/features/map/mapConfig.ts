import { tokens } from '@/theme'

export const MAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/dark'

export const SPAIN_CENTER: [number, number] = [-3.7, 40.0]
export const SPAIN_ZOOM = 5.2

// Mirrors STATUS_DOT_COLOR in features/points/display.ts: MapLibre paint
// expressions take literal colours, not theme paths.
export const STATUS_COLORS = {
  available: tokens.accent,
  occupied: tokens.err,
  unknown: tokens.text3,
} as const
