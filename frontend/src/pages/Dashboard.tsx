import { useEffect, useState } from 'react'
import { Alert, Card } from '../components/ui'
import { ApiError, getSessionInfo, type TokenInfo } from '../lib/api'
import { GENERIC_ERROR } from '../lib/form'

const when = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export default function Dashboard() {
  const [info, setInfo] = useState<TokenInfo>()
  const [error, setError] = useState<string>()

  // Calls a protected route. It proves the guard works and shows the session the backend sees.
  useEffect(() => {
    let live = true
    getSessionInfo()
      .then((d) => live && setInfo(d))
      .catch((err) => live && setError(err instanceof ApiError ? err.message : GENERIC_ERROR))
    return () => {
      live = false
    }
  }, [])

  const rows: [string, string | undefined][] = [
    ['Session started', info?.session_started_at],
    ['Logs you out if idle after', info?.expires_at],
    ['Hard session limit', info?.session_expires_at],
  ]

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pt-28 pb-16 lg:py-32">
      <title>Dashboard - Bill Buddy</title>
      <div className="animate-rise">
        <h1 className="text-4xl leading-[1.04] font-extrabold tracking-tight sm:text-6xl">You are signed in.</h1>
      </div>

      <div className="mt-12 grid gap-6 md:grid-cols-3">
        <Card className="animate-rise [animation-delay:150ms] md:col-span-2">
          <h2 className="text-xl font-bold tracking-tight">Your session</h2>
          <p className="mt-1 text-gray-500">Renewed on every request, so only inactivity ends it.</p>
          {error && (
            <div className="mt-6">
              <Alert tone="error">Could not load session details. {error}</Alert>
            </div>
          )}
          <dl className="mt-6 grid gap-4">
            {rows.map(([label, value]) => (
              <div key={label} className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1 rounded-2xl bg-gray-50 px-4 py-3">
                <dt className="text-sm text-gray-500">{label}</dt>
                <dd className="min-h-6 text-sm font-semibold">
                  {value ? when.format(new Date(value)) : !error && <span className="block h-5 w-36 animate-pulse rounded-xl bg-gray-200" />}
                </dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card className="animate-rise [animation-delay:300ms]">
          <h2 className="text-xl font-bold tracking-tight">Subscriptions</h2>
          <p className="mt-1 text-gray-500">Nothing here yet. Your subscriptions will show up on this page.</p>
        </Card>
      </div>
    </div>
  )
}
