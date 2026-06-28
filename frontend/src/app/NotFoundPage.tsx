import { Button, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router'

export function NotFoundPage() {
  return (
    <Stack spacing={2} sx={{ p: 3, maxWidth: 480, mx: 'auto', textAlign: 'center', pt: 10 }}>
      <Typography variant="numeric" sx={{ fontSize: 48, fontWeight: 700, color: 'primary.main' }}>
        404
      </Typography>
      <Typography variant="h3">Página no encontrada</Typography>
      <Typography variant="body2" color="text.secondary">
        La ruta que has solicitado no existe.
      </Typography>
      <Button component={RouterLink} to="/" variant="contained" sx={{ alignSelf: 'center', mt: 1 }}>
        Volver al inicio
      </Button>
    </Stack>
  )
}
