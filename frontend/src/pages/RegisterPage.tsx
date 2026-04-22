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

export function RegisterPage() {
  const actionData = useActionData() as AuthActionError | undefined
  const navigation = useNavigation()
  const submitting = navigation.state === 'submitting'

  return (
    <Stack spacing={3}>
      <Typography variant="h4" component="h1">
        Crear cuenta
      </Typography>
      <Form method="post">
        <Stack spacing={2}>
          <TextField
            name="name"
            type="text"
            label="Nombre (opcional)"
            autoComplete="name"
            fullWidth
          />
          <TextField
            name="email"
            type="email"
            label="Email"
            autoComplete="email"
            required
            fullWidth
          />
          <TextField
            name="password"
            type="password"
            label="Contraseña"
            autoComplete="new-password"
            helperText="Mínimo 12 caracteres"
            required
            fullWidth
            inputProps={{ minLength: 12 }}
          />
          {actionData?.error && (
            <Alert severity="error">{actionData.error}</Alert>
          )}
          <Button
            type="submit"
            variant="contained"
            disabled={submitting}
            fullWidth
          >
            {submitting ? 'Creando cuenta…' : 'Crear cuenta'}
          </Button>
        </Stack>
      </Form>
      <Typography variant="body2">
        ¿Ya tienes cuenta?{' '}
        <MuiLink component={RouterLink} to="/login">
          Inicia sesión
        </MuiLink>
      </Typography>
    </Stack>
  )
}
