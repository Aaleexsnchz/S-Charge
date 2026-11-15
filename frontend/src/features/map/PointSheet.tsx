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
import { ConnectorRow } from '@/features/points/ConnectorRow'
import {
  googleMapsDirectionsUrl,
  pointTitle,
  STATUS_CHIP_COLOR,
  STATUS_LABELS,
} from '@/features/points/display'
import { usePoint } from '@/features/points/usePoint'

type Props = {
  pointId: string | null
  onClose: () => void
}

export function PointSheet({ pointId, onClose }: Props) {
  const navigate = useNavigate()
  const { data: point, isPending, isError } = usePoint(pointId)

  const connectors = point?.evses.flatMap((evse) => evse.connectors) ?? []

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
      <Box
        sx={{
          width: 36,
          height: 4,
          bgcolor: 'divider',
          borderRadius: 2,
          mx: 'auto',
          mt: 1,
          mb: -0.5,
        }}
      />
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
                  {pointTitle(point)}
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
              {connectors.map((connector) => (
                <ConnectorRow key={connector.id} connector={connector} />
              ))}
            </Stack>

            <Stack direction="row" spacing={1.5} sx={{ pt: 0.5 }}>
              <Button variant="outlined" fullWidth onClick={() => navigate(`/points/${point.id}`)}>
                Detalles
              </Button>
              <Button
                variant="contained"
                fullWidth
                component="a"
                href={googleMapsDirectionsUrl(point.latitude, point.longitude)}
                target="_blank"
                rel="noopener noreferrer"
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
