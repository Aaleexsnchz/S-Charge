import { useQuery } from '@tanstack/react-query'
import type { Point } from '@/features/points/usePoint'
import type { Coords } from '@/hooks/useGeolocation'
import { apiClient } from '@/lib/api/client'

const BBOX_HALF_DEG = 0.05
const NEARBY_LIMIT = 3
const STALE_TIME = 5 * 60 * 1000

export type NearbyPoint = Point & { distanceKm: number }

function haversineKm(a: Coords, b: Coords): number {
  const R = 6371
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const dLat = toRad(b.lat - a.lat)
  const dLng = toRad(b.lng - a.lng)
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.sin(dLng / 2) ** 2 * Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat))
  return 2 * R * Math.asin(Math.sqrt(h))
}

export function useNearbyPoints(coords: Coords | null) {
  const keyCoords = coords
    ? [Math.round(coords.lat * 100) / 100, Math.round(coords.lng * 100) / 100]
    : null
  return useQuery({
    queryKey: ['nearby-points', keyCoords],
    enabled: coords !== null,
    staleTime: STALE_TIME,
    queryFn: async (): Promise<NearbyPoint[]> => {
      const center = coords as Coords
      const bbox = [
        center.lng - BBOX_HALF_DEG,
        center.lat - BBOX_HALF_DEG,
        center.lng + BBOX_HALF_DEG,
        center.lat + BBOX_HALF_DEG,
      ].join(',')
      const { data, response } = await apiClient.GET('/api/points', {
        params: { query: { bbox } },
      })
      if (!data) {
        throw new Error(`nearby points request failed (${response.status})`)
      }
      return (data as Point[])
        .map((point) => ({
          ...point,
          distanceKm: haversineKm(center, { lat: point.latitude, lng: point.longitude }),
        }))
        .sort((a, b) => a.distanceKm - b.distanceKm)
        .slice(0, NEARBY_LIMIT)
    },
  })
}
