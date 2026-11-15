import { Button, Link as MuiLink, Stack, Typography } from '@mui/material'
import { Link as RouterLink, useSearchParams } from 'react-router'
import { useResendVerification } from './useResendVerification'

export function CheckEmailPage() {
  const [searchParams] = useSearchParams()
  const email = searchParams.get('email') ?? ''
  const { resend, resending } = useResendVerification()

  function handleResend() {
    if (email) void resend(email)
  }

  return (
    <Stack spacing={3}>
      <Typography variant="h3" component="h1">
        Revisa tu email
      </Typography>
      <Typography variant="body1">
        {email
          ? `Te hemos enviado un enlace a ${email}. Haz clic en él para verificar tu cuenta.`
          : 'Te hemos enviado un enlace de verificación a tu correo.'}
      </Typography>
      <Button variant="outlined" onClick={handleResend} disabled={!email || resending} fullWidth>
        {resending ? 'Reenviando…' : 'Reenviar correo'}
      </Button>
      <Typography variant="body2" align="center">
        <MuiLink component={RouterLink} to="/login">
          Volver al inicio de sesión
        </MuiLink>
      </Typography>
    </Stack>
  )
}
