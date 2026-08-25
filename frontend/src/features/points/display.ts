import type { AggregateStatus } from '@/features/map/types'
import type { components } from '@/lib/api/schema'
import type { Point } from './usePoint'

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

type Connector = components['schemas']['ConnectorRead']

export type PricingState =
  | { kind: 'per_kwh'; pricePerKwh: number }
  | { kind: 'free' }
  | { kind: 'time' }
  | { kind: 'flat' }
  | { kind: 'expired'; validTo: Date }
  | { kind: 'unpublished' }

export function pricingState(connector: Connector): PricingState {
  if (connector.pricing_kind === 'free') return { kind: 'free' }
  if (connector.pricing_kind === 'energy' && connector.current_price_per_kwh !== null) {
    return { kind: 'per_kwh', pricePerKwh: connector.current_price_per_kwh }
  }
  if (connector.pricing_kind === 'time') return { kind: 'time' }
  if (connector.pricing_kind === 'flat') return { kind: 'flat' }

  const validTo = connector.tariff?.valid_to ? new Date(connector.tariff.valid_to) : null
  if (validTo !== null && validTo.getTime() < Date.now()) return { kind: 'expired', validTo }
  return { kind: 'unpublished' }
}

const PRICING_RANK: Record<PricingState['kind'], number> = {
  free: 0,
  per_kwh: 1,
  time: 2,
  flat: 3,
  expired: 4,
  unpublished: 5,
}

export function pointPricingState(point: Point): PricingState | null {
  let best: PricingState | null = null
  for (const evse of point.evses) {
    for (const connector of evse.connectors) {
      const state = pricingState(connector)
      if (best === null || PRICING_RANK[state.kind] < PRICING_RANK[best.kind]) {
        best = state
      } else if (
        state.kind === 'per_kwh' &&
        best.kind === 'per_kwh' &&
        state.pricePerKwh < best.pricePerKwh
      ) {
        best = state
      }
    }
  }
  return best
}

export function pricePerKwhLabel(pricePerKwh: number): string {
  return `${pricePerKwh.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €/kWh`
}

export function shortPriceLabel(state: PricingState): string {
  switch (state.kind) {
    case 'per_kwh':
      return pricePerKwhLabel(state.pricePerKwh)
    case 'free':
      return 'Gratis'
    case 'time':
      return 'Por tiempo'
    case 'flat':
      return 'Tarifa fija'
    case 'expired':
      return 'Tarifa caducada'
    case 'unpublished':
      return 'Sin precio'
  }
}

export function longPriceLabel(state: PricingState): string {
  switch (state.kind) {
    case 'per_kwh':
      return pricePerKwhLabel(state.pricePerKwh)
    case 'free':
      return 'Gratis'
    case 'time':
      return 'El operador cobra por tiempo, no por energía'
    case 'flat':
      return 'El operador cobra una tarifa fija por sesión'
    case 'expired':
      return `La tarifa publicada caducó el ${state.validTo.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      })}`
    case 'unpublished':
      return 'El operador no publica precio'
  }
}

export function googleMapsDirectionsUrl(lat: number, lng: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
}
