import { describe, expect, it } from 'vitest'
import { addDays, sumMoney } from './format'
import { dashboard, subscriptions, upcomingPayments, type MockSubscription } from './mocks'

const TODAY = '2026-10-30'
const subs = subscriptions(TODAY)

const sub = (name: string, next: string, frequency: MockSubscription['frequency'] = 'MONTHLY'): MockSubscription => ({
  id: name,
  name,
  category: 'Utilities',
  amount: '10.00',
  frequency,
  next,
  label: 'actual',
})

describe('sample dashboard', () => {
  const data = dashboard(subs, '2026-05', '2026-10', TODAY)

  it('matches the mockup', () => {
    expect(data.total_monthly_spend).toBe('245.00')
    expect(data.active_count).toBe(8)
    expect(data.months.map((m) => sumMoney([m.confirmed, m.manual]))).toEqual([190, 225, 235, 210, 255, 245])
  })

  it('projects twelve months per category', () => {
    expect(sumMoney(data.yearly_by_category.map((c) => c.amount))).toBe(2940)
    expect(data.yearly_by_category).toContainEqual({ category: 'Utilities', amount: '1932.36' })
  })

  it('is all zeros for a new user (TC-15)', () => {
    const empty = dashboard([], '2026-05', '2026-10', TODAY)
    expect(empty).toMatchObject({ total_monthly_spend: '0.00', yearly_by_category: [], active_count: 0 })
    expect(empty.months.every((m) => m.confirmed === '0.00' && m.manual === '0.00')).toBe(true)
  })
})

describe('sample upcoming payments', () => {
  it('starts with the three in the mockup', () => {
    expect(upcomingPayments(subs, TODAY).slice(0, 3)).toMatchObject([
      { name: 'Netflix', date: '2026-10-30' },
      { name: 'Gym', date: '2026-11-02', label: 'manual' },
      { name: 'Phone', date: '2026-11-05' },
    ])
  })

  it('includes day 30 and leaves out day 31 (TC-14)', () => {
    const at = [29, 30, 31].map((n) => sub(`day ${n}`, addDays(TODAY, n)))
    expect(upcomingPayments(at, TODAY).map((p) => p.name)).toEqual(['day 29', 'day 30'])
  })

  it('repeats weekly payments and clamps month ends', () => {
    expect(upcomingPayments([sub('w', TODAY, 'WEEKLY')], TODAY)).toHaveLength(5)
    const dates = upcomingPayments([sub('m', '2027-01-31')], '2027-01-31').map((p) => p.date)
    expect(dates).toEqual(['2027-01-31', '2027-02-28'])
  })
})
