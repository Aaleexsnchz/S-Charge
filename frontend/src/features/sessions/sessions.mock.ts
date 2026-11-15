// Placeholder data — dev-time scaffolding to preview the Sessions tab.
// Remove when the charging-session backend lands. See docs/features/sessions.md.

export type MockSession = {
  id: string
  date: string
  time: string
  station: string
  durationMin: number
  energyKwh: number
  costEur: number
  private?: boolean
}

export const MOCK_SESSIONS: MockSession[] = [
  {
    id: '1',
    date: '27 ago',
    time: '18:42',
    station: 'Bluespace - Leganés',
    durationMin: 28,
    energyKwh: 32.4,
    costEur: 12.05,
  },
  {
    id: '2',
    date: '25 ago',
    time: '07:30',
    station: 'Wallbox casa',
    durationMin: 205,
    energyKwh: 24.8,
    costEur: 3.6,
    private: true,
  },
  {
    id: '3',
    date: '22 ago',
    time: '20:10',
    station: 'M-Leganes-011',
    durationMin: 105,
    energyKwh: 18.6,
    costEur: 7.2,
  },
  {
    id: '4',
    date: '19 ago',
    time: '09:05',
    station: 'LEGANES II',
    durationMin: 38,
    energyKwh: 27.3,
    costEur: 8.12,
  },
  {
    id: '5',
    date: '16 ago',
    time: '22:35',
    station: 'Wallbox casa',
    durationMin: 260,
    energyKwh: 31.5,
    costEur: 4.57,
    private: true,
  },
  {
    id: '6',
    date: '12 ago',
    time: '13:20',
    station: 'Saltoki Leganés',
    durationMin: 70,
    energyKwh: 12.4,
    costEur: 3.07,
  },
  {
    id: '7',
    date: '08 ago',
    time: '17:55',
    station: 'Petroprix Leganés II',
    durationMin: 24,
    energyKwh: 38.2,
    costEur: 19.07,
  },
  {
    id: '8',
    date: '04 ago',
    time: '08:40',
    station: 'M-Leganes-009',
    durationMin: 92,
    energyKwh: 15.9,
    costEur: 6.15,
  },
]
