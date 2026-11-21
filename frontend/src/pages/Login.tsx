import { useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router'
import SplitLayout from '../components/SplitLayout'
import { Alert, Button, Field } from '../components/ui'
import { ApiError, login } from '../lib/api'
import type { LoginState } from '../lib/useAuth'
import { focusFirstError, GENERIC_ERROR, type Errors } from '../lib/form'

export default function Login() {
  const notice = (useLocation().state as LoginState)?.notice
  const [errors, setErrors] = useState<Errors>({})
  const [formError, setFormError] = useState<string>()
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const data = new FormData(form)
    const email = String(data.get('email')).trim()
    const password = String(data.get('password'))

    const next: Errors = {}
    if (!email) next.email = 'Enter your email'
    if (!password) next.password = 'Enter your password'
    setErrors(next)
    setFormError(undefined)
    if (Object.keys(next).length) return focusFirstError(form, next)

    setBusy(true)
    try {
      await login(email, password) // GuestOnly redirects once the session exists
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : GENERIC_ERROR)
      setBusy(false)
    }
  }

  return (
    <SplitLayout
      title="Every subscription, one calm view."
      lede="Log in to pick up where you left off."
    >
      <title>Log in - Bill Buddy</title>
      <h2 className="text-2xl font-bold tracking-tight">Log in</h2>
      <p className="mt-1 text-gray-500">Use the email you signed up with.</p>

      <form noValidate onSubmit={onSubmit} className="mt-6 grid gap-5">
        {notice && <Alert tone="info">{notice}</Alert>}
        {formError && <Alert tone="error">{formError}</Alert>}
        <Field label="Email" name="email" type="email" autoComplete="email" inputMode="email" spellCheck={false} error={errors.email} />
        <Field label="Password" name="password" type="password" autoComplete="current-password" error={errors.password} />
        <Button type="submit" arrow disabled={busy} aria-busy={busy} className="w-full">
          {busy ? 'Logging in...' : 'Log in'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-500">
        New to Bill Buddy?{' '}
        <Link to="/signup" className="font-semibold text-secondary-600 underline underline-offset-4 hover:text-secondary-700">
          Create an account
        </Link>
      </p>
    </SplitLayout>
  )
}
