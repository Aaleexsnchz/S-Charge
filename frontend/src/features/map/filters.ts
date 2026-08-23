import type { MapFeatureCollection, MapFilters } from './types'

const AVAILABLE_STATUSES = new Set(['available'])

export function filterFeatures(
  collection: MapFeatureCollection,
  filters: MapFilters,
): MapFeatureCollection {
  const features = collection.features.filter((feature) => {
    const props = feature.properties
    if (filters.onlyAvailable && !AVAILABLE_STATUSES.has(props.aggregate_status)) {
      return false
    }
    if (filters.standard && !props.standards.includes(filters.standard)) {
      return false
    }
    // A free point carries no price, so comparing against maxPrice alone would
    // hide exactly the points a price filter is looking for.
    if (filters.maxPrice !== null && !props.has_free) {
      if (props.min_price_per_kwh === null || props.min_price_per_kwh > filters.maxPrice) {
        return false
      }
    }
    return true
  })
  return { type: 'FeatureCollection', features }
}
