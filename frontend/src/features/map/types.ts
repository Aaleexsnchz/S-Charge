export type AggregateStatus = 'available' | 'occupied' | 'unknown'

export type MapPointProperties = {
  id: string
  aggregate_status: AggregateStatus
  standards: string[]
  max_power_w: number | null
  min_price_per_kwh: number | null
  has_free: boolean
}

export type MapFeature = {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: MapPointProperties
}

export type MapFeatureCollection = {
  type: 'FeatureCollection'
  features: MapFeature[]
}

export type MapFilters = {
  onlyAvailable: boolean
  standard: string | null
  maxPrice: number | null
}

export const EMPTY_FILTERS: MapFilters = {
  onlyAvailable: false,
  standard: null,
  maxPrice: null,
}
