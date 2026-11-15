import { keyframes } from '@emotion/react'
import VisibilityOffOutlinedIcon from '@mui/icons-material/VisibilityOffOutlined'
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined'
import {
  Alert,
  Box,
  Button,
  Divider,
  IconButton,
  InputAdornment,
  Link as MuiLink,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { alpha } from '@mui/material/styles'
import { useSnackbar } from 'notistack'
import { type ReactNode, useEffect, useRef, useState } from 'react'
import {
  Form,
  Link as RouterLink,
  useActionData,
  useNavigation,
  useSearchParams,
} from 'react-router'
import { BOLT_PATH, BOLT_VIEWBOX } from '@/lib/bolt'
import { tokens } from '@/theme'
import type { LoginActionData } from './actions'
import { GoogleSignInButton } from './GoogleSignInButton'
import { useResendVerification } from './useResendVerification'

const GAUGE_WIDTH = 58
const GAUGE_HEIGHT = 116

/** `pathLength={100}` normalises the outline, so the dash pattern below is read
 *  as percentages of the perimeter rather than user units. */
const travel = keyframes`
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: -100; }
`

function BoltSvg({ children }: { children: ReactNode }) {
  return (
    <Box
      component="svg"
      viewBox={BOLT_VIEWBOX}
      aria-hidden
      sx={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        width: GAUGE_WIDTH,
        height: GAUGE_HEIGHT,
        overflow: 'visible',
      }}
    >
      {children}
    </Box>
  )
}

/** Fills as the two credentials are entered. */
function BoltGauge({ level }: { level: number }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center' }}>
      <Box
        role="img"
        aria-label={`Credenciales completadas: ${Math.round(level * 100)}%`}
        sx={{ position: 'relative', width: GAUGE_WIDTH, height: GAUGE_HEIGHT }}
      >
        <BoltSvg>
          <path
            d={BOLT_PATH}
            fill={alpha(tokens.accent, 0.06)}
            stroke={alpha(tokens.accent, 0.22)}
            strokeWidth={0.3}
          />
        </BoltSvg>

        <Box
          sx={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 0,
            height: `${level * 100}%`,
            overflow: 'hidden',
            transition: 'height 420ms cubic-bezier(0.22, 1, 0.36, 1)',
            '@media (prefers-reduced-motion: reduce)': { transition: 'none' },
          }}
        >
          <BoltSvg>
            <path d={BOLT_PATH} fill={tokens.accent} fillOpacity={0.85} />
          </BoltSvg>
        </Box>

        <BoltSvg>
          <Box
            component="path"
            d={BOLT_PATH}
            pathLength={100}
            fill="none"
            stroke={tokens.accent}
            strokeWidth={0.45}
            strokeLinecap="round"
            strokeLinejoin="round"
            sx={{
              strokeDasharray: '18 82',
              animation: `${travel} 3.2s linear infinite`,
              filter: `drop-shadow(0 0 2px ${alpha(tokens.accent, 0.95)}) drop-shadow(0 0 7px ${alpha(tokens.accent, 0.55)})`,
              '@media (prefers-reduced-motion: reduce)': { animation: 'none' },
            }}
          />
        </BoltSvg>
      </Box>
    </Box>
  )
}

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
  const [showPassword, setShowPassword] = useState(false)
  const canSubmit = email.trim() !== '' && password !== ''
  const charge = (email.trim() !== '' ? 0.5 : 0) + (password !== '' ? 0.5 : 0)

  const { resend, resending } = useResendVerification()
  function handleResendVerify() {
    if (unverifiedEmail) void resend(unverifiedEmail)
  }

  return (
    <Stack spacing={2.5}>
      <BoltGauge level={charge} />

      <Form method="post" noValidate>
        <Stack spacing={2}>
          <TextField
            name="email"
            type="email"
            label="Email"
            autoComplete="email"
            inputMode="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
          />
          <TextField
            name="password"
            type={showPassword ? 'text' : 'password'}
            label="Contraseña"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      size="small"
                      edge="end"
                      aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                      onClick={() => setShowPassword((shown) => !shown)}
                      sx={{ color: 'text.disabled' }}
                    >
                      {showPassword ? (
                        <VisibilityOffOutlinedIcon fontSize="small" />
                      ) : (
                        <VisibilityOutlinedIcon fontSize="small" />
                      )}
                    </IconButton>
                  </InputAdornment>
                ),
              },
            }}
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
          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={submitting || !canSubmit}
            fullWidth
          >
            {submitting ? 'Iniciando sesión…' : 'Iniciar sesión'}
          </Button>
          <Box sx={{ textAlign: 'center' }}>
            <MuiLink
              component={RouterLink}
              to="/forgot-password"
              variant="body2"
              underline="hover"
              color="text.secondary"
            >
              ¿Olvidaste tu contraseña?
            </MuiLink>
          </Box>
        </Stack>
      </Form>

      <Divider sx={{ color: 'text.disabled', fontSize: 13 }}>o</Divider>
      <GoogleSignInButton label="Continuar con Google" />

      <Typography variant="body2" align="center" color="text.secondary">
        ¿No tienes cuenta?{' '}
        <MuiLink component={RouterLink} to="/register" sx={{ fontWeight: 500 }}>
          Regístrate
        </MuiLink>
      </Typography>
    </Stack>
  )
}
