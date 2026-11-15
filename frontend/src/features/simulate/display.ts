import { formatDecimal, formatEur } from '@/lib/format'

export function durationLabel(minutes: number): string {
  const total = Math.round(minutes)
  const hours = Math.floor(total / 60)
  const mins = total % 60
  if (hours === 0) return `${mins} min`
  if (mins === 0) return `${hours} h`
  return `${hours} h ${mins} min`
}

export function energyLabel(kwh: number): string {
  return `${formatDecimal(kwh, 1)} kWh`
}

export function costLabel(eur: number | null): string {
  if (eur === null) return 'Sin precio'
  return `${formatEur(eur)} €`
}
