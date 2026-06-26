import { Button, Stack, Typography } from '@mui/material'
import { isRouteErrorResponse, useRouteError } from 'react-router'

export function RouteErrorPage() {
  const error = useRouteError()
  const notFound = isRouteErrorResponse(error) && error.status === 404

  return (
    <Stack
      spacing={3}
      sx={{
        minHeight: '100svh',
        alignItems: 'center',
        justifyContent: 'center',
        p: 3,
        textAlign: 'center',
      }}
    >
      <Typography variant="h4" component="h1">
        {notFound ? 'Página no encontrada' : 'Algo ha ido mal'}
      </Typography>
      <Typography variant="body1" color="text.secondary">
        {notFound
          ? 'La página que buscas no existe.'
          : 'No se ha podido cargar la aplicación. Comprueba tu conexión e inténtalo de nuevo.'}
      </Typography>
      <Button variant="contained" onClick={() => window.location.assign('/')}>
        Volver al inicio
      </Button>
    </Stack>
  )
}
