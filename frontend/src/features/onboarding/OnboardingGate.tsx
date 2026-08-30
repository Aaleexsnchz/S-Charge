import { Box, Button, Paper, Stack, TextField, Typography } from '@mui/material'
import { type ReactNode, useState } from 'react'
import { Form, useFetcher, useRouteLoaderData } from 'react-router'
import type { RootLoaderData } from '@/features/auth/loaders'
import { MAX_NAME_LENGTH, type NameActionData } from '@/features/profile/actions'

function AskForName() {
  const fetcher = useFetcher<NameActionData>()
  const [name, setName] = useState('')
  const submitting = fetcher.state !== 'idle'
  const error = fetcher.data && 'error' in fetcher.data ? fetcher.data.error : null

  return (
    <Box sx={{ p: 2, maxWidth: 600, mx: 'auto', pt: 6 }}>
      <Typography variant="h1">Bienvenido a S-Charge</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
        ¿Cómo quieres que te llamemos?
      </Typography>

      <Paper sx={{ p: 2, mt: 3 }}>
        <fetcher.Form method="post" action="/onboarding">
          <Stack spacing={2}>
            <TextField
              name="name"
              label="Nombre"
              autoComplete="given-name"
              autoFocus
              slotProps={{ htmlInput: { maxLength: MAX_NAME_LENGTH } }}
              value={name}
              onChange={(e) => setName(e.target.value)}
              error={error !== null}
              helperText={error}
              fullWidth
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={submitting || name.trim() === ''}
              fullWidth
            >
              {submitting ? 'Guardando…' : 'Continuar'}
            </Button>
          </Stack>
        </fetcher.Form>
      </Paper>

      <Form method="post" action="/logout">
        <Button type="submit" variant="text" color="inherit" size="small" sx={{ mt: 2 }}>
          Cerrar sesión
        </Button>
      </Form>
    </Box>
  )
}

export function OnboardingGate({ children }: { children: ReactNode }) {
  const data = useRouteLoaderData('root') as RootLoaderData | undefined
  if (!data?.user?.name?.trim()) return <AskForName />
  return <>{children}</>
}
