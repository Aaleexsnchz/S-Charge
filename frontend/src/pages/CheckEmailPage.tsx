import { useState } from 'react'
import { Button, Stack, Typography } from '@mui/material'
import { Link as RouterLink, useSearchParams } from 'react-router'
import { useSnackbar } from 'notistack'
import { apiClient } from '../api/client'

export function CheckEmailPage() {
  const [searchParams] = useSearchParams()
  const email = searchParams.get('email') ?? ''
  const { enqueueSnackbar } = useSnackbar()
  const [resending, setResending] = useState(false)

  async function handleResend() {
    if (!email) return
    setResending(true)
    const { response } = await apiClient.POST(
      '/api/auth/request-verify-token',
      { body: { email } },
    )
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
        Revisa tu email
      </Typography>
      <Typography variant="body1">
        {email
          ? `Te hemos enviado un enlace a ${email}. Haz clic en él para verificar tu cuenta.`
          : 'Te hemos enviado un enlace de verificación a tu correo.'}
      </Typography>
      <Button
        variant="outlined"
        onClick={handleResend}
        disabled={!email || resending}
        fullWidth
      >
        {resending ? 'Reenviando…' : 'Reenviar correo'}
      </Button>
      <Typography variant="body2">
        <RouterLink to="/login">Volver al inicio de sesión</RouterLink>
      </Typography>
    </Stack>
  )
}
