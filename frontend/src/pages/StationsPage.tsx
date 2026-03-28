import { Link } from 'react-router'

export function StationsPage() {
  return (
    <main className="page">
      <h2>Stations</h2>
      <p>Later, this page will list charging stations from your backend.</p>

      <ul>
        <li>
          <Link to="/stations/demo-station-id">Example station detail route</Link>
        </li>
      </ul>
    </main>
  )
}
