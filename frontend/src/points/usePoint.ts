import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import type { components } from '../api/schema'

export type Point = components['schemas']['PointRead']

export class PointNotFoundError extends Error {
  constructor() {
    super('point not found')
    this.name = 'PointNotFoundError'
  }
}

export function usePoint(pointId: string | null) {
  return useQuery({
    queryKey: ['point', pointId],
    enabled: pointId !== null,
    retry: (failureCount, error) => !(error instanceof PointNotFoundError) && failureCount < 2,
    queryFn: async (): Promise<Point> => {
      const { data, response } = await apiClient.GET('/api/points/{point_id}', {
        params: { path: { point_id: pointId as string } },
      })
      if (!data) {
        if (response.status === 404) throw new PointNotFoundError()
        throw new Error(`point request failed (${response.status})`)
      }
      return data
    },
  })
}
