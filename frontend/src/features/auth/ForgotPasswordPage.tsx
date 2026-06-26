import { Alert, Button, Link as MuiLink, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { Form, Link as RouterLink, useActionData, useNavigation } from 'react-router'
import type { ForgotPasswordActionData } from './actions'

export function ForgotPasswordPage() {
  const actionData = useActionData() as ForgotPasswordActionData | undefined
  const navigation = useNavigation()
  const submitting = navigation.state === 'submitting'

  const errorMessage = actionData && 'error' in actionData ? actionData.error : null

  const [email, setEmail] = useState('')

  if (actionData && 'submitted' in actionData) {
    return (
      <Stack spacing={3}>
        <Typography variant="h4" component="h1">
          Revisa tu email
        </Typography>
        <Alert severity="info">
          Si existe una cuenta con ese email, recibirás un enlace para restablecer tu contraseña.
        </Alert>
        <Typography variant="body2">
          <MuiLink component={RouterLink} to="/login">
            Volver al inicio de sesión
          </MuiLink>
        </Typography>
      </Stack>
    )
  }

  return (
    <Stack spacing={3}>
      <Typography variant="h4" component="h1">
        Restablecer contraseña
      </Typography>
      <Typography variant="body2">
        Introduce tu email y te enviaremos un enlace para restablecer tu contraseña.
      </Typography>
      {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
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
          <Button
            type="submit"
            variant="contained"
            disabled={submitting || email.trim() === ''}
            fullWidth
          >
            {submitting ? 'Enviando…' : 'Enviar enlace'}
          </Button>
        </Stack>
      </Form>
      <Typography variant="body2">
        <MuiLink component={RouterLink} to="/login">
          Volver al inicio de sesión
        </MuiLink>
      </Typography>
    </Stack>
  )
}
