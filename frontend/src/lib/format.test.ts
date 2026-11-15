import { describe, expect, it } from 'vitest'
import { formatDecimal, formatEur } from './format'

describe('formatEur', () => {
  it('always shows two decimals with a comma', () => {
    expect(formatEur(12)).toBe('12,00')
    expect(formatEur(3.6)).toBe('3,60')
    expect(formatEur(0.4)).toBe('0,40')
  })

  it('rounds to the cent', () => {
    expect(formatEur(0.3456)).toBe('0,35')
  })

  it('groups thousands from five digits up', () => {
    expect(formatEur(1234.5)).toBe('1234,50')
    expect(formatEur(12345.6)).toBe('12.345,60')
  })
})

describe('formatDecimal', () => {
  it('caps the decimals and drops trailing zeros', () => {
    expect(formatDecimal(201.06, 1)).toBe('201,1')
    expect(formatDecimal(22, 1)).toBe('22')
    expect(formatDecimal(1.25, 0)).toBe('1')
  })
})
