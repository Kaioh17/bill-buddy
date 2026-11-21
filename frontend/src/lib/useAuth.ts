import { useEffect, useSyncExternalStore } from 'react'
import { session, tokenExpiry } from './api'

/** Router state passed to /login: where to go afterwards and an optional message. */
export type LoginState = { from?: string; notice?: string } | null

export function useAuth() {
  const token = useSyncExternalStore(session.subscribe, session.get)
  return { isAuthed: token !== null, logout: session.end }
}

/** Ends the session the moment the token runs out, even if the user is idle on a page. */
export function useSessionExpiry() {
  const token = useSyncExternalStore(session.subscribe, session.get)
  useEffect(() => {
    if (!token) return
    const id = setTimeout(session.expire, Math.max(tokenExpiry(token) - Date.now(), 0))
    return () => clearTimeout(id)
  }, [token])
}
