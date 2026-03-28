import { Link, Outlet } from 'react-router'
import '../styles/layout.css'

export function RootLayout() {
  return (
    <div className="layout">
      <header className="topbar">
        <h1>EV Charging App</h1>
        <nav className="nav">
          <Link to="/">Home</Link>
          <Link to="/stations">Stations</Link>
          <Link to="/map">Map</Link>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}
