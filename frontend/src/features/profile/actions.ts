import type { ActionFunctionArgs } from 'react-router'
import { apiClient } from '@/lib/api/client'

export const MAX_NAME_LENGTH = 100

export type NameActionData = { success: true } | { error: string }

const EMPTY_NAME = 'Escribe tu nombre'
const NAME_TOO_LONG = `El nombre no puede superar los ${MAX_NAME_LENGTH} caracteres`
const GENERIC_ERROR = 'Error del servidor, inténtalo de nuevo'

export async function updateNameAction({ request }: ActionFunctionArgs): Promise<NameActionData> {
  const formData = await request.formData()
  const name = String(formData.get('name') ?? '').trim()
  if (name === '') return { error: EMPTY_NAME }
  if (name.length > MAX_NAME_LENGTH) return { error: NAME_TOO_LONG }

  const { response } = await apiClient.PATCH('/api/users/me', { body: { name } })
  if (response.ok) return { success: true }
  return { error: GENERIC_ERROR }
}
