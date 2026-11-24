import type { ReactNode } from 'react'
import { Alert, Button } from '../ui'

/** Gray placeholder while data loads. Size it with a class. */
export function Skeleton({ className }: { className: string }) {
  return <span aria-hidden className={`block animate-pulse rounded-lg bg-gray-100 ${className}`} />
}

/** Marks projected figures, which must never pass for confirmed payments (NFR 6). */
export function Estimated() {
  return <span className="rounded-md bg-gray-50 px-2 py-1 text-[0.6875rem] whitespace-nowrap text-gray-500">Estimated</span>
}

export function LoadError({ what, message, onRetry }: { what: string; message: string; onRetry: () => void }) {
  return (
    <div className="mt-5 grid justify-items-start gap-3">
      <Alert tone="error">
        Could not load {what}. {message}
      </Alert>
      <Button variant="soft" onClick={onRetry}>
        Try again
      </Button>
    </div>
  )
}

export function SectionHeader({ title, lede, aside }: { title: string; lede: string; aside?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <p className="mt-1 text-xs text-gray-500">{lede}</p>
      </div>
      {aside}
    </div>
  )
}

/** Teal link with an optional trailing icon. */
export const textLink =
  'inline-flex items-center gap-2 rounded-md text-[0.8125rem] font-medium text-secondary-600 underline-offset-4 hover:text-secondary-700 hover:underline'
