import type { ReactNode } from 'react'

/** Page title and lede, with optional actions on the right. */
export default function PageHeader({ title, lede, actions }: { title: string; lede: string; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-5">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-[2.125rem]">{title}</h1>
        <p className="mt-1.5 text-sm text-gray-500">{lede}</p>
      </div>
      {actions && <div className="flex flex-wrap gap-3 max-sm:w-full max-sm:*:flex-auto">{actions}</div>}
    </div>
  )
}
