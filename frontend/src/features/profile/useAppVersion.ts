import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api/client'

export function useAppVersion() {
  return useQuery({
    queryKey: ['app-version'],
    staleTime: Number.POSITIVE_INFINITY,
    queryFn: async (): Promise<string> => {
      const { data, response } = await apiClient.GET('/api/health')
      if (!data) throw new Error(`health request failed (${response.status})`)
      return data.version
    },
  })
}
