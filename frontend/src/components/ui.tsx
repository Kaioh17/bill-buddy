import { ArrowRightIcon, EyeIcon, EyeSlashIcon } from '@phosphor-icons/react'
import { useId, useState, type ComponentProps, type ReactNode } from 'react'
import { Link } from 'react-router'

/*
 * Building blocks. Look: white surfaces on a pale gray page, separated by hairline borders.
 * Teal for the one action that matters, small radii.
 * Motion is transform and opacity plus colour, on a spring-like curve (ease-fluid).
 */

// ---- Button ----

type Variant = 'solid' | 'soft'

const look: Record<Variant, string> = {
  solid: 'bg-secondary-600 text-white hover:bg-secondary-700',
  soft: 'border border-gray-200 bg-primary text-gray-900 hover:bg-gray-100',
}

function buttonClass(variant: Variant, className = '') {
  return [
    'group inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium',
    'transition-[transform,background-color] duration-500 ease-fluid active:scale-[0.98]',
    'disabled:pointer-events-none disabled:bg-gray-200 disabled:text-gray-500',
    look[variant],
    className,
  ].join(' ')
}

function Arrow() {
  return (
    <ArrowRightIcon
      size={16}
      aria-hidden
      className="transition-transform duration-500 ease-fluid group-hover:translate-x-0.5"
    />
  )
}

type ButtonProps = { variant?: Variant; arrow?: boolean }

export function Button({ variant = 'solid', arrow = false, className, children, ...rest }: ButtonProps & ComponentProps<'button'>) {
  return (
    <button className={buttonClass(variant, className)} {...rest}>
      {children}
      {arrow && <Arrow />}
    </button>
  )
}

export function ButtonLink({ variant = 'solid', arrow = false, className, children, ...rest }: ButtonProps & ComponentProps<typeof Link>) {
  return (
    <Link className={buttonClass(variant, className)} {...rest}>
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
          className={`block min-h-11 w-full rounded-lg border border-gray-300 bg-primary px-3.5 text-base text-gray-900 outline-none transition-shadow duration-500 ease-fluid placeholder:text-gray-500 ${
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
            className="absolute top-0 right-0 grid size-11 place-items-center rounded-lg text-gray-500 transition-colors duration-500 ease-fluid hover:text-gray-900"
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

/** White card with a hairline border. */
export function Card({ className = '', children }: { className?: string; children: ReactNode }) {
  return <div className={`rounded-xl border border-gray-200 bg-primary p-5 sm:p-6 ${className}`}>{children}</div>
}

export function Alert({ tone, children }: { tone: 'error' | 'info'; children: ReactNode }) {
  const toneClass =
    tone === 'error' ? 'bg-red-50 text-red-800' : 'bg-secondary-50 text-secondary-700'
  return (
    <p role={tone === 'error' ? 'alert' : 'status'} className={`rounded-lg px-4 py-3 text-sm ${toneClass}`}>
      {children}
    </p>
  )
}
