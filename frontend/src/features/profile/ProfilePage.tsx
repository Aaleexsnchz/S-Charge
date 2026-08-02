import LogoutIcon from '@mui/icons-material/Logout'
import { Avatar, Box, Button, Stack, Typography } from '@mui/material'
import { Form, useRouteLoaderData } from 'react-router'
import type { RootLoaderData } from '@/features/auth/loaders'
import { useAppVersion } from './useAppVersion'

export function ProfilePage() {
  const data = useRouteLoaderData('root') as RootLoaderData | undefined
  // Before the early return: the linter enforces unconditional hook calls.
  const { data: version } = useAppVersion()
  const user = data?.user
  if (!user) return null

  const initial = (user.name?.trim()?.[0] ?? user.email[0] ?? '?').toUpperCase()

  return (
    <Box sx={{ p: 2, maxWidth: 600, mx: 'auto' }}>
      <Stack spacing={1} sx={{ alignItems: 'center', textAlign: 'center', py: 2 }}>
        <Avatar
          sx={{
            width: 80,
            height: 80,
            fontSize: 32,
            fontWeight: 600,
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
          }}
        >
          {initial}
        </Avatar>
        {user.name && (
          <Typography variant="h2" sx={{ mt: 1 }}>
            {user.name}
          </Typography>
        )}
        <Typography variant="body2" color="text.secondary">
          {user.email}
        </Typography>
      </Stack>

      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ display: 'block', textAlign: 'center' }}
      >
        Versión {version ?? '—'}
      </Typography>

      <Box sx={{ mt: 3 }}>
        <Form method="post" action="/logout">
          <Button
            type="submit"
            variant="outlined"
            color="error"
            size="large"
            fullWidth
            startIcon={<LogoutIcon />}
          >
            Cerrar sesión
          </Button>
        </Form>
      </Box>
    </Box>
  )
}
