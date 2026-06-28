import { Box, Button, Paper, Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'
import { Link as RouterLink, useRouteLoaderData } from 'react-router'
import { PlaceholderBadge } from '@/components/PlaceholderBadge'
import type { RootLoaderData } from '@/features/auth/loaders'
import { MOCK_NEXT_RESERVATION, MOCK_STATS } from './dashboard.mock'
import { NearbyPoints } from './NearbyPoints'

const DATE_FORMAT = new Intl.DateTimeFormat('es-ES', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function SectionHeader({
  title,
  badge = false,
  action,
}: {
  title: string
  badge?: boolean
  action?: ReactNode
}) {
  return (
    <Stack
      direction="row"
      sx={{ alignItems: 'center', justifyContent: 'space-between', mt: 3, mb: 1.5 }}
    >
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', minWidth: 0 }}>
        <Typography variant="h3">{title}</Typography>
        {badge && <PlaceholderBadge />}
      </Stack>
      {action}
    </Stack>
  )
}

export function DashboardPage() {
  const data = useRouteLoaderData('root') as RootLoaderData | undefined
  const firstName = data?.user?.name?.trim().split(' ')[0]
  const today = capitalize(DATE_FORMAT.format(new Date()))

  return (
    <Box sx={{ p: 2, maxWidth: 600, mx: 'auto', pb: 4 }}>
      <Typography variant="h1">{firstName ? `Hola, ${firstName}` : 'Hola'}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        {today}
      </Typography>

      {MOCK_NEXT_RESERVATION && (
        <>
          <SectionHeader title="Próxima reserva" badge />
          <Paper sx={{ p: 2 }}>
            <Typography sx={{ fontWeight: 600 }}>{MOCK_NEXT_RESERVATION.station}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {MOCK_NEXT_RESERVATION.when} · {MOCK_NEXT_RESERVATION.connector}
            </Typography>
            <Box sx={{ mt: 1.5 }}>
              <Typography variant="overline" color="text.secondary">
                Empieza en
              </Typography>
              <Typography
                variant="numeric"
                sx={{
                  display: 'block',
                  fontSize: 22,
                  fontWeight: 700,
                  color: 'primary.main',
                  lineHeight: 1,
                }}
              >
                {MOCK_NEXT_RESERVATION.startsIn}
              </Typography>
            </Box>
          </Paper>
        </>
      )}

      <SectionHeader title="Resumen" badge />
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
        {MOCK_STATS.map((stat) => (
          <Paper key={stat.label} sx={{ p: 1.75 }}>
            <Typography variant="caption" color="text.secondary">
              {stat.label}
            </Typography>
            <Typography
              variant="numeric"
              sx={{ display: 'block', fontSize: 24, fontWeight: 700, mt: 0.5 }}
            >
              {stat.unit === '€' && (
                <Box component="span" sx={{ fontSize: 16, color: 'text.secondary', mr: 0.25 }}>
                  €
                </Box>
              )}
              {stat.value}
              {stat.unit && stat.unit !== '€' && (
                <Box component="span" sx={{ fontSize: 12, color: 'text.secondary', ml: 0.5 }}>
                  {stat.unit}
                </Box>
              )}
            </Typography>
          </Paper>
        ))}
      </Box>

      <SectionHeader
        title="Puntos cercanos"
        action={
          <Button component={RouterLink} to="/map" size="small" variant="text">
            Ver mapa
          </Button>
        }
      />
      <NearbyPoints />
    </Box>
  )
}
