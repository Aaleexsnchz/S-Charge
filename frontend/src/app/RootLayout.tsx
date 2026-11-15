import EvStationIcon from '@mui/icons-material/EvStation'
import EvStationOutlinedIcon from '@mui/icons-material/EvStationOutlined'
import HistoryIcon from '@mui/icons-material/History'
import HistoryOutlinedIcon from '@mui/icons-material/HistoryOutlined'
import HomeIcon from '@mui/icons-material/Home'
import HomeOutlinedIcon from '@mui/icons-material/HomeOutlined'
import MapIcon from '@mui/icons-material/Map'
import MapOutlinedIcon from '@mui/icons-material/MapOutlined'
import {
  AppBar,
  Avatar,
  BottomNavigation,
  BottomNavigationAction,
  Box,
  IconButton,
  Toolbar,
} from '@mui/material'
import { NavLink, Outlet, useLocation } from 'react-router'
import { Wordmark } from '@/components/Wordmark'
import { useCurrentUser, userInitial } from '@/features/auth/currentUser'

function activeSection(pathname: string) {
  if (pathname.startsWith('/map') || pathname.startsWith('/points')) return 'map'
  if (pathname.startsWith('/sessions')) return 'sessions'
  if (pathname.startsWith('/my-points')) return 'my-points'
  if (pathname === '/') return 'home'
  return false as const
}

export function RootLayout() {
  const section = activeSection(useLocation().pathname)
  const user = useCurrentUser()

  return (
    <Box sx={{ height: '100dvh', display: 'flex', flexDirection: 'column' }}>
      <AppBar position="static">
        <Toolbar sx={{ minHeight: 56, px: 2, justifyContent: 'space-between' }}>
          <Wordmark size={18} />
          <IconButton component={NavLink} to="/profile" sx={{ p: 0 }} aria-label="Perfil">
            <Avatar
              sx={{
                width: 36,
                height: 36,
                fontSize: 15,
                fontWeight: 600,
                bgcolor: 'primary.main',
                color: 'primary.contrastText',
              }}
            >
              {user ? userInitial(user) : null}
            </Avatar>
          </IconButton>
        </Toolbar>
      </AppBar>

      <Box component="main" sx={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        <Outlet />
      </Box>

      <BottomNavigation
        value={section}
        showLabels
        sx={{ flexShrink: 0, height: 64, pb: 'env(safe-area-inset-bottom)' }}
      >
        <BottomNavigationAction
          component={NavLink}
          to="/"
          value="home"
          label="Inicio"
          icon={section === 'home' ? <HomeIcon /> : <HomeOutlinedIcon />}
        />
        <BottomNavigationAction
          component={NavLink}
          to="/map"
          value="map"
          label="Mapa"
          icon={section === 'map' ? <MapIcon /> : <MapOutlinedIcon />}
        />
        <BottomNavigationAction
          component={NavLink}
          to="/sessions"
          value="sessions"
          label="Sesiones"
          icon={section === 'sessions' ? <HistoryIcon /> : <HistoryOutlinedIcon />}
        />
        <BottomNavigationAction
          component={NavLink}
          to="/my-points"
          value="my-points"
          label="Mis puntos"
          icon={section === 'my-points' ? <EvStationIcon /> : <EvStationOutlinedIcon />}
        />
      </BottomNavigation>
    </Box>
  )
}
