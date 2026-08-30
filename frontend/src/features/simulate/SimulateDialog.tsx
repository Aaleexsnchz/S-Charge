import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import {
  Alert,
  Box,
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
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useState } from 'react'
import { Eyebrow } from '@/components/Eyebrow'
import { durationLabel } from './display'
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

/** The charge the driver asked for, drawn on the battery it applies to. */
function SocRange({ from, to, valid }: { from: number; to: number; valid: boolean }) {
  const lo = Math.min(Math.max(from, 0), 100)
  const hi = Math.min(Math.max(to, 0), 100)
  return (
    <Box sx={{ position: 'relative', height: 4, borderRadius: 999, bgcolor: 'divider' }}>
      {valid && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: `${lo}%`,
            width: `${hi - lo}%`,
            borderRadius: 999,
            bgcolor: 'primary.main',
            boxShadow: '0 0 8px rgba(127,231,196,0.5)',
          }}
        />
      )}
    </Box>
  )
}

/** Value and unit are one unbreakable pair: a "kWh" that wraps to its own line
 *  reads as a different number. */
function Figure({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Eyebrow>{label}</Eyebrow>
      <Typography
        variant="numeric"
        sx={{ display: 'block', fontSize: 15, fontWeight: 600, mt: 0.25, whiteSpace: 'nowrap' }}
      >
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
      <DialogTitle sx={{ pb: 1.5 }}>Simular carga</DialogTitle>
      {/* `dividers` is load-bearing, not decoration. Without it MUI applies
          `.MuiDialogTitle-root + & { padding-top: 0 }`, and since the content is
          an `overflow-y: auto` scrollport it clips at its padding box — slicing
          the first field's label, which floats above its own input. An `sx`
          padding cannot win that rule: one class loses to a sibling selector. */}
      <DialogContent dividers>
        <Stack spacing={2}>
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

          <Box>
            <Box sx={{ mb: 1 }}>
              <Eyebrow>Carga</Eyebrow>
            </Box>
            <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
              <TextField
                label="Desde"
                type="number"
                size="small"
                value={socFrom}
                onChange={(e) => {
                  setSocFrom(e.target.value)
                  simulate.reset()
                }}
                slotProps={{ htmlInput: { min: 0, max: 99 } }}
                sx={{ flex: 1 }}
              />
              <ArrowForwardIcon sx={{ color: 'text.disabled', fontSize: 18, flexShrink: 0 }} />
              <TextField
                label="Hasta"
                type="number"
                size="small"
                value={socTo}
                onChange={(e) => {
                  setSocTo(e.target.value)
                  simulate.reset()
                }}
                slotProps={{ htmlInput: { min: 1, max: 100 } }}
                sx={{ flex: 1 }}
              />
            </Stack>
            <Box sx={{ mt: 1.5 }}>
              <SocRange from={from} to={to} valid={socValid} />
            </Box>
          </Box>

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
            <Box>
              <Divider sx={{ mb: 2 }} />
              <Eyebrow>Coste estimado</Eyebrow>
              {result.cost_eur !== null ? (
                <Stack direction="row" spacing={0.75} sx={{ alignItems: 'baseline', mt: 0.5 }}>
                  <Typography
                    variant="numeric"
                    sx={{ fontSize: 38, fontWeight: 700, lineHeight: 1, color: 'primary.main' }}
                  >
                    {result.cost_eur.toLocaleString('es-ES', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </Typography>
                  <Typography variant="numeric" sx={{ fontSize: 15, color: 'text.secondary' }}>
                    €
                  </Typography>
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  El operador no publica precio, así que no se puede calcular.
                </Typography>
              )}

              <Stack
                direction="row"
                spacing={1}
                sx={{
                  mt: 2,
                  pt: 2,
                  borderTop: 1,
                  borderColor: 'divider',
                  justifyContent: 'space-between',
                }}
              >
                <Figure label="Duración" value={durationLabel(result.duration_minutes)} />
                <Figure
                  label="Energía"
                  value={result.energy_kwh.toLocaleString('es-ES', { maximumFractionDigits: 1 })}
                  unit="kWh"
                />
                <Figure
                  label="Potencia"
                  value={result.average_power_kw.toLocaleString('es-ES', {
                    maximumFractionDigits: 1,
                  })}
                  unit="kW"
                />
              </Stack>

              {result.price_per_kwh !== null && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ mt: 1.5, display: 'block' }}
                >
                  Precio medio de la carga:{' '}
                  <Box component="span" sx={{ whiteSpace: 'nowrap' }}>
                    {result.price_per_kwh.toLocaleString('es-ES', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}{' '}
                    €/kWh
                  </Box>
                </Typography>
              )}
            </Box>
          )}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5, pt: 1 }}>
        <Button onClick={handleClose} color="inherit">
          Cerrar
        </Button>
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
