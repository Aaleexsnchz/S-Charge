import { Box, Stack, Typography } from '@mui/material'
import { Navigate, Outlet } from 'react-router'
import { Wordmark } from '@/components/Wordmark'
import { useCurrentUser } from './currentUser'

export function AuthLayout() {
  const user = useCurrentUser()
  if (user) return <Navigate to="/" replace />
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
      <Stack spacing={4} sx={{ width: '100%', maxWidth: 380 }}>
        <Stack spacing={1.25} sx={{ alignItems: 'center', textAlign: 'center' }}>
          <Wordmark size={42} />
          <Typography
            variant="numeric"
            sx={{
              fontSize: 10,
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
              color: 'text.disabled',
            }}
          >
            Carga más inteligente
          </Typography>
        </Stack>
        <Outlet />
      </Stack>
    </Box>
  )
}
