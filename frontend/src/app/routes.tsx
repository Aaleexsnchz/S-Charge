import { createBrowserRouter, Outlet } from 'react-router'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { RootHydrateFallback } from '@/components/RootHydrateFallback'
import { AuthLayout } from '@/features/auth/AuthLayout'
import {
  forgotPasswordAction,
  loginAction,
  logoutAction,
  registerAction,
  resetPasswordAction,
} from '@/features/auth/actions'
import { CheckEmailPage } from '@/features/auth/CheckEmailPage'
import { ForgotPasswordPage } from '@/features/auth/ForgotPasswordPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { rootLoader } from '@/features/auth/loaders'
import { RegisterPage } from '@/features/auth/RegisterPage'
import { ResetPasswordPage } from '@/features/auth/ResetPasswordPage'
import { VerifyEmailPage } from '@/features/auth/VerifyEmailPage'
import { HomePage } from '@/features/home/HomePage'
import { ProfilePage } from '@/features/profile/ProfilePage'
import { NotFoundPage } from './NotFoundPage'
import { RootLayout } from './RootLayout'
import { RouteErrorPage } from './RouteErrorPage'

export const router = createBrowserRouter([
  {
    id: 'root',
    loader: rootLoader,
    HydrateFallback: RootHydrateFallback,
    element: <Outlet />,
    errorElement: <RouteErrorPage />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          { path: 'login', element: <LoginPage />, action: loginAction },
          {
            path: 'register',
            element: <RegisterPage />,
            action: registerAction,
          },
          { path: 'check-email', element: <CheckEmailPage /> },
          { path: 'verify-email', element: <VerifyEmailPage /> },
          {
            path: 'forgot-password',
            element: <ForgotPasswordPage />,
            action: forgotPasswordAction,
          },
          {
            path: 'reset-password',
            element: <ResetPasswordPage />,
            action: resetPasswordAction,
          },
        ],
      },
      {
        element: (
          <ProtectedRoute>
            <RootLayout />
          </ProtectedRoute>
        ),
        children: [
          { index: true, element: <HomePage /> },
          {
            path: 'map',
            lazy: async () => ({
              Component: (await import('@/features/map/MapPage')).MapPage,
            }),
          },
          {
            path: 'points/:pointId',
            lazy: async () => ({
              Component: (await import('@/features/points/PointDetailPage')).PointDetailPage,
            }),
          },
          { path: 'profile', element: <ProfilePage /> },
          { path: 'logout', action: logoutAction },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
