import { Box, Paper, Stack, Typography } from '@mui/material'
import { Navigate, Outlet, useRouteLoaderData } from 'react-router'
import { Wordmark } from '@/components/Wordmark'
import type { RootLoaderData } from './loaders'

export function AuthLayout() {
  const data = useRouteLoaderData('root') as RootLoaderData | undefined
  if (data?.user) return <Navigate to="/profile" replace />
  return (
    <Box
      sx={{
        minHeight: '100dvh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2.5,
      }}
    >
      <Stack spacing={3} sx={{ width: '100%', maxWidth: 400 }}>
        <Stack spacing={0.75} sx={{ alignItems: 'center', textAlign: 'center' }}>
          <Wordmark size={28} />
          <Typography variant="body2" color="text.secondary">
            Carga más inteligente
          </Typography>
        </Stack>
        <Paper sx={{ p: 3 }}>
          <Outlet />
        </Paper>
      </Stack>
    </Box>
  )
}
