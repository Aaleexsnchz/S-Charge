import { useSnackbar } from 'notistack'
import { useState } from 'react'
import { apiClient } from '@/lib/api/client'

export function useResendVerification() {
  const { enqueueSnackbar } = useSnackbar()
  const [resending, setResending] = useState(false)

  async function resend(email: string) {
    setResending(true)
    let ok = false
    try {
      const { response } = await apiClient.POST('/api/auth/request-verify-token', {
        body: { email },
      })
      ok = response.ok
    } catch {
      // A network failure reads the same as a refused request.
    } finally {
      setResending(false)
    }
    if (ok) {
      enqueueSnackbar('Correo reenviado. Revisa tu bandeja de entrada.', { variant: 'success' })
    } else {
      enqueueSnackbar('No se pudo reenviar el correo. Inténtalo de nuevo.', { variant: 'error' })
    }
  }

  return { resend, resending }
}
