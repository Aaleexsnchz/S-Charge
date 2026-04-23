import type { ReactNode } from 'react'
import { Navigate, useRouteLoaderData } from 'react-router'
import type { RootLoaderData } from '../auth/loaders'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const data = useRouteLoaderData('root') as RootLoaderData | undefined
  if (!data?.user) return <Navigate to="/login" replace />
  return <>{children}</>
}
