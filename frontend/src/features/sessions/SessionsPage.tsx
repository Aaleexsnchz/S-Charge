import { Box, Divider, Paper, Stack, Typography } from '@mui/material'
import { Eyebrow } from '@/components/Eyebrow'
import { PlaceholderBadge } from '@/components/PlaceholderBadge'
import { costLabel, durationLabel, energyLabel } from '@/features/simulate/display'
import { MOCK_SESSIONS, type MockSession } from './sessions.mock'

function SummaryCell({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <Box sx={{ flex: 1, textAlign: 'center' }}>
      <Typography variant="numeric" sx={{ display: 'block', fontSize: 19, fontWeight: 600 }}>
        {value}
        {unit && (
          <Box component="span" sx={{ fontSize: 11, color: 'text.secondary', ml: 0.4 }}>
            {unit}
          </Box>
        )}
      </Typography>
      <Box sx={{ mt: 0.25 }}>
        <Eyebrow>{label}</Eyebrow>
      </Box>
    </Box>
  )
}

/** The bar is the row's own energy against the month's largest session, so the
 *  list can be read by shape before it is read by number. */
function SessionRow({ session, maxKwh }: { session: MockSession; maxKwh: number }) {
  return (
    <Stack direction="row" spacing={2} sx={{ px: 2, py: 2, alignItems: 'flex-start' }}>
      <Box sx={{ width: 44, flexShrink: 0 }}>
        <Typography
          variant="numeric"
          sx={{ display: 'block', fontSize: 12, color: 'text.secondary', lineHeight: 1.4 }}
        >
          {session.date}
        </Typography>
        <Typography
          variant="numeric"
          sx={{ display: 'block', fontSize: 11, color: 'text.disabled', lineHeight: 1.4 }}
        >
          {session.time}
        </Typography>
      </Box>

      <Box sx={{ minWidth: 0, flex: 1 }}>
        <Stack
          direction="row"
          spacing={1}
          sx={{ alignItems: 'baseline', justifyContent: 'space-between' }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: 15, minWidth: 0 }} noWrap>
            {session.station}
          </Typography>
          <Typography variant="numeric" sx={{ fontWeight: 600, flexShrink: 0 }}>
            {costLabel(session.costEur)}
          </Typography>
        </Stack>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
          {durationLabel(session.durationMin)} · {energyLabel(session.energyKwh)}
          {session.private && ' · Privado'}
        </Typography>

        <Box sx={{ mt: 1.25, height: 2, borderRadius: 999, bgcolor: 'divider' }}>
          <Box
            sx={{
              height: '100%',
              width: `${(session.energyKwh / maxKwh) * 100}%`,
              borderRadius: 999,
              bgcolor: 'primary.main',
              opacity: 0.6,
            }}
          />
        </Box>
      </Box>
    </Stack>
  )
}

export function SessionsPage() {
  const totalKwh = MOCK_SESSIONS.reduce((sum, session) => sum + session.energyKwh, 0)
  const totalCost = MOCK_SESSIONS.reduce((sum, session) => sum + session.costEur, 0)
  const maxKwh = Math.max(...MOCK_SESSIONS.map((session) => session.energyKwh), 1)

  return (
    <Box sx={{ p: 2, maxWidth: 600, mx: 'auto', pb: 4 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 2 }}>
        <Typography variant="h1">Sesiones</Typography>
        <PlaceholderBadge />
      </Stack>

      <Paper sx={{ px: 1, py: 2, display: 'flex', alignItems: 'center' }}>
        <SummaryCell label="Sesiones" value={String(MOCK_SESSIONS.length)} />
        <Divider orientation="vertical" flexItem />
        <SummaryCell
          label="Cargados"
          value={totalKwh.toLocaleString('es-ES', { maximumFractionDigits: 1 })}
          unit="kWh"
        />
        <Divider orientation="vertical" flexItem />
        <SummaryCell
          label="Gastado"
          value={totalCost.toLocaleString('es-ES', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
          unit="€"
        />
      </Paper>

      <Box sx={{ mt: 4, mb: 1.5 }}>
        <Eyebrow>Agosto</Eyebrow>
      </Box>
      <Stack spacing={1}>
        {MOCK_SESSIONS.map((session) => (
          <Paper key={session.id}>
            <SessionRow session={session} maxKwh={maxKwh} />
          </Paper>
        ))}
      </Stack>
    </Box>
  )
}
