import { CaretDownIcon } from '@phosphor-icons/react'
import type { ComponentProps, ReactNode } from 'react'

type Props = { label: string; icon?: ReactNode; compact?: boolean } & ComponentProps<'select'>

/** Native select in the app's style. The label is for screen readers only. */
export default function Select({ label, icon, compact = false, children, ...rest }: Props) {
  const size = compact ? 'min-h-8 pr-8 pl-2.5 text-xs' : `min-h-11 pr-9 text-sm ${icon ? 'pl-11' : 'pl-4'}`
  return (
    <span className="relative inline-flex items-center">
      {icon && <span className="pointer-events-none absolute left-4 text-gray-500">{icon}</span>}
      <select
        aria-label={label}
        className={`w-full cursor-pointer appearance-none rounded-lg border border-gray-200 bg-primary text-gray-900 transition-colors hover:bg-gray-50 ${size}`}
        {...rest}
      >
        {children}
      </select>
      <CaretDownIcon size={12} weight="bold" aria-hidden className="pointer-events-none absolute right-3 text-gray-500" />
    </span>
  )
}
