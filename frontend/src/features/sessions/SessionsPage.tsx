import { Box, Divider, Paper, Stack, Typography } from '@mui/material'
import { PlaceholderBadge } from '@/components/PlaceholderBadge'
import { costLabel, durationLabel, energyLabel } from '@/features/simulate/display'
import { MOCK_SESSIONS } from './sessions.mock'

function SummaryCell({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ flex: 1, textAlign: 'center' }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography
        variant="numeric"
        sx={{ display: 'block', fontSize: 18, fontWeight: 600, mt: 0.25 }}
      >
        {value}
      </Typography>
    </Box>
  )
}

export function SessionsPage() {
  const totalKwh = MOCK_SESSIONS.reduce((sum, session) => sum + session.energyKwh, 0)
  const totalCost = MOCK_SESSIONS.reduce((sum, session) => sum + session.costEur, 0)

  return (
    <Box sx={{ p: 2, maxWidth: 600, mx: 'auto', pb: 4 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 2 }}>
        <Typography variant="h1">Sesiones</Typography>
        <PlaceholderBadge />
      </Stack>

      <Paper sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
        <SummaryCell label="Sesiones" value={String(MOCK_SESSIONS.length)} />
        <Divider orientation="vertical" flexItem />
        <SummaryCell
          label="kWh"
          value={totalKwh.toLocaleString('es-ES', { maximumFractionDigits: 1 })}
        />
        <Divider orientation="vertical" flexItem />
        <SummaryCell
          label="Gastado"
          value={`${totalCost.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`}
        />
      </Paper>

      <Stack spacing={1} sx={{ mt: 2 }}>
        {MOCK_SESSIONS.map((session) => (
          <Paper key={session.id} sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">
              {session.date}
              {session.private && ' · Privado'}
            </Typography>
            <Typography sx={{ fontWeight: 600, mt: 0.25 }}>{session.station}</Typography>
            <Stack
              direction="row"
              sx={{ justifyContent: 'space-between', alignItems: 'baseline', mt: 1 }}
            >
              <Typography variant="body2" color="text.secondary">
                {durationLabel(session.durationMin)} · {energyLabel(session.energyKwh)}
              </Typography>
              <Typography variant="numeric" sx={{ fontWeight: 600 }}>
                {costLabel(session.costEur)}
              </Typography>
            </Stack>
          </Paper>
        ))}
      </Stack>
    </Box>
  )
}
