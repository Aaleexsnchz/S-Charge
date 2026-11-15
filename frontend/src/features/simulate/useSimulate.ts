import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api/client'
import type { components } from '@/lib/api/schema'

type SimulationRequest = components['schemas']['SimulationRequest']
type SimulationResult = components['schemas']['SimulationResult']

export function useSimulate() {
  return useMutation({
    mutationFn: async (request: SimulationRequest): Promise<SimulationResult> => {
      const { data, response } = await apiClient.POST('/api/simulate', { body: request })
      if (!data) throw new Error(`simulation failed (${response.status})`)
      return data
    },
  })
}
