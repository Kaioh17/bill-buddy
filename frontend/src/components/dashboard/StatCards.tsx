import { ArrowRightIcon, RepeatIcon, TrendDownIcon, TrendUpIcon, WalletIcon } from '@phosphor-icons/react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { formatMonth, money } from '../../lib/format'
import { Card } from '../ui'
import { Skeleton, textLink } from './Section'

type StatProps = { label: string; icon: ReactNode; value?: string; caption: string; aside: ReactNode }

function Stat({ label, icon, value, caption, aside }: StatProps) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-sm font-medium text-gray-500">{label}</h2>
        <span className="text-secondary-600">{icon}</span>
      </div>
      <div className="mt-2 flex min-h-12 flex-wrap items-end justify-between gap-x-4 gap-y-2">
        {value === undefined ? (
          <Skeleton className="h-11 w-40" />
        ) : (
          <p className="text-[2.625rem] leading-none font-semibold tracking-tight">{value}</p>
        )}
        {aside}
      </div>
      <p className="mt-4 text-xs text-gray-500">{caption}</p>
    </Card>
  )
}

type MonthlySpendProps = {
  month: string
  isCurrent: boolean
  total?: number
  /** Percent against the previous month, null when there is nothing to compare with. */
  change: number | null
  previousMonth: string
}

export function MonthlySpend({ month, isCurrent, total, change, previousMonth }: MonthlySpendProps) {
  return (
    <Stat
      label="Monthly spend"
      icon={<WalletIcon size={20} aria-hidden />}
      value={total === undefined ? undefined : money(total)}
      caption={isCurrent ? `Estimated recurring spend for ${formatMonth(month)}` : `Recurring spend in ${formatMonth(month)}`}
      aside={change !== null && <Change percent={change} previousMonth={previousMonth} />}
    />
  )
}

function Change({ percent, previousMonth }: { percent: number; previousMonth: string }) {
  const rounded = Math.abs(percent).toFixed(1)
  const vs = `vs. ${formatMonth(previousMonth, 'long')}`
  const chip = 'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium'
  if (rounded === '0.0') return <p className={`${chip} bg-gray-100 text-gray-600`}>No change {vs}</p>

  const up = percent > 0
  const Trend = up ? TrendUpIcon : TrendDownIcon
  return (
    <p className={`${chip} ${up ? 'bg-[#f6f1e8] text-[#6e5530]' : 'bg-secondary-50 text-secondary-700'}`}>
      <Trend size={14} weight="bold" aria-hidden />
      <span>
        <span className="sr-only">{up ? 'Up' : 'Down'} </span>
        {rounded}% {vs}
      </span>
    </p>
  )
}

export function ActiveSubscriptions({ count }: { count?: number }) {
  return (
    <Stat
      label="Active subscriptions"
      icon={<RepeatIcon size={20} aria-hidden />}
      value={count === undefined ? undefined : String(count)}
      caption="Across your recurring bills and memberships"
      aside={
        <Link to="/subscriptions" className={textLink}>
          Manage subscriptions <ArrowRightIcon size={14} aria-hidden />
        </Link>
      }
    />
  )
}
