import { Container } from '@mui/material'
import { Navigate, Outlet, useRouteLoaderData } from 'react-router'
import type { RootLoaderData } from './loaders'

export function AuthLayout() {
  const data = useRouteLoaderData('root') as RootLoaderData | undefined
  if (data?.user) return <Navigate to="/profile" replace />
  return (
    <Container maxWidth="xs" sx={{ py: { xs: 4, sm: 8 } }}>
      <Outlet />
    </Container>
  )
}
