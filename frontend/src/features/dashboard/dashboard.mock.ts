// Placeholder data — dev-time scaffolding to preview the dashboard's appearance.
// Remove when sessions/reservation/stats backends land. See docs/features.md.

export type DashboardStat = { label: string; value: string; unit?: string }

export const MOCK_STATS: DashboardStat[] = [
  { label: 'Sesiones este mes', value: '14' },
  { label: 'kWh cargados', value: '312.6' },
  { label: 'Gastado', value: '118.40', unit: '€' },
  { label: 'CO₂ evitado', value: '142', unit: 'kg' },
]

export type MockReservation = {
  station: string
  when: string
  connector: string
  startsIn: string
}

export const MOCK_NEXT_RESERVATION: MockReservation | null = {
  station: 'REVE Sagrada Família',
  when: 'Hoy · 18:30 – 19:30',
  connector: 'CCS 150 kW',
  startsIn: '08h 47m',
}
