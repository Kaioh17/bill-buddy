/**
 * Sample data for `npm run dev` with VITE_USE_MOCKS=true (see .env.example). Never bundled
 * in a production build. Dates are relative to today, so the dashboard always looks current.
 */
import {
  ApiError,
  session,
  type CatalogEntry,
  type CurrentUser,
  type Dashboard,
  type Reconciliation,
  type Subscription,
  type UpcomingPayment,
} from './api'
import { addDays, addMonths, parseDay, sumMoney, toDay } from './format'

export type MockSubscription = {
  id: string
  name: string
  category: string
  amount: string
  frequency: 'WEEKLY' | 'MONTHLY' | 'YEARLY'
  next: string
  label: UpcomingPayment['label']
}

// name, category, amount, days until the next payment, label
const ROWS: [string, string, string, number, UpcomingPayment['label']][] = [
  ['Netflix', 'Entertainment', '15.99', 0, 'actual'],
  ['Gym', 'Health & fitness', '30.00', 3, 'manual'],
  ['Phone', 'Utilities', '45.00', 6, 'actual'],
  ['Spotify', 'Entertainment', '9.99', 9, 'actual'],
  ['Internet', 'Utilities', '49.99', 13, 'actual'],
  ['Electricity', 'Utilities', '66.04', 16, 'actual'],
  ['Apple TV+', 'Entertainment', '7.99', 21, 'actual'],
  ['Notion', 'Productivity', '20.00', 25, 'actual'],
]

/** Spend per month, oldest first, ending with the current month. */
const HISTORY = [185, 180, 195, 200, 205, 195, 190, 225, 235, 210, 255, 245]

export const subscriptions = (today: string): MockSubscription[] =>
  ROWS.map(([name, category, amount, inDays, label], i) => ({
    id: `mock-${i}`,
    name,
    category,
    amount,
    frequency: 'MONTHLY',
    next: addDays(today, inDays),
    label,
  }))

/** The nth payment after `first`. Month ends clamp: Jan 31 is followed by Feb 28. */
function nthPayment(first: string, frequency: MockSubscription['frequency'], n: number): string {
  if (frequency === 'WEEKLY') return addDays(first, 7 * n)
  const start = parseDay(first)
  const months = frequency === 'YEARLY' ? 12 * n : n
  const date = new Date(start.getFullYear(), start.getMonth() + months + 1, 0) // last day of that month
  date.setDate(Math.min(start.getDate(), date.getDate()))
  return toDay(date)
}

/** Same rule as the Design Report's getUpcomingPayments: day 30 is in, day 31 is not. */
export function upcomingPayments(subs: MockSubscription[], today: string): UpcomingPayment[] {
  const end = addDays(today, 30)
  const out: UpcomingPayment[] = []
  for (const s of subs) {
    for (let n = 0, date = s.next; date <= end; date = nthPayment(s.next, s.frequency, ++n)) {
      if (date >= today)
        out.push({ subscription_id: s.id, name: s.name, category: s.category, date, amount: s.amount, label: s.label })
    }
  }
  return out.sort((a, b) => a.date.localeCompare(b.date))
}

function monthlyCost(s: MockSubscription): number {
  const amount = Number(s.amount)
  if (s.frequency === 'WEEKLY') return (amount * 52) / 12
  return s.frequency === 'YEARLY' ? amount / 12 : amount
}

export function dashboard(subs: MockSubscription[], from: string, to: string, today: string): Dashboard {
  const manual = sumMoney(subs.filter((s) => s.label === 'manual').map(monthlyCost))
  const history = new Map(HISTORY.toReversed().map((total, ago) => [addMonths(today.slice(0, 7), -ago), total]))

  const months: Dashboard['months'] = []
  for (let month = from; month <= to; month = addMonths(month, 1)) {
    const total = subs.length ? (history.get(month) ?? 0) : 0
    months.push({
      month,
      confirmed: Math.max(total - manual, 0).toFixed(2),
      manual: (total ? manual : 0).toFixed(2),
    })
  }

  const yearly = new Map<string, number[]>()
  for (const s of subs) yearly.set(s.category, [...(yearly.get(s.category) ?? []), monthlyCost(s) * 12])

  return {
    months,
    total_monthly_spend: sumMoney(subs.map(monthlyCost)).toFixed(2),
    yearly_by_category: [...yearly].map(([category, costs]) => ({ category, amount: sumMoney(costs).toFixed(2) })),
    active_count: subs.length,
  }
}

// ---- stand-ins for the API calls ----

