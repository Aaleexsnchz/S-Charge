import { Box, Chip, Paper, Stack, Typography } from '@mui/material'
import type { components } from '@/lib/api/schema'
import { pricePerKwhLabel } from './display'

function hourLabel(isoTime: string): string {
  return isoTime.slice(0, 5)
}

type ConnectorSchedule = components['schemas']['ConnectorScheduleRead']

type Props = {
  schedules: ConnectorSchedule[]
  connectorLabels: Map<string, string>
}

export function PriceScheduleCard({ schedules, connectorLabels }: Props) {
  if (schedules.length === 0) return null

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        Precio por franjas
      </Typography>
      <Stack spacing={2}>
        {schedules.map((schedule) => {
          const labels = schedule.connector_ids
            .map((id) => connectorLabels.get(id))
            .filter((label): label is string => label !== undefined)
          return (
            <Box key={schedule.connector_ids.join('-')}>
              {schedules.length > 1 && labels.length > 0 && (
                <Typography variant="caption" color="text.secondary">
                  {labels.join(' · ')}
                </Typography>
              )}
              <Stack spacing={0.25} sx={{ mt: 0.5 }}>
                {schedule.bands.map((band) => (
                  <Stack
                    key={band.start_time}
                    direction="row"
                    spacing={1}
                    sx={{
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      px: 1,
                      py: 0.5,
                      borderRadius: 1,
                      bgcolor: band.is_current ? 'action.selected' : undefined,
                    }}
                  >
                    <Typography variant="body2" sx={{ fontWeight: band.is_current ? 600 : 400 }}>
                      {hourLabel(band.start_time)}–{hourLabel(band.end_time)}
                    </Typography>
                    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                      {band.is_current && <Chip size="small" label="Ahora" color="primary" />}
                      <Typography
                        variant="numeric"
                        sx={{ fontSize: 13, fontWeight: band.is_current ? 600 : 400 }}
                      >
                        {pricePerKwhLabel(band.price_per_kwh)}
                      </Typography>
                    </Stack>
                  </Stack>
                ))}
              </Stack>
            </Box>
          )
        })}
      </Stack>
    </Paper>
  )
}
