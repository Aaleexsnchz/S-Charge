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
    name: 'Plaza del Sol · Plaza 12',
    address: 'C/ Verdi 4, Gràcia, Barcelona',
    public: true,
    status: 'available',
    bookingsThisMonth: 14,
    earningsEur: 126.4,
  },
  {
    id: '2',
    name: 'Garaje Sants',
    address: 'C/ Rosselló 205, Sants, Barcelona',
    public: false,
    status: 'occupied',
    bookingsThisMonth: 8,
    earningsEur: 72.1,
  },
  {
    id: '3',
    name: 'Parking Clot',
    address: 'Av. Meridiana 110, Sant Martí, Barcelona',
    public: true,
    status: 'unknown',
    bookingsThisMonth: 0,
    earningsEur: 0,
  },
]
