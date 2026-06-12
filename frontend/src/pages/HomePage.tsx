import { Button, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router'

export function HomePage() {
  return (
    <Stack spacing={2} sx={{ p: 3, maxWidth: 600, mx: 'auto' }}>
      <Typography variant="h5" component="h2">
        Inicio
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Encuentra puntos de carga para tu vehículo eléctrico en toda España.
      </Typography>
      <Button component={RouterLink} to="/map" variant="contained" sx={{ alignSelf: 'flex-start' }}>
        Ver mapa de puntos
      </Button>
    </Stack>
  )
}
