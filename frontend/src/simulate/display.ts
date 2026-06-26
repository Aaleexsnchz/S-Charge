import type { SimulationResult } from './useSimulate'

export function durationLabel(minutes: number): string {
  const total = Math.round(minutes)
  const hours = Math.floor(total / 60)
  const mins = total % 60
  if (hours === 0) return `${mins} min`
  if (mins === 0) return `${hours} h`
  return `${hours} h ${mins} min`
}

export function energyLabel(kwh: number): string {
  return `${kwh.toLocaleString('es-ES', { maximumFractionDigits: 1 })} kWh`
}

export function costLabel(eur: number | null): string {
  if (eur === null) return '—'
  return `${eur.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`
}

export const PRICE_SOURCE_LABELS: Record<NonNullable<SimulationResult['price_source']>, string> = {
  reve_tariff: 'tarifa real del punto',
  pvpc_plus_margin: 'estimado (PVPC + margen)',
}
