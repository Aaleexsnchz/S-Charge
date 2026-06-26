import type { AggregateStatus } from '@/features/map/types'

export const STANDARD_LABELS: Record<string, string> = {
  IEC_62196_T2: 'Tipo 2',
  IEC_62196_T2_COMBO: 'CCS Combo 2',
  CHADEMO: 'CHAdeMO',
  IEC_62196_T1: 'Tipo 1',
  IEC_62196_T3A: 'Tipo 3A',
  IEC_62196_T3C: 'Tipo 3C',
  DOMESTIC_F: 'Schuko',
}

export function standardLabel(standard: string): string {
  return STANDARD_LABELS[standard] ?? standard
}

export const STATUS_LABELS: Record<AggregateStatus, string> = {
  available: 'Disponible',
  occupied: 'Ocupado',
  unknown: 'Estado desconocido',
}

export const STATUS_CHIP_COLOR: Record<
  AggregateStatus,
  'success' | 'warning' | 'error' | 'default'
> = {
  available: 'success',
  occupied: 'warning',
  unknown: 'default',
}

export function powerLabel(maxPowerW: number | null | undefined): string | null {
  if (!maxPowerW) return null
  return `${(maxPowerW / 1000).toLocaleString('es-ES', { maximumFractionDigits: 1 })} kW`
}

export function priceLabel(pricePerKwh: number | null | undefined): string | null {
  if (pricePerKwh === null || pricePerKwh === undefined) return null
  return `${pricePerKwh.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €/kWh`
}

export function googleMapsDirectionsUrl(lat: number, lng: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
}
