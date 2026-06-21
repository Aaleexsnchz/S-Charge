import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material'
import { useNavigate } from 'react-router'
import {
  googleMapsDirectionsUrl,
  powerLabel,
  priceLabel,
  STATUS_CHIP_COLOR,
  STATUS_LABELS,
  standardLabel,
} from '../points/display'
import { usePoint } from '../points/usePoint'

type Props = {
  pointId: string | null
  onClose: () => void
}

export function PointSheet({ pointId, onClose }: Props) {
  const navigate = useNavigate()
  const { data: point, isPending, isError } = usePoint(pointId)

  const connectors =
    point?.evses.flatMap((evse) => evse.connectors.map((connector) => ({ evse, connector }))) ?? []

  return (
    <Drawer
      anchor="bottom"
      open={pointId !== null}
      onClose={onClose}
      slotProps={{
        paper: {
          sx: {
            borderTopLeftRadius: 16,
            borderTopRightRadius: 16,
            pb: 'env(safe-area-inset-bottom)',
            maxHeight: '70svh',
          },
        },
      }}
    >
      <Box sx={{ p: 2.5 }}>
        {isPending && pointId !== null && (
          <Stack spacing={1}>
            <Skeleton variant="text" width="60%" height={32} />
            <Skeleton variant="text" width="80%" />
            <Skeleton variant="rounded" height={56} />
          </Stack>
        )}
        {isError && <Alert severity="error">No se pudo cargar el punto de carga.</Alert>}
        {point && (
          <Stack spacing={1.5}>
            <Stack
              direction="row"
              spacing={1}
              sx={{ alignItems: 'flex-start', justifyContent: 'space-between' }}
            >
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="h6" component="h2" noWrap>
                  {point.name ?? point.cpo_name ?? 'Punto de carga'}
                </Typography>
                {point.name && point.cpo_name && (
                  <Typography variant="body2" color="text.secondary" noWrap>
                    {point.cpo_name}
                  </Typography>
                )}
              </Box>
              <Chip
                size="small"
                label={STATUS_LABELS[point.aggregate_status]}
                color={STATUS_CHIP_COLOR[point.aggregate_status]}
              />
            </Stack>

            <Typography variant="body2" color="text.secondary">
              {point.address}, {point.city}
              {point.opening_24_7 ? ' · 24h' : ''}
            </Typography>

            <Divider />

            <Stack spacing={0.75} sx={{ maxHeight: '24svh', overflowY: 'auto' }}>
              {connectors.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  Sin información de conectores.
                </Typography>
              )}
              {connectors.map(({ connector }) => (
                <Stack
                  key={connector.id}
                  direction="row"
                  spacing={1}
                  sx={{ alignItems: 'center', justifyContent: 'space-between' }}
                >
                  <Typography variant="body2">
                    {standardLabel(connector.standard)}
                    {powerLabel(connector.max_electric_power)
                      ? ` · ${powerLabel(connector.max_electric_power)}`
                      : ''}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {priceLabel(connector.tariff?.price_per_kwh) ?? '—'}
                  </Typography>
                </Stack>
              ))}
            </Stack>

            <Stack direction="row" spacing={1.5} sx={{ pt: 0.5 }}>
              <Button variant="outlined" fullWidth onClick={() => navigate(`/points/${point.id}`)}>
                Detalles
              </Button>
              <Button
                variant="contained"
                fullWidth
                onClick={() =>
                  window.open(
                    googleMapsDirectionsUrl(point.latitude, point.longitude),
                    '_blank',
                    'noopener',
                  )
                }
              >
                Navegar
              </Button>
            </Stack>
          </Stack>
        )}
      </Box>
    </Drawer>
  )
}
