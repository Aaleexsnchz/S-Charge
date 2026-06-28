import AddIcon from '@mui/icons-material/Add'
import { Box, Chip, Divider, Fab, Paper, Stack, Typography } from '@mui/material'
import { useSnackbar } from 'notistack'
import { PlaceholderBadge } from '@/components/PlaceholderBadge'
import { STATUS_CHIP_COLOR, STATUS_LABELS } from '@/features/points/display'
import { MOCK_OWNED_POINTS } from './myPoints.mock'

export function MyPointsPage() {
  const { enqueueSnackbar } = useSnackbar()

  return (
    <Box sx={{ p: 2, maxWidth: 600, mx: 'auto', pb: 12 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 2 }}>
        <Typography variant="h1">Mis puntos</Typography>
        <PlaceholderBadge />
      </Stack>

      <Stack spacing={1.5}>
        {MOCK_OWNED_POINTS.map((point) => (
          <Paper key={point.id} sx={{ p: 2 }}>
            <Stack
              direction="row"
              spacing={1}
              sx={{ alignItems: 'flex-start', justifyContent: 'space-between' }}
            >
              <Box sx={{ minWidth: 0 }}>
                <Typography sx={{ fontWeight: 600 }} noWrap>
                  {point.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" noWrap>
                  {point.address}
                </Typography>
              </Box>
              <Chip
                size="small"
                label={STATUS_LABELS[point.status]}
                color={STATUS_CHIP_COLOR[point.status]}
              />
            </Stack>

            <Box sx={{ mt: 1 }}>
              <Chip size="small" variant="outlined" label={point.public ? 'Público' : 'Privado'} />
            </Box>

            <Divider sx={{ my: 1.5 }} />

            <Stack direction="row" spacing={2}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Reservas este mes
                </Typography>
                <Typography
                  variant="numeric"
                  sx={{ display: 'block', fontSize: 18, fontWeight: 600 }}
                >
                  {point.bookingsThisMonth}
                </Typography>
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Ingresos este mes
                </Typography>
                <Typography
                  variant="numeric"
                  sx={{ display: 'block', fontSize: 18, fontWeight: 600 }}
                >
                  {point.earningsEur.toLocaleString('es-ES', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}{' '}
                  €
                </Typography>
              </Box>
            </Stack>
          </Paper>
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
