import { apiClient } from '../api/client'
import type { User } from '../api/types'

export type RootLoaderData = { user: User | null }

export async function rootLoader(): Promise<RootLoaderData> {
  const { data } = await apiClient.GET('/api/users/me')
  return { user: data ?? null }
}
