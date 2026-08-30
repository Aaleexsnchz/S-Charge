import AddIcon from '@mui/icons-material/Add'
import { Box, Divider, Fab, Paper, Stack, Typography } from '@mui/material'
import { useSnackbar } from 'notistack'
import { Eyebrow } from '@/components/Eyebrow'
import { PlaceholderBadge } from '@/components/PlaceholderBadge'
import { STATUS_DOT_COLOR, STATUS_DOT_GLOW, STATUS_LABELS } from '@/features/points/display'
import { MOCK_OWNED_POINTS, type MockOwnedPoint } from './myPoints.mock'

function Figure({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <Box sx={{ flex: 1 }}>
      <Eyebrow>{label}</Eyebrow>
      <Typography variant="numeric" sx={{ display: 'block', fontSize: 18, fontWeight: 600 }}>
        {value}
        {unit && (
          <Box component="span" sx={{ fontSize: 11, color: 'text.secondary', ml: 0.4 }}>
            {unit}
          </Box>
        )}
      </Typography>
    </Box>
  )
}

function PointCard({ point }: { point: MockOwnedPoint }) {
  return (
    <Paper sx={{ p: 2 }}>
      <Stack direction="row" spacing={1.25} sx={{ alignItems: 'flex-start' }}>
        <Box
          role="img"
          aria-label={STATUS_LABELS[point.status]}
          sx={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            mt: 0.9,
            flexShrink: 0,
            bgcolor: STATUS_DOT_COLOR[point.status],
            boxShadow: STATUS_DOT_GLOW[point.status],
          }}
        />
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
        <Figure label="Reservas" value={String(point.bookingsThisMonth)} />
        <Figure
          label="Ingresos"
          value={point.earningsEur.toLocaleString('es-ES', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
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
        sx={{ position: 'fixed', right: 16, bottom: 80 }}
      >
        <AddIcon />
      </Fab>
    </Box>
  )
}
