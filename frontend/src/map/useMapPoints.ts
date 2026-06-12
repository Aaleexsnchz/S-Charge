import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import type { MapFeatureCollection } from './types'

const CATALOGUE_STALE_TIME = 5 * 60 * 1000

export function useMapPoints() {
  return useQuery({
    queryKey: ['map-points'],
    staleTime: CATALOGUE_STALE_TIME,
    queryFn: async (): Promise<MapFeatureCollection> => {
      const { data, response } = await apiClient.GET('/api/points/map')
      if (!data) {
        throw new Error(`map points request failed (${response.status})`)
      }
      return data as unknown as MapFeatureCollection
    },
  })
}
