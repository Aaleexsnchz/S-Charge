import { createBrowserRouter } from 'react-router'
import { RootLayout } from './layouts/RootLayout'
import { HomePage } from './pages/HomePage'
import { MapPage } from './pages/MapPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { StationDetailPage } from './pages/StationDetailPage'
import { StationsPage } from './pages/StationsPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'stations',
        element: <StationsPage />,
      },
      {
        path: 'stations/:stationId',
        element: <StationDetailPage />,
      },
      {
        path: 'map',
        element: <MapPage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
])
