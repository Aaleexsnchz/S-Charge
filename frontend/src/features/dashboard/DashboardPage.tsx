import { Box, Button, Paper, Stack, Typography } from '@mui/material'
import { alpha } from '@mui/material/styles'
import type { ReactNode } from 'react'
import { Link as RouterLink } from 'react-router'
import { Eyebrow } from '@/components/Eyebrow'
import { PlaceholderBadge } from '@/components/PlaceholderBadge'
import { Stat } from '@/components/Stat'
import { useCurrentUser } from '@/features/auth/currentUser'
import { tokens } from '@/theme'
import { MOCK_MONTH_SPEND, MOCK_NEXT_RESERVATION, MOCK_STATS } from './dashboard.mock'
import { NearbyPoints } from './NearbyPoints'

const DATE_FORMAT = new Intl.DateTimeFormat('es-ES', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
})

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
      sx={{ alignItems: 'center', justifyContent: 'space-between', mt: 4, mb: 1.5 }}
    >
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', minWidth: 0 }}>
        <Eyebrow>{title}</Eyebrow>
        {badge && <PlaceholderBadge />}
      </Stack>
      {action}
    </Stack>
  )
}

export function DashboardPage() {
  const firstName = useCurrentUser()?.name?.trim().split(' ')[0]

  return (
    <Box sx={{ p: 2, maxWidth: 600, mx: 'auto', pb: 4 }}>
      <Eyebrow>{DATE_FORMAT.format(new Date())}</Eyebrow>
      <Typography variant="h1" sx={{ mt: 0.5 }}>
        {firstName ? `Hola, ${firstName}` : 'Hola'}
      </Typography>

      {MOCK_NEXT_RESERVATION && (
        <>
          <SectionHeader title="Próxima reserva" badge />
          <Paper sx={{ p: 2, pl: 2.25, position: 'relative', overflow: 'hidden' }}>
            <Box
              sx={{
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: 2,
                bgcolor: 'primary.main',
                boxShadow: `0 0 10px ${alpha(tokens.accent, 0.55)}`,
              }}
            />
            <Stack
              direction="row"
              sx={{ alignItems: 'flex-start', justifyContent: 'space-between', gap: 2 }}
            >
              <Box sx={{ minWidth: 0 }}>
                <Typography sx={{ fontWeight: 600 }} noWrap>
                  {MOCK_NEXT_RESERVATION.station}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                  {MOCK_NEXT_RESERVATION.when}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {MOCK_NEXT_RESERVATION.connector}
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'right', flexShrink: 0 }}>
                <Eyebrow>Empieza en</Eyebrow>
                <Typography
                  variant="numeric"
                  sx={{
                    display: 'block',
                    fontSize: 20,
                    fontWeight: 700,
                    color: 'primary.main',
                    lineHeight: 1.2,
                  }}
                >
                  {MOCK_NEXT_RESERVATION.startsIn}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </>
      )}

      <SectionHeader title="Este mes" badge />
      <Box>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'baseline' }}>
          <Typography
            variant="numeric"
            sx={{ fontSize: 44, fontWeight: 700, lineHeight: 1, color: 'primary.main' }}
          >
            {MOCK_MONTH_SPEND.value}
          </Typography>
          <Typography variant="numeric" sx={{ fontSize: 15, color: 'text.secondary' }}>
            {MOCK_MONTH_SPEND.unit}
          </Typography>
        </Stack>
        <Box
          sx={{
            mt: 2,
            pt: 2,
            borderTop: 1,
            borderColor: 'divider',
            display: 'flex',
            justifyContent: 'space-between',
          }}
        >
          {MOCK_STATS.map((stat) => (
            <Stat
              key={stat.label}
              label={stat.label}
              value={stat.value}
              unit={stat.unit}
              sx={{ flex: 1, minWidth: 0 }}
              valueSx={{ fontSize: 17, fontWeight: 600, mt: 0.25 }}
            />
          ))}
        </Box>
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
