// Placeholder data — dev-time scaffolding to preview the dashboard's appearance.
// Remove when sessions/reservation/stats backends land. See docs/features.md.
// The month's totals mirror MOCK_SESSIONS; keep both in step.

export const MOCK_MONTH_SPEND = { value: '63,83', unit: '€' }

export type DashboardStat = { label: string; value: string; unit?: string }

export const MOCK_STATS: DashboardStat[] = [
  { label: 'Sesiones', value: '8' },
  { label: 'Cargados', value: '201,1', unit: 'kWh' },
  { label: 'CO₂ evitado', value: '108', unit: 'kg' },
]

export type MockReservation = {
  station: string
  when: string
  connector: string
  startsIn: string
}

export const MOCK_NEXT_RESERVATION: MockReservation | null = {
  station: 'Bluespace - Leganés',
  when: 'Hoy · 18:30 – 19:15',
  connector: 'CCS 120 kW',
  startsIn: '02h 15m',
}
