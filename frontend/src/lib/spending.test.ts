import { describe, expect, it } from 'vitest'
import { axisTicks, monthsEnding, percentChange, toMonthSpend } from './spending'

const month = (m: string) => toMonthSpend({ month: m, confirmed: '215.00', manual: '30.00' })

describe('spending', () => {
  it('adds manual entries to the month total', () => {
    expect(month('2026-10')).toEqual({ month: '2026-10', confirmed: 215, manual: 30, total: 245 })
  })

  it('picks the months of the chart period', () => {
    const all = ['2026-07', '2026-08', '2026-09', '2026-10'].map(month)
    const names = (end: string, n: number) => monthsEnding(all, end, n).map((m) => m.month)
    expect(names('2026-10', 3)).toEqual(['2026-08', '2026-09', '2026-10'])
    expect(names('2026-09', 2)).toEqual(['2026-08', '2026-09'])
    expect(names('2026-08', 12)).toEqual(['2026-07', '2026-08'])
  })

  it('compares months, and skips the comparison without a base', () => {
    expect(percentChange(245, 255)!.toFixed(1)).toBe('-3.9')
    expect(percentChange(245, 0)).toBeNull()
    expect(percentChange(245, undefined)).toBeNull()
  })

  it.each([
    [255, [0, 100, 200, 300]],
    [300, [0, 100, 200, 300]],
    [301, [0, 200, 400]],
    [12, [0, 5, 10, 15]],
    [0.5, [0, 0.2, 0.4, 0.6]],
    [4200, [0, 2000, 4000, 6000]],
    [0, [0]],
  ])('scales the axis for a maximum of %s', (max, ticks) => {
    axisTicks(max).forEach((t, i) => expect(t).toBeCloseTo(ticks[i]))
    expect(axisTicks(max)).toHaveLength(ticks.length)
  })
})
