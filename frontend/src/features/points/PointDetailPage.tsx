import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  Paper,
  Stack,
  Typography,
} from '@mui/material'
import { useState } from 'react'
import { Link as RouterLink, useLocation, useNavigate, useParams } from 'react-router'
import { type ConnectorOption, SimulateDialog } from '@/features/simulate/SimulateDialog'
import { formatEur } from '@/lib/format'
import { ConnectorRow } from './ConnectorRow'
import {
  connectorLabel,
  evseStatus,
  googleMapsDirectionsUrl,
  longPriceLabel,
  type PricingState,
  pointPricingState,
  pointTitle,
  STATUS_CHIP_COLOR,
  STATUS_LABELS,
} from './display'
import { PriceScheduleCard } from './PriceScheduleCard'
import { PointNotFoundError, usePoint } from './usePoint'

const WEEKDAY_LABELS = ['', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

function PriceCard({ state }: { state: PricingState }) {
  if (state.kind === 'per_kwh') {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="overline" color="text.secondary">
          Desde
        </Typography>
        <Typography
          variant="numeric"
          sx={{
            display: 'block',
            fontSize: 32,
            fontWeight: 700,
            color: 'primary.main',
            lineHeight: 1.1,
          }}
        >
          {formatEur(state.pricePerKwh)} €
        </Typography>
        <Typography variant="body2" color="text.secondary">
          por kWh
        </Typography>
      </Paper>
    )
  }

  if (state.kind === 'free') {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="overline" color="text.secondary">
          Precio
        </Typography>
        <Typography
          sx={{
            display: 'block',
            fontSize: 32,
            fontWeight: 700,
            color: 'success.main',
            lineHeight: 1.1,
          }}
        >
          Gratis
        </Typography>
      </Paper>
    )
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="overline" color="text.secondary">
        Precio
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {longPriceLabel(state)}
      </Typography>
    </Paper>
  )
}

export function PointDetailPage() {
  const { pointId } = useParams<{ pointId: string }>()
  const navigate = useNavigate()
  // React Router keys the first entry of a session 'default': opened from a
  // shared link or a PWA deep link, going back would leave the app.
  const isFirstEntry = useLocation().key === 'default'
  const { data: point, isPending, error } = usePoint(pointId ?? null)
  const [simulateOpen, setSimulateOpen] = useState(false)

  if (isPending) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!point) {
    return (
      <Stack spacing={2} sx={{ p: 3, maxWidth: 480, mx: 'auto' }}>
        <Alert severity={error instanceof PointNotFoundError ? 'warning' : 'error'}>
          {error instanceof PointNotFoundError
            ? 'Este punto de carga no existe o ya no está disponible.'
            : 'No se pudo cargar el punto de carga. Inténtalo de nuevo.'}
        </Alert>
        <Button component={RouterLink} to="/map" variant="outlined">
          Volver al mapa
        </Button>
      </Stack>
    )
  }

  const connectorOptions: ConnectorOption[] = point.evses.flatMap((evse) =>
    evse.connectors.map((connector) => ({
      id: connector.id,
      isDC: connector.power_type === 'DC',
      label: connectorLabel(connector),
    })),
  )

  const pointPrice = pointPricingState(point)

  const connectorLabels = new Map(connectorOptions.map((option) => [option.id, option.label]))

  return (
    <Box sx={{ overflowY: 'auto', height: '100%' }}>
      <Stack spacing={2} sx={{ p: 2, maxWidth: 600, mx: 'auto', pb: 4 }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
          <IconButton
            aria-label="Volver"
            onClick={() => (isFirstEntry ? navigate('/map') : navigate(-1))}
            edge="start"
          >
            <ArrowBackIcon />
          </IconButton>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="h5" component="h1" noWrap>
              {pointTitle(point)}
            </Typography>
            {point.name && point.cpo_name && (
              <Typography variant="body2" color="text.secondary" noWrap>
                {point.cpo_name}
              </Typography>
            )}
          </Box>
        </Stack>

        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
          <Chip
            size="small"
            label={STATUS_LABELS[point.aggregate_status]}
            color={STATUS_CHIP_COLOR[point.aggregate_status]}
          />
          {point.opening_24_7 && <Chip size="small" label="Abierto 24h" variant="outlined" />}
          {point.parking_type && (
            <Chip size="small" label={point.parking_type} variant="outlined" />
          )}
        </Stack>

        {pointPrice !== null && <PriceCard state={pointPrice} />}

        <PriceScheduleCard schedules={point.price_schedules} connectorLabels={connectorLabels} />

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Dirección
          </Typography>
          <Typography variant="body2">
            {point.address}, {point.postal_code ? `${point.postal_code} ` : ''}
            {point.city}
            {point.region ? ` (${point.region})` : ''}
          </Typography>
          {!point.opening_24_7 && point.opening_hours && point.opening_hours.length > 0 && (
            <>
              <Typography variant="subtitle2" sx={{ mt: 1.5 }} gutterBottom>
                Horario
              </Typography>
              <Stack spacing={0.25}>
                {point.opening_hours.map((slot) => (
                  <Typography
                    key={`${slot.weekday}-${slot.period_begin}-${slot.period_end}`}
                    variant="body2"
                    color="text.secondary"
                  >
                    {WEEKDAY_LABELS[Number(slot.weekday)] ?? String(slot.weekday)}{' '}
                    {String(slot.period_begin)}–{String(slot.period_end)}
                  </Typography>
                ))}
              </Stack>
            </>
          )}
        </Paper>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Puntos de conexión ({point.evses.length})
          </Typography>
          <Stack spacing={1.5} divider={<Divider flexItem />}>
            {point.evses.map((evse, index) => (
              <Box key={evse.id}>
                <Stack
                  direction="row"
                  spacing={1}
                  sx={{ alignItems: 'center', justifyContent: 'space-between' }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {evse.evse_id ?? `Plaza ${index + 1}`}
                  </Typography>
                  {evse.status !== null && (
                    <Chip
                      size="small"
                      label={evseStatus(evse.status).label}
                      color={evseStatus(evse.status).color}
                      variant="outlined"
                    />
                  )}
                </Stack>
                <Stack spacing={0.5} sx={{ mt: 0.75 }}>
                  {evse.connectors.map((connector) => (
                    <ConnectorRow key={connector.id} connector={connector} showPowerType />
                  ))}
                </Stack>
              </Box>
            ))}
          </Stack>
        </Paper>

        {connectorOptions.length > 0 && (
          <Button variant="outlined" size="large" onClick={() => setSimulateOpen(true)}>
            Simular carga
          </Button>
        )}

        <Button
          variant="contained"
          size="large"
          component="a"
          href={googleMapsDirectionsUrl(point.latitude, point.longitude)}
          target="_blank"
          rel="noopener noreferrer"
        >
          Navegar
        </Button>
      </Stack>

      <SimulateDialog
        open={simulateOpen}
        onClose={() => setSimulateOpen(false)}
        connectors={connectorOptions}
      />
    </Box>
  )
}
