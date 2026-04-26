import { Outlet, createBrowserRouter } from 'react-router'
import {
  forgotPasswordAction,
  loginAction,
  logoutAction,
  registerAction,
  resetPasswordAction,
} from './auth/actions'
import { rootLoader } from './auth/loaders'
import { ProtectedRoute } from './components/ProtectedRoute'
import { RootHydrateFallback } from './components/RootHydrateFallback'
import { AuthLayout } from './layouts/AuthLayout'
import { RootLayout } from './layouts/RootLayout'
import { CheckEmailPage } from './pages/CheckEmailPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { ProfilePage } from './pages/ProfilePage'
import { RegisterPage } from './pages/RegisterPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'

export const router = createBrowserRouter([
  {
    id: 'root',
    loader: rootLoader,
    HydrateFallback: RootHydrateFallback,
    element: <Outlet />,
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
          { path: 'profile', element: <ProfilePage /> },
          { path: 'logout', action: logoutAction },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
