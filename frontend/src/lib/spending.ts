/** Dashboard arithmetic, kept out of the components so it can be tested. */
import type { Dashboard } from './api'
import { addMonths, sumMoney } from './format'

export type MonthSpend = { month: string; confirmed: number; manual: number; total: number }

export const toMonthSpend = (m: Dashboard['months'][number]): MonthSpend => ({
  month: m.month,
  confirmed: Number(m.confirmed),
  manual: Number(m.manual),
  total: sumMoney([m.confirmed, m.manual]),
})

/** The `count` months ending with `end`, or fewer when there is less history. */
export function monthsEnding(months: MonthSpend[], end: string, count: number): MonthSpend[] {
  const start = addMonths(end, 1 - count)
  return months.filter((m) => m.month >= start && m.month <= end)
}

/** Percent change, or null when there is nothing to compare with. */
export const percentChange = (now: number, before: number | undefined) =>
  before ? ((now - before) / before) * 100 : null

/** Axis ticks from 0 up to a round number at or above `max`, in two or three steps. */
export function axisTicks(max: number): number[] {
  if (max <= 0) return [0]
  const rough = max / 3
  const magnitude = 10 ** Math.floor(Math.log10(rough))
  const step = [1, 2, 2.5, 5, 10].map((n) => n * magnitude).find((s) => s >= rough)!
  return Array.from({ length: Math.ceil(max / step) + 1 }, (_, i) => i * step)
}
