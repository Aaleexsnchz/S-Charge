import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useCurrentUser } from './currentUser'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const user = useCurrentUser()
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}
