import { NavLink, Outlet } from 'react-router'
import { useAuth, useSessionExpiry } from '../lib/useAuth'
import SkipLink from './SkipLink'
import { Button, ButtonLink } from './ui'

const YEAR = new Date().getFullYear()

const pill = 'flex items-center rounded-xl bg-primary/80 p-1.5 shadow-float backdrop-blur-xl'

const navLink =
  'inline-flex min-h-11 items-center rounded-lg px-4 text-sm font-medium text-gray-600 transition-colors duration-500 ease-fluid hover:text-gray-900 aria-[current=page]:bg-gray-100 aria-[current=page]:text-gray-900'

/** Frame for guest pages and the 404: skip link, floating glass nav, main landmark, footer. */
export default function Shell() {
  const { isAuthed, logout } = useAuth()
  useSessionExpiry()

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[radial-gradient(60rem_40rem_at_0%_0%,var(--color-secondary-50),transparent_70%)]">
      <SkipLink />

      <header className="fixed inset-x-0 top-4 z-40 flex justify-between px-4 sm:top-6 sm:grid sm:grid-cols-[1fr_auto_1fr]">
        {/* Brand stays centered; the actions sit in their own pill on the far right. */}
        <NavLink to="/" className={`${pill} px-4 sm:col-start-2`} aria-label="Bill Buddy home">
          <span className="inline-flex min-h-11 items-center gap-2 text-sm font-bold tracking-tight">
            <img src="/favicon.svg" width={24} height={24} alt="" />
            <span className="max-[479px]:sr-only">Bill Buddy</span>
          </span>
        </NavLink>
        <nav aria-label="Account" className={`${pill} gap-1 sm:col-start-3 sm:justify-self-end`}>
          {isAuthed ? (
            <>
              <NavLink to="/dashboard" className={navLink}>
                Dashboard
              </NavLink>
              <Button variant="soft" onClick={logout}>
                Log out
              </Button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={navLink}>
                Log in
              </NavLink>
              <ButtonLink to="/signup" arrow>
                Sign up
              </ButtonLink>
            </>
          )}
        </nav>
      </header>

      <main id="main" className="flex flex-1 flex-col">
        <Outlet />
      </main>

      <footer className="px-4 pb-8 text-center text-sm text-gray-500">&copy; {YEAR} Bill Buddy</footer>
    </div>
  )
}
