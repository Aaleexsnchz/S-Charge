import AddIcon from '@mui/icons-material/Add'
import { Box, Divider, Fab, Paper, Stack, Typography } from '@mui/material'
import { useSnackbar } from 'notistack'
import { Eyebrow } from '@/components/Eyebrow'
import { PlaceholderBadge } from '@/components/PlaceholderBadge'
import { Stat } from '@/components/Stat'
import { StatusDot } from '@/features/points/StatusDot'
import { formatEur } from '@/lib/format'
import { BOTTOM_NAV_HEIGHT } from '@/lib/layout'
import { MOCK_OWNED_POINTS, type MockOwnedPoint } from './myPoints.mock'

const FIGURE_SX = { flex: 1 }
const FIGURE_VALUE_SX = { display: 'block', fontSize: 18, fontWeight: 600 }

function PointCard({ point }: { point: MockOwnedPoint }) {
  return (
    <Paper sx={{ p: 2 }}>
      <Stack direction="row" spacing={1.25} sx={{ alignItems: 'flex-start' }}>
        <StatusDot status={point.status} labelled sx={{ mt: 0.9, flexShrink: 0 }} />
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography sx={{ fontWeight: 600 }} noWrap>
            {point.name}
          </Typography>
          <Typography variant="body2" color="text.secondary" noWrap>
            {point.address}
          </Typography>
        </Box>
      </Stack>

      <Box sx={{ mt: 1, ml: 2.25 }}>
        <Eyebrow>{point.public ? 'Público' : 'Privado'}</Eyebrow>
      </Box>

      <Divider sx={{ my: 1.75 }} />

      <Stack direction="row" spacing={2}>
        <Stat
          sx={FIGURE_SX}
          valueSx={FIGURE_VALUE_SX}
          label="Reservas"
          value={String(point.bookingsThisMonth)}
        />
        <Stat
          sx={FIGURE_SX}
          valueSx={FIGURE_VALUE_SX}
          label="Ingresos"
          value={formatEur(point.earningsEur)}
          unit="€"
        />
      </Stack>
    </Paper>
  )
}

export function MyPointsPage() {
  const { enqueueSnackbar } = useSnackbar()

  return (
    <Box sx={{ p: 2, maxWidth: 600, mx: 'auto', pb: 12 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 0.5 }}>
        <Typography variant="h1">Mis puntos</Typography>
        <PlaceholderBadge />
      </Stack>
      <Box sx={{ mb: 2.5 }}>
        <Eyebrow>Este mes</Eyebrow>
      </Box>

      <Stack spacing={1.5}>
        {MOCK_OWNED_POINTS.map((point) => (
          <PointCard key={point.id} point={point} />
        ))}
      </Stack>

      <Fab
        color="primary"
        aria-label="Registrar punto"
        onClick={() => enqueueSnackbar('Registro de puntos: próximamente', { variant: 'info' })}
        sx={{ position: 'fixed', right: 16, bottom: BOTTOM_NAV_HEIGHT + 16 }}
      >
        <AddIcon />
      </Fab>
    </Box>
  )
}
