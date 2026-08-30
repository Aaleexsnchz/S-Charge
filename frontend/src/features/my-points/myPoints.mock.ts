// Placeholder data — dev-time scaffolding to preview the My-points tab.
// `ChargingPoint.owner_user_id` already exists in the backend, so a thin
// `GET /api/points/mine` would make this real. See docs/features.md.

import type { AggregateStatus } from '@/features/map/types'

export type MockOwnedPoint = {
  id: string
  name: string
  address: string
  public: boolean
  status: AggregateStatus
  bookingsThisMonth: number
  earningsEur: number
}

export const MOCK_OWNED_POINTS: MockOwnedPoint[] = [
  {
    id: '1',
    name: 'Wallbox casa',
    address: 'C/ Rioja 8, Zarzaquemada, Leganés',
    public: false,
    status: 'occupied',
    bookingsThisMonth: 7,
    earningsEur: 26.6,
  },
  {
    id: '2',
    name: 'Garaje Butarque · Plaza 12',
    address: 'C/ Butarque 30, Leganés',
    public: false,
    status: 'available',
    bookingsThisMonth: 11,
    earningsEur: 78.4,
  },
  {
    id: '3',
    name: 'Plaza Campus · Nivel -2',
    address: 'Av. de la Universidad 20, Leganés',
    public: false,
    status: 'available',
    bookingsThisMonth: 4,
    earningsEur: 29.6,
  },
]
