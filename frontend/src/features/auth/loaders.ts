import { apiClient } from '@/lib/api/client'
import type { User } from '@/types/api'

export type RootLoaderData = { user: User | null }

export async function rootLoader(): Promise<RootLoaderData> {
  const { data } = await apiClient.GET('/api/users/me')
  return { user: data ?? null }
}
