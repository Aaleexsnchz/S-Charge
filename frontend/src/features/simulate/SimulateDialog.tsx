import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useState } from 'react'
import { costLabel, durationLabel, energyLabel } from './display'
import { useSimulate } from './useSimulate'
import { useVehicles } from './useVehicles'

export type ConnectorOption = {
  id: string
  label: string
  isDC: boolean
}

type Props = {
  open: boolean
  onClose: () => void
  connectors: ConnectorOption[]
}

export function SimulateDialog({ open, onClose, connectors }: Props) {
  const { data: vehicles, isPending: vehiclesLoading } = useVehicles()
  const simulate = useSimulate()

  const [connectorId, setConnectorId] = useState('')
  const [vehicleId, setVehicleId] = useState('')
  const [socFrom, setSocFrom] = useState('20')
  const [socTo, setSocTo] = useState('80')

  const connector = connectors.find((c) => c.id === connectorId)
  const vehicle = vehicles?.find((v) => v.id === vehicleId)

  const from = Number(socFrom)
  const to = Number(socTo)
  const socValid = from >= 0 && to <= 100 && from < to
  const dcUnsupported = Boolean(connector?.isDC && vehicle && vehicle.max_dc_kw === null)

  const handleClose = () => {
    simulate.reset()
    onClose()
  }

  const handleRun = () => {
    if (!connectorId || !vehicleId || !socValid || dcUnsupported) return
    simulate.mutate({
      connector_id: connectorId,
      vehicle_id: vehicleId,
      soc_from: from,
      soc_to: to,
    })
  }

  const result = simulate.data

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="xs">
      <DialogTitle>Simular carga</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 0.5 }}>
          <FormControl fullWidth size="small">
            <InputLabel id="sim-connector-label">Conector</InputLabel>
            <Select
              labelId="sim-connector-label"
              label="Conector"
              value={connectorId}
              onChange={(e) => {
                setConnectorId(e.target.value)
                simulate.reset()
              }}
            >
              {connectors.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth size="small" disabled={vehiclesLoading}>
            <InputLabel id="sim-vehicle-label">Vehículo</InputLabel>
            <Select
              labelId="sim-vehicle-label"
              label="Vehículo"
              value={vehicleId}
              onChange={(e) => {
                setVehicleId(e.target.value)
                simulate.reset()
              }}
            >
              {(vehicles ?? []).map((v) => (
                <MenuItem key={v.id} value={v.id}>
                  {v.make} {v.model}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Stack direction="row" spacing={2}>
            <TextField
              label="Desde (%)"
              type="number"
              size="small"
              value={socFrom}
              onChange={(e) => {
                setSocFrom(e.target.value)
                simulate.reset()
              }}
              slotProps={{ htmlInput: { min: 0, max: 99 } }}
              fullWidth
            />
            <TextField
              label="Hasta (%)"
              type="number"
              size="small"
              value={socTo}
              onChange={(e) => {
                setSocTo(e.target.value)
                simulate.reset()
              }}
              slotProps={{ htmlInput: { min: 1, max: 100 } }}
              fullWidth
            />
          </Stack>

          {!socValid && (
            <Typography variant="caption" color="error">
              El porcentaje final debe ser mayor que el inicial (0–100).
            </Typography>
          )}
          {dcUnsupported && (
            <Alert severity="warning">
              Este vehículo no admite carga en corriente continua (DC).
            </Alert>
          )}
          {simulate.isError && (
            <Alert severity="error">No se pudo calcular la simulación. Inténtalo de nuevo.</Alert>
          )}

          {result && (
            <Stack spacing={1.5}>
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1 }}>
                <Metric label="Duración" value={durationLabel(result.duration_minutes)} />
                <Metric label="Energía" value={energyLabel(result.energy_kwh)} />
                <Metric label="Coste" value={costLabel(result.cost_eur)} />
              </Box>
              <Paper sx={{ p: 1.5 }}>
                <Stack
                  direction="row"
                  sx={{ justifyContent: 'space-between', alignItems: 'baseline' }}
                >
                  <Typography variant="body2" color="text.secondary">
                    Potencia media
                  </Typography>
                  <Typography variant="numeric" sx={{ fontSize: 14, fontWeight: 600 }}>
                    {result.average_power_kw.toLocaleString('es-ES', { maximumFractionDigits: 1 })}{' '}
                    kW
                  </Typography>
                </Stack>
                {result.price_per_kwh !== null ? (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 0.5, display: 'block' }}
                  >
                    Precio medio de la carga:{' '}
                    {result.price_per_kwh.toLocaleString('es-ES', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}{' '}
                    €/kWh
                  </Typography>
                ) : (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 0.5, display: 'block' }}
                  >
                    El operador no publica precio, así que no se calcula el coste.
                  </Typography>
                )}
              </Paper>
            </Stack>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cerrar</Button>
        <Button
          variant="contained"
          onClick={handleRun}
          disabled={!connectorId || !vehicleId || !socValid || dcUnsupported || simulate.isPending}
          startIcon={simulate.isPending ? <CircularProgress size={16} color="inherit" /> : null}
        >
          Calcular
        </Button>
      </DialogActions>
    </Dialog>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Paper sx={{ p: 1.5, bgcolor: (t) => t.palette.tokens.surface2 }}>
      <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block' }}>
        {label}
      </Typography>
      <Typography
        variant="numeric"
        sx={{ display: 'block', fontSize: 17, fontWeight: 700, mt: 0.5 }}
      >
        {value}
      </Typography>
    </Paper>
  )
}
