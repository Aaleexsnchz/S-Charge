import { useRouteLoaderData } from 'react-router'
import type { User } from '@/types/api'
import type { RootLoaderData } from './loaders'

export function useCurrentUser(): User | null {
  const data = useRouteLoaderData('root') as RootLoaderData | undefined
  return data?.user ?? null
}

export function userInitial(user: User): string {
  return (user.name?.trim()[0] ?? user.email[0] ?? '?').toUpperCase()
}
