import { NavLink, Outlet } from 'react-router'
import '../styles/layout.css'

export function RootLayout() {
  return (
    <div className="layout">
      <header className="topbar">
        <h1>EV Charging</h1>
        <nav className="nav">
          <NavLink to="/" end>
            Inicio
          </NavLink>
          <NavLink to="/map">Mapa</NavLink>
          <NavLink to="/profile">Perfil</NavLink>
        </nav>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
