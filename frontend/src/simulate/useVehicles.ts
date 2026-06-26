import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import type { components } from '../api/schema'

export type Vehicle = components['schemas']['VehicleRead']

export function useVehicles() {
  return useQuery({
    queryKey: ['vehicles'],
    staleTime: 60 * 60 * 1000,
    queryFn: async (): Promise<Vehicle[]> => {
      const { data, response } = await apiClient.GET('/api/vehicles')
      if (!data) throw new Error(`vehicles request failed (${response.status})`)
      return data
    },
  })
}