/** A token the session store can read. The email rides along to pick the scenario. */
export function token(email: string): string {
  const payload = { sub: encodeURIComponent(email), exp: Math.floor(Date.now() / 1000) + 12 * 3600 }
  return `mock.${btoa(JSON.stringify(payload))}.mock`
}

/** Applies the scenario picked by the sign-in email, then returns that user's subscriptions. */
async function load(): Promise<{ subs: MockSubscription[]; today: string }> {
  const signedIn = session.get()
  const email: string = signedIn ? JSON.parse(atob(signedIn.split('.')[1])).sub : ''
  await new Promise((done) => setTimeout(done, email.startsWith('slow') ? 4000 : 250))
  if (email.startsWith('error'))
    throw new ApiError(0, 'network_error', 'Cannot reach the server. Check your connection and try again.')
  const today = toDay(new Date())
  return { subs: email.startsWith('empty') ? [] : subscriptions(today), today }
}

export async function getDashboard(from: string, to: string): Promise<Dashboard> {
  const { subs, today } = await load()
  return dashboard(subs, from, to, today)
}

export async function getUpcomingPayments(): Promise<UpcomingPayment[]> {
  const { subs, today } = await load()
  return upcomingPayments(subs, today)
}

export const currentUser: CurrentUser = { first_name: 'Jordan', last_name: 'Lee' }

// ---- subscriptions: stateful, so confirm, dismiss and the picker behave like the real thing ----

const CATALOG: [name: string, type: string, category: string][] = [
  ['Netflix', 'Video streaming', 'Entertainment'],
  ['Hulu', 'Video streaming', 'Entertainment'],
  ['Spotify', 'Music streaming', 'Entertainment'],
  ['Apple Music', 'Music streaming', 'Entertainment'],
  ['Dropbox', 'Cloud storage', 'Productivity'],
  ['Planet Fitness', 'Gym', 'Health & fitness'],
]

const resolved = new Set<string>() // likely items already confirmed or dismissed
let assumed = new Set(['Netflix', 'Spotify', 'Hulu'])

export async function getSubscriptions(): Promise<Subscription[]> {
  const { subs, today } = await load()
  const out: Subscription[] = subs.map((s) => ({
    id: s.id,
    name: s.name,
    label: s.label,
    frequency: s.frequency,
    kind: 'SUBSCRIPTION',
    category: s.category,
    service_type: s.name === 'Spotify' ? 'Music streaming' : null,
    amount: s.amount,
    last_payment_date: addDays(s.next, -30),
    next_expected_date: s.next,
    likely_reasons: [],
    on_assumed_list: assumed.has(s.name),
    similar_to: s.name === 'Spotify' ? ['Apple Music'] : [],
  }))
  if (!subs.length) return []
  out.push(
    {
      ...out[0],
      id: 'mock-apple-music',
      name: 'Apple Music',
      service_type: 'Music streaming',
      amount: '10.99',
      on_assumed_list: false,
      similar_to: ['Spotify'],
      next_expected_date: addDays(today, 11),
    },
    {
      ...out[0],
      id: 'mock-likely',
      name: 'Cloud Backup Co',
      label: 'likely',
      category: 'Productivity',
      amount: '14.99',
      likely_reasons: ['amount changed, maybe a plan change'],
      on_assumed_list: false,
      similar_to: [],
      next_expected_date: addDays(today, 8),
    },
  )
  return out.filter((s) => !resolved.has(s.id))
}

export async function confirmSubscription(id: string) {
  resolved.add(id)
}

export async function dismissSubscription(id: string) {
  resolved.add(id)
}

export async function getCatalog(): Promise<CatalogEntry[]> {
  await load()
  return CATALOG.map(([name, service_type, category]) => ({
    id: name,
    name,
    service_type,
    category,
    selected: assumed.has(name),
  }))
}

export async function saveAssumed(ids: string[]) {
  assumed = new Set(ids)
}

export async function getReconciliation(): Promise<Reconciliation> {
  const { subs, today } = await load()
  if (!subs.length) return { unexpected: [], unconfirmed: [] }
  return {
    unexpected: [{ subscription_id: 'mock-apple-music', name: 'Apple Music', last_payment_date: addDays(today, -19), amount: '10.99' }]
      .filter(() => !assumed.has('Apple Music')),
    unconfirmed: [...assumed]
      .filter((name) => !['Netflix', 'Spotify'].includes(name))
      .map((name) => ({ catalog_entry_id: name, name, last_payment_date: null, amount: null })),
  }
}

export async function linkSandboxBank() {
  await load() // sample data is always "linked", this only simulates the wait
}
