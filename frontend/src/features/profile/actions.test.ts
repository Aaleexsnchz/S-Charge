import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/lib/api/client'
import { MAX_NAME_LENGTH, updateNameAction } from './actions'

vi.mock('@/lib/api/client', () => ({
  apiClient: { PATCH: vi.fn() },
}))

const patch = vi.mocked(apiClient.PATCH)

function requestWith(name: string): Request {
  const body = new FormData()
  body.set('name', name)
  return new Request('https://test/profile', { method: 'POST', body })
}

function run(name: string) {
  return updateNameAction({
    request: requestWith(name),
    params: {},
    context: {},
  } as unknown as Parameters<typeof updateNameAction>[0])
}

describe('updateNameAction', () => {
  beforeEach(() => {
    patch.mockReset()
  })

  it.each(['', '   '])('rejects a blank name without calling the API: %p', async (name) => {
    expect(await run(name)).toEqual({ error: 'Escribe tu nombre' })
    expect(patch).not.toHaveBeenCalled()
  })

  it('rejects a name over the backend limit without calling the API', async () => {
    const result = await run('a'.repeat(MAX_NAME_LENGTH + 1))
    expect(result).toEqual({
      error: `El nombre no puede superar los ${MAX_NAME_LENGTH} caracteres`,
    })
    expect(patch).not.toHaveBeenCalled()
  })

  it('sends the trimmed name and reports success', async () => {
    patch.mockResolvedValue({
      data: { id: 'u1', email: 'alejandro@example.com', name: 'Alejandro' },
      response: new Response(null, { status: 200 }),
    })

    expect(await run('  Alejandro  ')).toEqual({ success: true })
    expect(patch).toHaveBeenCalledWith('/api/users/me', { body: { name: 'Alejandro' } })
  })

  it('surfaces a server failure in Spanish', async () => {
    patch.mockResolvedValue({
      error: { detail: 'boom' },
      response: new Response(null, { status: 500 }),
    })

    expect(await run('Alejandro')).toEqual({ error: 'Error del servidor, inténtalo de nuevo' })
  })
})
