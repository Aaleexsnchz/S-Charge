import { Alert, Button, Link as MuiLink, Stack, TextField, Typography } from '@mui/material'
import { useSnackbar } from 'notistack'
import { useEffect, useState } from 'react'
import {
  Form,
  Link as RouterLink,
  useActionData,
  useNavigate,
  useNavigation,
  useSearchParams,
} from 'react-router'
import type { ResetPasswordActionData } from './actions'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const actionData = useActionData() as ResetPasswordActionData | undefined
  const navigation = useNavigation()
  const submitting = navigation.state === 'submitting'
  const navigate = useNavigate()
  const { enqueueSnackbar } = useSnackbar()

  const [password, setPassword] = useState('')
  const canSubmit = password.length >= 12 && token !== ''

  useEffect(() => {
    if (actionData && 'success' in actionData) {
      enqueueSnackbar('Contraseña actualizada', { variant: 'success' })
      navigate('/login', { replace: true })
    }
  }, [actionData, enqueueSnackbar, navigate])

  if (!token) {
    return (
      <Stack spacing={3}>
        <Typography variant="h4" component="h1">
          Restablecer contraseña
        </Typography>
        <Alert severity="error">Enlace inválido o expirado</Alert>
        <Typography variant="body2">
          <MuiLink component={RouterLink} to="/forgot-password">
            Solicitar otro
          </MuiLink>
        </Typography>
      </Stack>
    )
  }

  const errorData = actionData && 'error' in actionData ? actionData : undefined

  return (
    <Stack spacing={3}>
      <Typography variant="h4" component="h1">
        Restablecer contraseña
      </Typography>
      <Form method="post" noValidate>
        <input type="hidden" name="token" value={token} />
        <Stack spacing={2}>
          <TextField
            name="password"
            type="password"
            label="Nueva contraseña"
            autoComplete="new-password"
            helperText="Mínimo 12 caracteres"
            slotProps={{ htmlInput: { minLength: 12 } }}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            fullWidth
          />
          {errorData && <Alert severity="error">{errorData.error}</Alert>}
          {errorData?.expiredToken && (
            <Typography variant="body2">
              <MuiLink component={RouterLink} to="/forgot-password">
                Solicitar otro
              </MuiLink>
            </Typography>
          )}
          <Button type="submit" variant="contained" disabled={submitting || !canSubmit} fullWidth>
            {submitting ? 'Guardando…' : 'Guardar contraseña'}
          </Button>
        </Stack>
      </Form>
    </Stack>
  )
}
