import { describe, expect, it } from 'vitest'
import { errorCodeFromDetail, messageFor } from './actions'

const GENERIC = 'Error del servidor, inténtalo de nuevo'

describe('errorCodeFromDetail', () => {
  it('returns a string detail as-is', () => {
    expect(errorCodeFromDetail('LOGIN_BAD_CREDENTIALS')).toBe(
      'LOGIN_BAD_CREDENTIALS',
    )
  })

  it('reads a string `code` from an object detail', () => {
    expect(errorCodeFromDetail({ code: 'REGISTER_INVALID_PASSWORD' })).toBe(
      'REGISTER_INVALID_PASSWORD',
    )
  })

  it('ignores non-string `code` values on an object detail', () => {
    expect(errorCodeFromDetail({ code: 42 })).toBeNull()
  })

  it('returns null for an object without `code`', () => {
    expect(errorCodeFromDetail({ reason: 'missing code' })).toBeNull()
  })

  it.each([null, undefined, 42, [], [{ code: 'X' }]])(
    'returns null for non-object/non-string input: %p',
    (input) => {
      expect(errorCodeFromDetail(input)).toBeNull()
    },
  )
})

describe('messageFor', () => {
  it.each([
    ['LOGIN_BAD_CREDENTIALS', 'Email o contraseña inválidos'],
    ['REGISTER_USER_ALREADY_EXISTS', 'Este email ya está registrado'],
    [
      'REGISTER_INVALID_PASSWORD',
      'La contraseña debe tener al menos 12 caracteres',
    ],
  ])('maps known string code %p to Spanish copy', (code, expected) => {
    expect(messageFor(code)).toBe(expected)
  })

  it('maps an object detail with a known `code` to Spanish copy', () => {
    expect(
      messageFor({ code: 'REGISTER_INVALID_PASSWORD', reason: 'too short' }),
    ).toBe('La contraseña debe tener al menos 12 caracteres')
  })

  it('falls back to the generic message for an unknown string code', () => {
    expect(messageFor('SOMETHING_WEIRD')).toBe(GENERIC)
  })

  it('falls back to the generic message for an object without `code`', () => {
    expect(messageFor({ reason: 'x' })).toBe(GENERIC)
  })

  it.each([null, undefined, 42, []])(
    'falls back to the generic message for non-object/non-string input: %p',
    (input) => {
      expect(messageFor(input)).toBe(GENERIC)
    },
  )
})
