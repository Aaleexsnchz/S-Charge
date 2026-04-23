import { Box, Button, Container, Stack, Typography } from '@mui/material'
import { Form, useRouteLoaderData } from 'react-router'
import type { RootLoaderData } from '../auth/loaders'

export function ProfilePage() {
  const data = useRouteLoaderData('root') as RootLoaderData | undefined
  const user = data?.user
  if (!user) return null

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
      <Stack spacing={3}>
        <Typography variant="h4" component="h1">
          Mi perfil
        </Typography>
        {user.name && (
          <Box>
            <Typography variant="overline" color="text.secondary">
              Nombre
            </Typography>
            <Typography>{user.name}</Typography>
          </Box>
        )}
        <Box>
          <Typography variant="overline" color="text.secondary">
            Email
          </Typography>
          <Typography>{user.email}</Typography>
        </Box>
        <Form method="post" action="/logout">
          <Button type="submit" variant="outlined" color="error">
            Cerrar sesión
          </Button>
        </Form>
      </Stack>
    </Container>
  )
}
