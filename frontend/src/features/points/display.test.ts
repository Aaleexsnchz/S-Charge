import { describe, expect, it } from 'vitest'
import type { components } from '@/lib/api/schema'
import {
  longPriceLabel,
  type PricingState,
  pointPricingState,
  pricingState,
  shortPriceLabel,
} from './display'

type Connector = components['schemas']['ConnectorRead']
type Point = components['schemas']['PointRead']

function connector(overrides: Partial<Connector>): Connector {
  return {
    id: 'c1',
    standard: 'IEC_62196_T2',
    format: 'SOCKET',
    power_type: 'AC',
    max_voltage: 400,
    max_amperage: 32,
    max_electric_power: 22000,
    pricing_kind: 'unknown',
    current_price_per_kwh: null,
    tariff: null,
    ...overrides,
  } as Connector
}

function point(connectors: Connector[]): Point {
  return { evses: [{ connectors }] } as Point
}

describe('pricingState', () => {
  it('reads an energy price as a per-kWh amount', () => {
    expect(
      pricingState(connector({ pricing_kind: 'energy', current_price_per_kwh: 0.42 })),
    ).toEqual({ kind: 'per_kwh', pricePerKwh: 0.42 })
  })

  it('reads free as free, not as a zero price', () => {
    expect(pricingState(connector({ pricing_kind: 'free' }))).toEqual({ kind: 'free' })
  })

  it('keeps time and flat pricing distinct from an absent price', () => {
    expect(pricingState(connector({ pricing_kind: 'time' }))).toEqual({ kind: 'time' })
    expect(pricingState(connector({ pricing_kind: 'flat' }))).toEqual({ kind: 'flat' })
  })

  it('reports an unknown price with a past valid_to as expired', () => {
    const state = pricingState(
      connector({
        pricing_kind: 'unknown',
        tariff: { id: 't1', currency: 'EUR', valid_from: null, valid_to: '2026-08-12T00:00:00Z' },
      }),
    )
    expect(state.kind).toBe('expired')
  })

  it('reports an unknown price with a future valid_to as unpublished', () => {
    const state = pricingState(
      connector({
        pricing_kind: 'unknown',
        tariff: { id: 't1', currency: 'EUR', valid_from: null, valid_to: '2099-01-01T00:00:00Z' },
      }),
    )
    expect(state.kind).toBe('unpublished')
  })

  it('reports an unknown price with no tariff as unpublished', () => {
    expect(pricingState(connector({ pricing_kind: 'unknown' }))).toEqual({ kind: 'unpublished' })
  })
})

describe('pointPricingState', () => {
  it('takes the cheapest per-kWh connector', () => {
    expect(
      pointPricingState(
        point([
          connector({ id: 'a', pricing_kind: 'energy', current_price_per_kwh: 0.47 }),
          connector({ id: 'b', pricing_kind: 'energy', current_price_per_kwh: 0.29 }),
        ]),
      ),
    ).toEqual({ kind: 'per_kwh', pricePerKwh: 0.29 })
  })

  it('prefers free over any priced connector', () => {
    expect(
      pointPricingState(
        point([
          connector({ id: 'a', pricing_kind: 'energy', current_price_per_kwh: 0.29 }),
          connector({ id: 'b', pricing_kind: 'free' }),
        ]),
      ),
    ).toEqual({ kind: 'free' })
  })

  it('prefers a known pricing kind over an absent price', () => {
    expect(
      pointPricingState(
        point([connector({ id: 'a' }), connector({ id: 'b', pricing_kind: 'time' })]),
      ),
    ).toEqual({ kind: 'time' })
  })

  it('returns null for a point with no connectors', () => {
    expect(pointPricingState(point([]))).toBeNull()
  })
})

describe('labels', () => {
  it('never states a price for a connector that has none', () => {
    const priceless: PricingState[] = [
      { kind: 'time' },
      { kind: 'flat' },
      { kind: 'expired', validTo: new Date('2026-08-12T00:00:00Z') },
      { kind: 'unpublished' },
    ]
    for (const state of priceless) {
      expect(shortPriceLabel(state)).not.toMatch(/€/)
      expect(longPriceLabel(state)).not.toMatch(/€\/kWh/)
    }
  })

  it('says when an expired tariff expired', () => {
    expect(longPriceLabel({ kind: 'expired', validTo: new Date('2026-08-12T12:00:00Z') })).toBe(
      'La tarifa publicada caducó el 12/08/2026',
    )
  })

  it('formats a per-kWh price in es-ES', () => {
    expect(shortPriceLabel({ kind: 'per_kwh', pricePerKwh: 0.4 })).toBe('0,40 €/kWh')
  })
})
