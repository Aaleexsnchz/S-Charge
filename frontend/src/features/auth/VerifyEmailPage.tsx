import { CircularProgress, Stack, Typography } from '@mui/material'
import { useSnackbar } from 'notistack'
import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { apiClient } from '@/lib/api/client'

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const navigate = useNavigate()
  const { enqueueSnackbar } = useSnackbar()
  const fired = useRef(false)

  useEffect(() => {
    if (fired.current) return
    fired.current = true

    if (!token) {
      enqueueSnackbar('Enlace de verificación inválido.', { variant: 'error' })
      navigate('/login?error=verify_failed', { replace: true })
      return
    }

    void (async () => {
      let ok = false
      try {
        const { response } = await apiClient.POST('/api/auth/verify', { body: { token } })
        ok = response.ok
      } catch {
        // Offline: fall through to the failure path rather than spin forever.
      }
      if (ok) {
        enqueueSnackbar('Email verificado. Ya puedes iniciar sesión.', {
          variant: 'success',
        })
        navigate('/login', { replace: true })
      } else {
        enqueueSnackbar('No se pudo verificar el email.', { variant: 'error' })
        navigate('/login?error=verify_failed', { replace: true })
      }
    })()
  }, [token, navigate, enqueueSnackbar])

  return (
    <Stack spacing={3} sx={{ alignItems: 'center' }}>
      <CircularProgress />
      <Typography variant="body1">Verificando tu email…</Typography>
    </Stack>
  )
}
