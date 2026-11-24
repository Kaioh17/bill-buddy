import {
  CalendarDotsIcon,
  CaretDownIcon,
  QuestionIcon,
  RepeatIcon,
  SquaresFourIcon,
  UserIcon,
  type Icon,
} from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router'
import { getCurrentUser } from '../lib/api'
import { useApi } from '../lib/useApi'
import { useAuth, useSessionExpiry } from '../lib/useAuth'
import SkipLink from './SkipLink'

const NAV: [to: string, label: string, icon: Icon][] = [
  ['/dashboard', 'Dashboard', SquaresFourIcon],
  ['/subscriptions', 'Subscriptions', RepeatIcon],
  ['/payments', 'Payments', CalendarDotsIcon],
]

const navLink =
  'inline-flex min-h-11 items-center gap-2 rounded-lg px-2.5 text-sm font-medium whitespace-nowrap text-gray-500 transition-colors hover:text-gray-900 sm:px-4 md:min-h-10 aria-[current=page]:bg-secondary-50 aria-[current=page]:font-semibold aria-[current=page]:text-secondary-700'

/** Frame for signed-in pages: top bar with the main nav, then the page. */
export default function AppShell() {
  useSessionExpiry()

  return (
    <div className="flex min-h-[100dvh] flex-col">
      <SkipLink />
      <header className="border-b border-gray-200 bg-primary">
        <div className="mx-auto flex max-w-[90rem] flex-wrap items-center gap-x-4 px-4 sm:px-8 md:min-h-20 lg:gap-x-12 lg:px-16">
          <Link to="/dashboard" aria-label="Bill Buddy home" className="inline-flex min-h-14 items-center gap-2.5 rounded-lg">
            <img src="/favicon.svg" width={34} height={34} alt="" />
            <span className="text-xl tracking-tight lg:text-[1.375rem]">Bill Buddy</span>
          </Link>

          {/* Own row under the logo on phones. */}
          <nav aria-label="Main" className="order-last -mx-2.5 flex w-full gap-1 pb-2 sm:mx-0 md:order-none md:w-auto md:pb-0">
            {NAV.map(([to, label, NavIcon]) => (
              <NavLink key={to} to={to} className={navLink}>
                <NavIcon size={18} aria-hidden className="max-[379px]:hidden" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-1">
            <Link
              to="/help"
              aria-label="Help"
              className="grid size-11 place-items-center rounded-lg text-gray-500 transition-colors hover:text-gray-900"
            >
              <QuestionIcon size={22} aria-hidden />
            </Link>
            <AccountMenu />
          </div>
        </div>
      </header>

      <main id="main" className="flex flex-1 flex-col">
        <Outlet />
      </main>
    </div>
  )
}

function AccountMenu() {
  const { logout } = useAuth()
  const { data: user } = useApi(getCurrentUser)
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointer = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      setOpen(false)
      trigger.current?.focus()
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div
      ref={root}
      className="relative"
      // Tabbing out closes it too. relatedTarget is null when the window itself loses focus.
      onBlur={(e) => e.relatedTarget && !e.currentTarget.contains(e.relatedTarget) && setOpen(false)}
    >
      <button
        ref={trigger}
        type="button"
        aria-expanded={open}
        aria-controls="account-menu"
        onClick={() => setOpen((o) => !o)}
        className="flex min-h-11 items-center gap-2.5 rounded-lg px-1.5 text-gray-500 transition-colors hover:text-gray-900"
      >
        <span className="sr-only">Account</span>
        <span className="grid size-[34px] place-items-center rounded-full bg-secondary-50 text-xs font-semibold text-secondary-700">
          {user ? user.first_name.charAt(0) + user.last_name.charAt(0) : <UserIcon size={18} aria-hidden />}
        </span>
        <CaretDownIcon size={14} weight="bold" aria-hidden />
      </button>
      <div
        id="account-menu"
        hidden={!open}
        className="absolute top-full right-0 z-30 mt-1 w-48 rounded-xl border border-gray-200 bg-primary p-1.5 shadow-float"
      >
        {user && (
          <p className="truncate px-3 py-2 text-sm text-gray-500">
            {user.first_name} {user.last_name}
          </p>
        )}
        <button
          type="button"
          onClick={logout}
          className="block min-h-11 w-full rounded-lg px-3 text-left text-sm font-medium transition-colors hover:bg-gray-100"
        >
          Log out
        </button>
      </div>
    </div>
  )
}
