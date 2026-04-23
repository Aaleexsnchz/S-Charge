import { redirect, type ActionFunctionArgs } from 'react-router'
import { apiClient } from '../api/client'

export type AuthActionError = { error: string }

const AUTH_ERROR_COPY: Record<string, string> = {
  LOGIN_BAD_CREDENTIALS: 'Email o contraseña inválidos',
  REGISTER_USER_ALREADY_EXISTS: 'Este email ya está registrado',
  REGISTER_INVALID_PASSWORD: 'La contraseña debe tener al menos 12 caracteres',
}

const FIELD_ERROR_COPY: Record<string, string> = {
  email: 'La dirección de correo introducida no es válida',
}

const GENERIC_ERROR = 'Error del servidor, inténtalo de nuevo'

export function errorCodeFromDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const code = (detail as Record<string, unknown>).code
    return typeof code === 'string' ? code : null
  }
  return null
}

export function fieldErrorFromValidationArray(
  detail: unknown,
): string | null {
  if (!Array.isArray(detail)) return null
  for (const item of detail) {
    if (!item || typeof item !== 'object') continue
    const loc = (item as Record<string, unknown>).loc
    if (!Array.isArray(loc) || loc.length === 0) continue
    const field = loc[loc.length - 1]
    if (typeof field !== 'string') continue
    const msg = FIELD_ERROR_COPY[field]
    if (msg) return msg
  }
  return null
}

export function messageFor(detail: unknown): string {
  const fieldMessage = fieldErrorFromValidationArray(detail)
  if (fieldMessage) return fieldMessage

  const code = errorCodeFromDetail(detail)
  if (code) {
    const msg = AUTH_ERROR_COPY[code]
    if (msg) return msg
  }
  return GENERIC_ERROR
}

function submitLogin(username: string, password: string) {
  return apiClient.POST('/api/auth/login', {
    body: {
      username,
      password,
      grant_type: 'password',
      scope: '',
    },
    bodySerializer: (body) =>
      new URLSearchParams(body as Record<string, string>),
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  })
}

export async function loginAction({
  request,
}: ActionFunctionArgs): Promise<AuthActionError | Response> {
  const formData = await request.formData()
  const username = String(formData.get('email') ?? '')
  const password = String(formData.get('password') ?? '')

  const { error, response } = await submitLogin(username, password)
  if (response.ok) return redirect('/profile')

  if ((response.status === 400 || response.status === 422) && error) {
    return { error: messageFor(error.detail) }
  }
  return { error: GENERIC_ERROR }
}

export async function registerAction({
  request,
}: ActionFunctionArgs): Promise<AuthActionError | Response> {
  const formData = await request.formData()
  const email = String(formData.get('email') ?? '')
  const password = String(formData.get('password') ?? '')
  const nameValue = formData.get('name')
  const name = typeof nameValue === 'string' && nameValue ? nameValue : null

  const { error, response } = await apiClient.POST('/api/auth/register', {
    body: { email, password, name },
  })

  if (response.ok) {
    const loginResult = await submitLogin(email, password)
    return redirect(loginResult.response.ok ? '/profile' : '/login')
  }

  if ((response.status === 400 || response.status === 422) && error) {
    return { error: messageFor(error.detail) }
  }
  return { error: GENERIC_ERROR }
}

export async function logoutAction(): Promise<Response> {
  await apiClient.POST('/api/auth/logout')
  return redirect('/login')
}
