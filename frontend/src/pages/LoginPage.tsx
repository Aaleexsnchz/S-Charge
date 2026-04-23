import { useState } from 'react'
import {
  Alert,
  Button,
  Link as MuiLink,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import {
  Form,
  Link as RouterLink,
  useActionData,
  useNavigation,
} from 'react-router'
import type { AuthActionError } from '../auth/actions'

export function LoginPage() {
  const actionData = useActionData() as AuthActionError | undefined
  const navigation = useNavigation()
  const submitting = navigation.state === 'submitting'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const canSubmit = email.trim() !== '' && password !== ''

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
          {actionData?.error && (
            <Alert severity="error">{actionData.error}</Alert>
          )}
          <Button
            type="submit"
            variant="contained"
            disabled={submitting || !canSubmit}
            fullWidth
          >
            {submitting ? 'Iniciando sesión…' : 'Iniciar sesión'}
          </Button>
        </Stack>
      </Form>
      <Typography variant="body2">
        ¿No tienes cuenta?{' '}
        <MuiLink component={RouterLink} to="/register">
          Regístrate
        </MuiLink>
      </Typography>
    </Stack>
  )
}
