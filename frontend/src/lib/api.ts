/**
 * API client and session store for the FastAPI backend.
 *
 * The backend renews the session on every authenticated response by sending a fresh
 * token in X-Access-Token, so the token only dies after inactivity. We swap it in
 * whenever we see the header, and drop to the login page on 401 or when it expires.
 * The token lives in sessionStorage: gone when the tab closes, matching the short session.
 */

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const KEY = 'bb.token'
const RENEW_HEADER = 'X-Access-Token'

// ---- session store (plain external store, read with useSyncExternalStore) ----

function read(): string | null {
  try {
    return sessionStorage.getItem(KEY)
  } catch {
    return null
  }
}

let token = read()
let expired = false
const subscribers = new Set<() => void>()

function write(next: string | null) {
  token = next
  try {
    if (next) sessionStorage.setItem(KEY, next)
    else sessionStorage.removeItem(KEY)
  } catch {
    // storage blocked: the session just lasts until reload
  }
  subscribers.forEach((fn) => fn())
}

export const session = {
  get: () => token,
  subscribe(fn: () => void) {
    subscribers.add(fn)
    return () => subscribers.delete(fn)
  },
  /** True when the last session ended by timeout or a 401, so the login page can say why. */
  wasExpired: () => expired,
  start(next: string) {
    expired = false
    write(next)
  },
  end() {
    expired = false
    write(null)
  },
  expire() {
    if (!token) return
    expired = true
    write(null)
  },
}

/** Expiry of a JWT in epoch ms (read only, the server does the verifying). 0 if unreadable. */
export function tokenExpiry(jwt: string): number {
  try {
    const payload = JSON.parse(atob(jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return Number(payload.exp) * 1000 || 0
  } catch {
    return 0
  }
}

// ---- requests ----

export class ApiError extends Error {
  status: number
  code: string
  /** Server-side validation messages keyed by field name (email, password, ...). */
  fields: Record<string, string>

  constructor(status: number, code: string, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.code = code
    this.fields = fields
  }
}

type Body = { json: unknown } | { form: Record<string, string> }

export async function api<T>(path: string, opts: { method?: string } & Partial<Body> = {}): Promise<T> {
  const headers: Record<string, string> = {}
  const sentToken = token
  if (sentToken) headers.Authorization = `Bearer ${sentToken}`

  let body: BodyInit | undefined
  if ('json' in opts) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.json)
  } else if ('form' in opts && opts.form) {
    body = new URLSearchParams(opts.form) // sets its own form-urlencoded content type
  }

  let res: Response
  try {
    res = await fetch(BASE + path, { method: opts.method ?? (body ? 'POST' : 'GET'), headers, body })
  } catch {
    throw new ApiError(0, 'network_error', 'Cannot reach the server. Check your connection and try again.')
  }

  const renewed = res.headers.get(RENEW_HEADER)
  // `token` is checked too so a response landing after logout cannot revive the session.
  if (renewed && sentToken && token) write(renewed)

  if (res.ok) return (res.status === 204 ? undefined : await res.json()) as T

  // A 401 on a request that carried a token means the session is over. A 401 without one
  // is just a failed login and must not look like a timeout.
  if (res.status === 401 && sentToken) session.expire()

  const error = (await res.json().catch(() => null))?.error
  const fields: Record<string, string> = {}
  const general: string[] = []
  for (const d of error?.details ?? []) {
    if (d.field) fields[d.field] ??= d.message
    else general.push(d.message)
  }
  throw new ApiError(
    res.status,
    error?.code ?? 'unknown_error',
    general.join(' ') || error?.message || 'Something went wrong. Try again.',
    fields,
  )
}

// ---- endpoints ----

