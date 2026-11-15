import LocationOnOutlinedIcon from '@mui/icons-material/LocationOnOutlined'
import { Button, CardActionArea, Paper, Skeleton, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router'
import {
  pointPricingState,
  pointTitle,
  STATUS_LABELS,
  shortPriceLabel,
  standardLabel,
} from '@/features/points/display'
import { StatusDot } from '@/features/points/StatusDot'
import type { Point } from '@/features/points/usePoint'
import { useGeolocation } from '@/hooks/useGeolocation'
import { formatDecimal } from '@/lib/format'
import { type NearbyPoint, useNearbyPoints } from './useNearbyPoints'

function connectorStandards(point: Point): string[] {
  const standards = new Set<string>()
  for (const evse of point.evses) {
    for (const connector of evse.connectors) standards.add(connector.standard)
  }
  return [...standards].slice(0, 2).map(standardLabel)
}

function NearbyCard({ point }: { point: NearbyPoint }) {
  const price = pointPricingState(point)
  return (
    <Paper
      sx={{
        transition: 'border-color 120ms',
        '&:hover': { borderColor: 'primary.main' },
      }}
    >
      <CardActionArea component={RouterLink} to={`/points/${point.id}`} sx={{ p: 1.75 }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 0.5 }}>
          <StatusDot status={point.aggregate_status} />
          <Typography variant="caption" color="text.secondary">
            {STATUS_LABELS[point.aggregate_status]}
          </Typography>
          <Typography variant="numeric" sx={{ ml: 'auto', fontSize: 12 }} color="text.secondary">
            {formatDecimal(point.distanceKm, 1)} km
          </Typography>
        </Stack>
        <Typography sx={{ fontWeight: 600 }} noWrap>
          {pointTitle(point)}
        </Typography>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'baseline', mt: 0.5 }}>
          {price !== null &&
            (price.kind === 'per_kwh' || price.kind === 'free' ? (
              <Typography variant="numeric" sx={{ fontWeight: 600 }}>
                {shortPriceLabel(price)}
              </Typography>
            ) : (
              <Typography variant="body2" color="text.secondary">
                {shortPriceLabel(price)}
              </Typography>
            ))}
          <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }} noWrap>
            {connectorStandards(point).join(' · ')}
          </Typography>
        </Stack>
      </CardActionArea>
    </Paper>
  )
}

export function NearbyPoints() {
  const geo = useGeolocation()
  const nearby = useNearbyPoints(geo.coords)

  if (geo.status === 'denied' || geo.status === 'unavailable') {
    return (
      <Paper sx={{ p: 2, textAlign: 'center' }}>
        <LocationOnOutlinedIcon sx={{ color: 'text.disabled', mb: 0.5 }} />
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          {geo.status === 'denied'
            ? 'Activa la ubicación para ver puntos cercanos.'
            : 'Tu dispositivo no permite obtener la ubicación.'}
        </Typography>
        {geo.status === 'denied' && (
          <Button variant="outlined" size="small" onClick={geo.request}>
            Reintentar
          </Button>
        )}
      </Paper>
    )
  }

  if (geo.status !== 'granted' || nearby.isPending) {
    return (
      <Stack spacing={1.5}>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} variant="rounded" height={84} />
        ))}
      </Stack>
    )
  }

  if (nearby.isError) {
    return (
      <Typography variant="body2" color="text.secondary">
        No se pudieron cargar los puntos cercanos.
      </Typography>
    )
  }

  if (nearby.data.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No hay puntos de carga cerca de ti.
      </Typography>
    )
  }

  return (
    <Stack spacing={1.5}>
      {nearby.data.map((point) => (
        <NearbyCard key={point.id} point={point} />
      ))}
    </Stack>
  )
}
