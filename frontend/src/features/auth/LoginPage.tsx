import {
  Alert,
  Box,
  Button,
  Divider,
  Link as MuiLink,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useSnackbar } from 'notistack'
import { useEffect, useRef, useState } from 'react'
import {
  Form,
  Link as RouterLink,
  useActionData,
  useNavigation,
  useSearchParams,
} from 'react-router'
import { apiClient } from '@/lib/api/client'
import type { LoginActionData } from './actions'
import { GoogleSignInButton } from './GoogleSignInButton'

export function LoginPage() {
  const actionData = useActionData() as LoginActionData | undefined
  const navigation = useNavigation()
  const submitting = navigation.state === 'submitting'

  const unverifiedEmail =
    actionData && 'unverifiedEmail' in actionData ? actionData.unverifiedEmail : null
  const errorMessage = actionData && 'error' in actionData ? actionData.error : null

  const [searchParams, setSearchParams] = useSearchParams()
  const { enqueueSnackbar } = useSnackbar()
  const oauthErrorHandled = useRef(false)
  useEffect(() => {
    if (oauthErrorHandled.current) return
    if (searchParams.get('error') !== 'oauth_failed') return
    oauthErrorHandled.current = true
    enqueueSnackbar('No se pudo iniciar sesión con Google. Inténtalo de nuevo.', {
      variant: 'error',
    })
    setSearchParams({}, { replace: true })
  }, [searchParams, setSearchParams, enqueueSnackbar])

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const canSubmit = email.trim() !== '' && password !== ''

  const [resending, setResending] = useState(false)
  async function handleResendVerify() {
    if (!unverifiedEmail) return
    setResending(true)
    const { response } = await apiClient.POST('/api/auth/request-verify-token', {
      body: { email: unverifiedEmail },
    })
    setResending(false)
    if (response.ok) {
      enqueueSnackbar('Correo reenviado. Revisa tu bandeja de entrada.', {
        variant: 'success',
      })
    } else {
      enqueueSnackbar('No se pudo reenviar el correo. Inténtalo de nuevo.', {
        variant: 'error',
      })
    }
  }

  return (
    <Stack spacing={3}>
      <Typography variant="h4" component="h1">
        Iniciar sesión
      </Typography>
      <Form method="post" noValidate>
        <Stack spacing={2}>
          <TextField
            name="email"
            type="email"
            label="Email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
          />
          <TextField
            name="password"
            type="password"
            label="Contraseña"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            fullWidth
          />
          {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
          {unverifiedEmail && (
            <Alert severity="warning">
              <Box>Verifica tu email antes de iniciar sesión.</Box>
              <Button
                size="small"
                onClick={handleResendVerify}
                disabled={resending}
                sx={{ mt: 1, p: 0 }}
              >
                {resending ? 'Reenviando…' : '¿Reenviar?'}
              </Button>
            </Alert>
          )}
          <Button type="submit" variant="contained" disabled={submitting || !canSubmit} fullWidth>
            {submitting ? 'Iniciando sesión…' : 'Iniciar sesión'}
          </Button>
        </Stack>
      </Form>
      <Typography variant="body2" align="right">
        <MuiLink component={RouterLink} to="/forgot-password">
          ¿Olvidaste tu contraseña?
        </MuiLink>
      </Typography>
      <Divider>o</Divider>
      <GoogleSignInButton label="Iniciar sesión con Google" />
      <Typography variant="body2">
        ¿No tienes cuenta?{' '}
        <MuiLink component={RouterLink} to="/register">
          Regístrate
        </MuiLink>
      </Typography>
    </Stack>
  )
}
