/**
 * The one place money and dates are formatted, so every screen matches.
 *
 * Days are local `YYYY-MM-DD` strings and months `YYYY-MM`, as the backend sends them.
 * `new Date('2026-10-30')` would parse as UTC and show the day before in US time zones,
 * so use parseDay instead.
 */

const LOCALE = 'en-US'

// ---- money (the backend sends decimals as strings) ----

const dollars = new Intl.NumberFormat(LOCALE, { style: 'currency', currency: 'USD' })
const wholeDollars = new Intl.NumberFormat(LOCALE, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

export const money = (value: string | number) => dollars.format(Number(value))
/** Rounded to the dollar, for chart axes and bar labels. */
export const moneyRounded = (value: string | number) => wholeDollars.format(Number(value))

/** Adds in whole cents so floating point never leaks into a total. */
export const sumMoney = (values: (string | number)[]) =>
  values.reduce<number>((cents, v) => cents + Math.round(Number(v) * 100), 0) / 100

// ---- days ----

const pad = (n: number) => String(n).padStart(2, '0')

export const toDay = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

export function parseDay(day: string): Date {
  const [y, m, d] = day.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function addDays(day: string, n: number): string {
  const d = parseDay(day)
  d.setDate(d.getDate() + n)
  return toDay(d)
}

/** Whole days from a to b. Rounded because a daylight saving day is not 24 hours. */
export const daysBetween = (a: string, b: string) =>
  Math.round((parseDay(b).getTime() - parseDay(a).getTime()) / 86_400_000)

const shortDay = new Intl.DateTimeFormat(LOCALE, { month: 'short', day: 'numeric' })
export const formatDay = (day: string) => shortDay.format(parseDay(day))

export function relativeDay(day: string, today: string): string {
  const n = daysBetween(today, day)
  if (n === 0) return 'Today'
  if (n === 1) return 'Tomorrow'
  if (n === -1) return 'Yesterday'
  return n < 0 ? `${-n} days ago` : `In ${n} days`
}

// ---- months ----

export const toMonth = (d: Date) => toDay(d).slice(0, 7)

export function addMonths(month: string, n: number): string {
  const [y, m] = month.split('-').map(Number)
  return toMonth(new Date(y, m - 1 + n, 1))
}

const monthFormats = {
  full: new Intl.DateTimeFormat(LOCALE, { month: 'long', year: 'numeric' }),
  long: new Intl.DateTimeFormat(LOCALE, { month: 'long' }),
  short: new Intl.DateTimeFormat(LOCALE, { month: 'short' }),
  narrow: new Intl.DateTimeFormat(LOCALE, { month: 'narrow' }),
}

export const formatMonth = (month: string, style: keyof typeof monthFormats = 'full') =>
  monthFormats[style].format(parseDay(`${month}-01`))
