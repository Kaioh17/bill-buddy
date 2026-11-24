import { describe, expect, it } from 'vitest'
import { addDays, addMonths, daysBetween, formatDay, formatMonth, money, moneyRounded, relativeDay, sumMoney, toDay } from './format'

describe('money', () => {
  it('formats decimal strings from the backend', () => {
    expect(money('245')).toBe('$245.00')
    expect(money('0')).toBe('$0.00')
    expect(money('1234.5')).toBe('$1,234.50')
    expect(moneyRounded('244.60')).toBe('$245')
  })

  it('adds without floating point drift', () => {
    expect(sumMoney(['0.10', '0.20'])).toBe(0.3)
    expect(sumMoney([])).toBe(0)
  })
})

describe('days', () => {
  it('stays on the same local day', () => {
    expect(formatDay('2026-10-30')).toBe('Oct 30')
    expect(toDay(new Date(2026, 9, 30, 23, 59))).toBe('2026-10-30')
  })

  it('crosses month and year ends', () => {
    expect(addDays('2026-10-30', 3)).toBe('2026-11-02')
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01')
    expect(addDays('2028-02-28', 1)).toBe('2028-02-29')
  })

  it('counts whole days across a daylight saving change', () => {
    expect(daysBetween('2026-10-30', '2026-11-05')).toBe(6)
    expect(daysBetween('2026-03-07', '2026-03-09')).toBe(2)
  })

  it.each([
    ['2026-10-30', 'Today'],
    ['2026-10-31', 'Tomorrow'],
    ['2026-11-02', 'In 3 days'],
    ['2026-10-29', 'Yesterday'],
    ['2026-10-28', '2 days ago'],
  ])('describes %s as %s', (day, text) => {
    expect(relativeDay(day, '2026-10-30')).toBe(text)
  })
})

describe('months', () => {
  it('rolls over the year in both directions', () => {
    expect(addMonths('2026-12', 1)).toBe('2027-01')
    expect(addMonths('2026-01', -1)).toBe('2025-12')
    expect(addMonths('2026-10', -11)).toBe('2025-11')
  })

  it('names months', () => {
    expect(formatMonth('2026-10')).toBe('October 2026')
    expect(formatMonth('2026-10', 'short')).toBe('Oct')
  })
})
