const LOCALE = 'es-ES'

const EUR = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const decimalFormats = new Map<number, Intl.NumberFormat>()

/** A euro amount with two decimals and no symbol, so callers can style the unit apart. */
export function formatEur(value: number): string {
  return EUR.format(value)
}

/** A quantity with at most `digits` decimals; trailing zeros are dropped. */
export function formatDecimal(value: number, digits: number): string {
  let format = decimalFormats.get(digits)
  if (!format) {
    format = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: digits })
    decimalFormats.set(digits, format)
  }
  return format.format(value)
}
