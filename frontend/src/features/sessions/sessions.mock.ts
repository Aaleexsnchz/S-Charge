// Placeholder data — dev-time scaffolding to preview the Sessions tab.
// Remove when the charging-session backend lands. See docs/features.md.

export type MockSession = {
  id: string
  date: string
  station: string
  durationMin: number
  energyKwh: number
  costEur: number
  private?: boolean
}

export const MOCK_SESSIONS: MockSession[] = [
  {
    id: '1',
    date: '21 abr · 08:15',
    station: 'REVE Sagrada Família',
    durationMin: 42,
    energyKwh: 18.2,
    costEur: 7.1,
  },
  {
    id: '2',
    date: '18 abr · 19:30',
    station: 'REVE Plaça Catalunya',
    durationMin: 84,
    energyKwh: 28.4,
    costEur: 11.92,
  },
  {
    id: '3',
    date: '15 abr · 07:50',
    station: 'Garaje Sants',
    durationMin: 130,
    energyKwh: 22.6,
    costEur: 7.23,
    private: true,
  },
  {
    id: '4',
    date: '12 abr · 14:05',
    station: 'REVE Diagonal Mar',
    durationMin: 36,
    energyKwh: 24.1,
    costEur: 10.12,
  },
  {
    id: '5',
    date: '09 abr · 22:18',
    station: 'Parking Clot',
    durationMin: 400,
    energyKwh: 31.2,
    costEur: 9.98,
    private: true,
  },
]
