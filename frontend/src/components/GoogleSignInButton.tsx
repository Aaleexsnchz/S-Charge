import { useState } from 'react'
import { Button } from '@mui/material'
import GoogleIcon from '@mui/icons-material/Google'
import { apiClient } from '../api/client'

export function GoogleSignInButton({ label }: { label: string }) {
  const [loading, setLoading] = useState(false)

  async function onClick() {
    setLoading(true)
    const { data } = await apiClient.GET('/api/auth/google/authorize')
    if (!data) {
      setLoading(false)
      window.location.href = '/login?error=oauth_failed'
      return
    }
    window.location.href = data.authorization_url
  }

  return (
    <Button
      type="button"
      variant="outlined"
      onClick={onClick}
      disabled={loading}
      fullWidth
      startIcon={<GoogleIcon />}
      sx={{
        color: 'text.primary',
        borderColor: 'divider',
        textTransform: 'none',
      }}
    >
      {label}
    </Button>
  )
}
