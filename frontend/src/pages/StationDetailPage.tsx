import { useParams } from 'react-router'

export function StationDetailPage() {
  const { stationId } = useParams()

  return (
    <main className="page">
      <h2>Station Detail</h2>
      <p>Route param: {stationId}</p>
    </main>
  )
}
