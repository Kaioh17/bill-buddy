import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, login, session, tokenExpiry } from './api'

const jwt = (exp: number) => `x.${btoa(JSON.stringify({ exp })).replace(/=/g, '')}.y`
const reply = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers })

const fetchMock = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  session.end()
})
afterEach(() => fetchMock.mockReset())

describe('api client', () => {
  it('logs in with a form-encoded body and stores the token', async () => {
    fetchMock.mockResolvedValue(reply(200, { access_token: 'tok', token_type: 'bearer', expires_in: 900 }))
    await login('a@b.co', 'pw')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/auth\/login$/)
    expect(init.body.toString()).toBe('username=a%40b.co&password=pw')
    expect(session.get()).toBe('tok')
  })

  it('swaps in the renewed token and sends the current one', async () => {
    session.start('old')
    fetchMock.mockResolvedValue(reply(200, {}, { 'X-Access-Token': 'new' }))
    await api('/health/me')
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer old')
    expect(session.get()).toBe('new')
  })

  it('does not revive a session that ended while the request was in flight', async () => {
    session.start('old')
    fetchMock.mockImplementation(async () => {
      session.end()
      return reply(200, {}, { 'X-Access-Token': 'new' })
    })
    await api('/health/me')
    expect(session.get()).toBeNull()
  })

  it('treats a 401 with a token as an expired session', async () => {
    session.start('old')
    fetchMock.mockResolvedValue(reply(401, { error: { code: 'token_expired', message: 'Session expired' } }))
    await expect(api('/health/me')).rejects.toMatchObject({ status: 401, code: 'token_expired' })
    expect(session.get()).toBeNull()
    expect(session.wasExpired()).toBe(true)
  })

  it('treats a 401 without a token as a plain failed login', async () => {
    fetchMock.mockResolvedValue(reply(401, { error: { code: 'invalid_credentials', message: 'Invalid email or password' } }))
    await expect(login('a@b.co', 'bad')).rejects.toThrow('Invalid email or password')
    expect(session.wasExpired()).toBe(false)
  })

  it('maps validation details to fields, and unkeyed ones to the message', async () => {
    fetchMock.mockResolvedValue(
      reply(422, {
        error: {
          code: 'validation_error',
          message: 'Invalid request',
          details: [
            { field: 'password', message: 'too short' },
            { field: '', message: 'Passwords do not match' },
          ],
        },
      }),
    )
    const err = (await api('/auth/signup', { json: {} }).catch((e) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.fields).toEqual({ password: 'too short' })
    expect(err.message).toBe('Passwords do not match')
  })

  it('reports an unreachable server', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'))
    await expect(api('/health/')).rejects.toMatchObject({ code: 'network_error' })
  })

  it('reads the expiry from a token', () => {
    expect(tokenExpiry(jwt(1_700_000_000))).toBe(1_700_000_000_000)
    expect(tokenExpiry('garbage')).toBe(0)
  })
})
