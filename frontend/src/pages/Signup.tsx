import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import SplitLayout from '../components/SplitLayout'
import { Alert, Button, Field } from '../components/ui'
import { ApiError, login, signup, type SignupInput } from '../lib/api'
import type { LoginState } from '../lib/useAuth'
import { focusFirstError, GENERIC_ERROR, type Errors } from '../lib/form'

// Mirrors the backend limits (schema/auth.py). The server stays the authority.
const PASSWORD_MIN = 12
const FIELDS = ['first_name', 'last_name', 'email', 'password', 'confirm_password'] as const

export default function Signup() {
  const navigate = useNavigate()
  const [errors, setErrors] = useState<Errors>({})
  const [formError, setFormError] = useState<string>()
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const data = new FormData(form)
    const input = Object.fromEntries(FIELDS.map((f) => [f, String(data.get(f))])) as SignupInput
    input.first_name = input.first_name.trim()
    input.last_name = input.last_name.trim()
    input.email = input.email.trim()

    const next: Errors = {}
    if (!input.first_name) next.first_name = 'Enter your first name'
    if (!input.last_name) next.last_name = 'Enter your last name'
    if (!/^\S+@\S+\.\S+$/.test(input.email)) next.email = 'Enter a valid email'
    if (input.password.length < PASSWORD_MIN) next.password = `Use at least ${PASSWORD_MIN} characters`
    if (input.confirm_password !== input.password) next.confirm_password = 'Passwords do not match'
    setErrors(next)
    setFormError(undefined)
    if (Object.keys(next).length) return focusFirstError(form, next)

    setBusy(true)
    try {
      await signup(input)
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : null
      const fields = { ...apiErr?.fields }
      if (apiErr?.code === 'email_already_registered') fields.email = apiErr.message
      setErrors(fields)
      if (Object.keys(fields).length) focusFirstError(form, fields)
      else setFormError(apiErr?.message ?? GENERIC_ERROR)
      setBusy(false)
      return
    }

    try {
      await login(input.email, input.password) // GuestOnly redirects once the session exists
    } catch {
      // The account exists now, so sending them back to signup would only hit "already registered".
      const state: LoginState = { notice: 'Account created. Log in to continue.' }
      navigate('/login', { replace: true, state })
    }
  }

  return (
    <SplitLayout
      title="Start with a clear picture."
      lede="Create an account to see what you pay for and what is due next."
    >
      <title>Sign up - Bill Buddy</title>
      <h2 className="text-2xl font-bold tracking-tight">Create your account</h2>
      <p className="mt-1 text-gray-500">It takes under a minute.</p>

      <form noValidate onSubmit={onSubmit} className="mt-6 grid gap-5 sm:grid-cols-2">
        {formError && (
          <div className="sm:col-span-2">
            <Alert tone="error">{formError}</Alert>
          </div>
        )}
        <Field label="First name" name="first_name" autoComplete="given-name" maxLength={50} error={errors.first_name} />
        <Field label="Last name" name="last_name" autoComplete="family-name" maxLength={50} error={errors.last_name} />
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          spellCheck={false}
          maxLength={254}
          error={errors.email}
          className="sm:col-span-2"
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          maxLength={128}
          hint={`At least ${PASSWORD_MIN} characters`}
          error={errors.password}
          className="sm:col-span-2"
        />
        <Field
          label="Confirm password"
          name="confirm_password"
          type="password"
          autoComplete="new-password"
          maxLength={128}
          error={errors.confirm_password}
          className="sm:col-span-2"
        />
        <Button type="submit" arrow disabled={busy} aria-busy={busy} className="w-full sm:col-span-2">
          {busy ? 'Creating account...' : 'Create account'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-500">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-secondary-600 underline underline-offset-4 hover:text-secondary-700">
          Log in
        </Link>
      </p>
    </SplitLayout>
  )
}