export type SignupInput = {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

type Token = { access_token: string; token_type: string; expires_in: number }

export type TokenInfo = {
  user_id: string
  issued_at: string
  expires_at: string
  session_started_at: string
  session_expires_at: string
  token_id: string
}

// Sample data for dev. `DEV` is false in a production build, so the mock module and its
// sign-in are dropped from the bundle. Tests always use the real client.
const MOCK = import.meta.env.DEV && import.meta.env.MODE !== 'test' && import.meta.env.VITE_USE_MOCKS === 'true'
const mocks = () => import('./mocks')

export async function login(email: string, password: string) {
  if (MOCK) return session.start((await mocks()).token(email))
  // OAuth2 password flow: form-encoded, and the email goes in `username`.
  const t = await api<Token>('/auth/login', { form: { username: email, password } })
  session.start(t.access_token)
}

export async function signup(input: SignupInput) {
  if (!MOCK) await api('/auth/signup', { json: input })
}

export const getSessionInfo = () => api<TokenInfo>('/health/me')

/** The backend's success envelope. Login and the health routes do not use it. */
type Envelope<T> = { meta: { count: number | null }; data: T }

// Money arrives as decimal strings. Format and add it with lib/format.

export type Dashboard = {
  /** Oldest first. `manual` is kept apart from confirmed bank payments (FR 4b). */
  months: { month: string; confirmed: string; manual: string }[]
  total_monthly_spend: string
  /** Projected, so always shown as estimated. */
  yearly_by_category: { category: string | null; amount: string }[]
  active_count: number
}

export type UpcomingPayment = {
  subscription_id: string
  name: string
  category: string | null
  date: string
  amount: string
  label: 'actual' | 'manual'
}

export type CurrentUser = { first_name: string; last_name: string }

// TODO(backend): /dashboard and /payments/upcoming are planned in docs/ENDPOINTS.md but not
// built yet. These shapes follow the Design Report (FR 5), check them once the routes exist.

/** Months are `YYYY-MM`, both ends included. */
export async function getDashboard(from: string, to: string): Promise<Dashboard> {
  if (MOCK) return (await mocks()).getDashboard(from, to)
  return (await api<Envelope<Dashboard>>(`/dashboard?from=${from}&to=${to}`)).data
}

/** The next 30 days, soonest first. */
export async function getUpcomingPayments(): Promise<UpcomingPayment[]> {
  if (MOCK) return (await mocks()).getUpcomingPayments()
  return (await api<Envelope<UpcomingPayment[]>>('/payments/upcoming')).data
}

/** TODO(backend): no route returns the signed-in user's name yet, so this is null for now. */
export async function getCurrentUser(): Promise<CurrentUser | null> {
  return MOCK ? (await mocks()).currentUser : null
}

// ---- subscriptions, the assumed list and reconciliation ----

export type Frequency = 'WEEKLY' | 'MONTHLY' | 'YEARLY'

export type Subscription = {
  id: string
  name: string
  /** `likely` is a detection the user has not confirmed yet. It is left out of every total. */
  label: 'actual' | 'likely' | 'manual'
  frequency: Frequency
  kind: 'SUBSCRIPTION' | 'BILL'
  category: string | null
  service_type: string | null
  amount: string
  last_payment_date: string | null
  /** An estimate from the last payment, never a confirmed bill. */
  next_expected_date: string
  /** Why a likely item is only likely. Empty for the others. */
  likely_reasons: string[]
  on_assumed_list: boolean
  /** Names of other active subscriptions of the same service type, such as two music apps. */
  similar_to: string[]
}

export type CatalogEntry = { id: string; name: string; service_type: string; category: string; selected: boolean }

export type Reconciliation = {
  /** Found in the bank data, not on the assumed list. */
  unexpected: { subscription_id: string; name: string; last_payment_date: string | null; amount: string }[]
  /** On the assumed list, but no matching bank payment in the last 60 days. */
  unconfirmed: { catalog_entry_id: string; name: string; last_payment_date: string | null; amount: string | null }[]
}

export async function getSubscriptions(): Promise<Subscription[]> {
  if (MOCK) return (await mocks()).getSubscriptions()
  return (await api<Envelope<Subscription[]>>('/subscriptions')).data
}

export async function confirmSubscription(id: string): Promise<void> {
  if (MOCK) return (await mocks()).confirmSubscription(id)
  await api(`/subscriptions/${id}/confirm`, { method: 'POST' })
}

export async function dismissSubscription(id: string): Promise<void> {
  if (MOCK) return (await mocks()).dismissSubscription(id)
  await api(`/subscriptions/${id}/dismiss`, { method: 'POST' })
}

export async function getCatalog(): Promise<CatalogEntry[]> {
  if (MOCK) return (await mocks()).getCatalog()
  return (await api<Envelope<CatalogEntry[]>>('/catalog')).data
}

/** Replaces the assumed list. The server drops ids it does not know. */
export async function saveAssumed(catalogEntryIds: string[]): Promise<void> {
  if (MOCK) return (await mocks()).saveAssumed(catalogEntryIds)
  await api('/assumed', { method: 'PUT', json: { catalog_entry_ids: catalogEntryIds } })
}

export async function getReconciliation(): Promise<Reconciliation> {
  if (MOCK) return (await mocks()).getReconciliation()
  return (await api<Envelope<Reconciliation>>('/reconciliation')).data
}

/**
 * Dev only: links Plaid's test bank with no Link UI, the backend refuses outside the sandbox.
 * Plaid's sandbox sends only the last month on the first pull and the rest on the second,
 * so this syncs once more. Without it nothing recurs yet and detection finds nothing.
 */
export async function linkSandboxBank(): Promise<void> {
  if (MOCK) return (await mocks()).linkSandboxBank()
  const { data } = await api<Envelope<{ id: string }>>('/plaid/sandbox-link', { method: 'POST' })
  await api(`/accounts/${data.id}/sync`, { method: 'POST' })
}
