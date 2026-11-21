import { ArrowUpRightIcon, EyeIcon, EyeSlashIcon } from '@phosphor-icons/react'
import { useId, useState, type ComponentProps, type ReactNode } from 'react'
import { Link } from 'react-router'

/*
 * Building blocks. Look: soft structuralism. Surfaces are separated by soft shadows, not
 * borders. Blue for the one action that matters, pill buttons, big radii.
 * Motion is transform and opacity plus colour, on a spring-like curve (ease-fluid).
 */

// ---- Button ----

type Variant = 'solid' | 'soft'

const look: Record<Variant, string> = {
  solid: 'bg-secondary-600 text-white hover:bg-secondary-700',
  soft: 'bg-gray-100 text-gray-900 hover:bg-gray-200/70',
}

function buttonClass(variant: Variant, arrow: boolean, className = '') {
  return [
    'group inline-flex min-h-11 items-center gap-3 rounded-full text-sm font-semibold',
    'transition-[transform,background-color] duration-500 ease-fluid active:scale-[0.98]',
    'disabled:pointer-events-none disabled:bg-gray-200 disabled:text-gray-500',
    arrow ? 'justify-between py-1.5 pr-1.5 pl-6' : 'justify-center px-6 py-2.5',
    look[variant],
    className,
  ].join(' ')
}

/** Trailing arrow lives in its own circle, flush with the button's right edge. */
function Arrow() {
  return (
    <span className="grid size-8 place-items-center rounded-full bg-white/15 transition-transform duration-500 ease-fluid group-hover:-translate-y-px group-hover:translate-x-0.5 group-hover:scale-105">
      <ArrowUpRightIcon size={16} weight="light" aria-hidden />
    </span>
  )
}

type ButtonProps = { variant?: Variant; arrow?: boolean }

export function Button({ variant = 'solid', arrow = false, className, children, ...rest }: ButtonProps & ComponentProps<'button'>) {
  return (
    <button className={buttonClass(variant, arrow, className)} {...rest}>
      {children}
      {arrow && <Arrow />}
    </button>
  )
}

export function ButtonLink({ variant = 'solid', arrow = false, className, children, ...rest }: ButtonProps & ComponentProps<typeof Link>) {
  return (
    <Link className={buttonClass(variant, arrow, className)} {...rest}>
      {children}
      {arrow && <Arrow />}
    </Link>
  )
}

// ---- Form field ----

type FieldProps = { label: string; error?: string; hint?: string } & ComponentProps<'input'>

export function Field({ label, error, hint, type = 'text', className = '', ...rest }: FieldProps) {
  const id = useId()
  const [shown, setShown] = useState(false)
  const isPassword = type === 'password'
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined

  return (
    <div className={className}>
      <label htmlFor={id} className="mb-2 block text-sm font-medium text-gray-900">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={isPassword && shown ? 'text' : type}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={`block min-h-13 w-full rounded-2xl bg-gray-50 px-4 text-base text-gray-900 shadow-field outline-none transition-shadow duration-500 ease-fluid placeholder:text-gray-500 ${
            error ? 'ring-2 ring-red-600' : 'focus:ring-2 focus:ring-secondary-600'
          } ${isPassword ? 'pr-14' : ''}`}
          {...rest}
        />
        {isPassword && (
          <button
            type="button"
            aria-label={shown ? 'Hide password' : 'Show password'}
            aria-pressed={shown}
            onClick={() => setShown((s) => !s)}
            className="absolute top-1 right-1 grid size-11 place-items-center rounded-xl text-gray-500 transition-colors duration-500 ease-fluid hover:text-gray-900"
          >
            {shown ? <EyeSlashIcon size={20} weight="light" aria-hidden /> : <EyeIcon size={20} weight="light" aria-hidden />}
          </button>
        )}
      </div>
      {error ? (
        <p id={`${id}-error`} className="mt-2 text-sm text-red-600">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="mt-2 text-sm text-gray-500">
            {hint}
          </p>
        )
      )}
    </div>
  )
}

// ---- Surfaces ----

/** White card lifted off the page by a soft shadow. */
export function Card({ className = '', children }: { className?: string; children: ReactNode }) {
  return <div className={`rounded-[2rem] bg-primary p-6 shadow-float sm:p-8 ${className}`}>{children}</div>
}

export function Alert({ tone, children }: { tone: 'error' | 'info'; children: ReactNode }) {
  const toneClass =
    tone === 'error' ? 'bg-red-50 text-red-800' : 'bg-secondary-50 text-secondary-700'
  return (
    <p role={tone === 'error' ? 'alert' : 'status'} className={`rounded-2xl px-4 py-3 text-sm ${toneClass}`}>
      {children}
    </p>
  )
}
