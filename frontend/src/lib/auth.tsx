import { Navigate, Outlet, useLocation } from 'react-router'
import { session } from './api'
import { useAuth, type LoginState } from './useAuth'

/** Route guard: logged-out visitors go to /login and come back to where they were. */
export function RequireAuth() {
  const { isAuthed } = useAuth()
  const location = useLocation()
  if (!isAuthed) {
    const state: LoginState = {
      from: location.pathname,
      notice: session.wasExpired() ? 'Your session expired. Log in again to continue.' : undefined,
    }
    return <Navigate to="/login" replace state={state} />
  }
  return <Outlet />
}

/**
 * Login and signup are pointless once signed in. This is also what finishes a login:
 * the session store flips, this redirects, so the pages never navigate themselves.
 */
export function GuestOnly() {
  const { isAuthed } = useAuth()
  const state = useLocation().state as LoginState
  return isAuthed ? <Navigate to={state?.from ?? '/dashboard'} replace /> : <Outlet />
}
