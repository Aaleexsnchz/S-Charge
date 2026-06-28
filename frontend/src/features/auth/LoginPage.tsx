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
    <Stack spacing={2.5}>
      <GoogleSignInButton label="Continuar con Google" />
      <Divider sx={{ color: 'text.disabled', fontSize: 13 }}>o</Divider>
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
          <Box sx={{ textAlign: 'right' }}>
            <MuiLink component={RouterLink} to="/forgot-password" variant="body2" underline="hover">
              ¿Olvidaste tu contraseña?
            </MuiLink>
          </Box>
          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={submitting || !canSubmit}
            fullWidth
          >
            {submitting ? 'Iniciando sesión…' : 'Iniciar sesión'}
          </Button>
        </Stack>
      </Form>
      <Typography variant="body2" align="center" color="text.secondary">
        ¿No tienes cuenta?{' '}
        <MuiLink component={RouterLink} to="/register" sx={{ fontWeight: 500 }}>
          Regístrate
        </MuiLink>
      </Typography>
    </Stack>
  )
}
