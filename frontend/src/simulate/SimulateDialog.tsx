import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
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
import { costLabel, durationLabel, energyLabel, PRICE_SOURCE_LABELS } from './display'
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
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Stack spacing={1} divider={<Divider flexItem />}>
                <ResultRow label="Energía" value={energyLabel(result.energy_kwh)} />
                <ResultRow label="Duración" value={durationLabel(result.duration_minutes)} />
                <ResultRow
                  label="Potencia media"
                  value={`${result.average_power_kw.toLocaleString('es-ES', { maximumFractionDigits: 1 })} kW`}
                />
                <ResultRow label="Coste" value={costLabel(result.cost_eur)} />
              </Stack>
              {result.price_source && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ mt: 1, display: 'block' }}
                >
                  Precio:{' '}
                  {result.price_per_kwh?.toLocaleString('es-ES', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}{' '}
                  €/kWh · {PRICE_SOURCE_LABELS[result.price_source]}
                </Typography>
              )}
            </Paper>
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

function ResultRow({ label, value }: { label: string; value: string }) {
  return (
    <Stack direction="row" sx={{ justifyContent: 'space-between' }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {value}
      </Typography>
    </Stack>
  )
}
