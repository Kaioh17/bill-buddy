import { ArrowRightIcon } from '@phosphor-icons/react'
import { Link } from 'react-router'
import { getUpcomingPayments } from '../../lib/api'
import { addDays, formatDay, money, relativeDay } from '../../lib/format'
import { useApi } from '../../lib/useApi'
import ServiceIcon from '../ServiceIcon'
import { Card } from '../ui'
import { Estimated, LoadError, SectionHeader, Skeleton, textLink } from './Section'

const SHOWN = 3
const WINDOW_DAYS = 30

export default function UpcomingPayments({ today }: { today: string }) {
  const { data, error, retry } = useApi(getUpcomingPayments)
  const next = data?.slice(0, SHOWN)

  return (
    <Card className="flex flex-col">
      <SectionHeader
        title="Upcoming payments"
        lede={
          next?.length
            ? `Your next ${next.length === 1 ? 'bill' : `${next.length} bills`} · next ${WINDOW_DAYS} days`
            : `Bills due in the next ${WINDOW_DAYS} days`
        }
        aside={
          <div className="flex flex-wrap gap-1.5">
            <span className="rounded-md bg-gray-50 px-2 py-1 text-[0.6875rem] whitespace-nowrap text-gray-500">
              {formatDay(today)} – {formatDay(addDays(today, WINDOW_DAYS))}
            </span>
            {!!next?.length && <Estimated />}
          </div>
        }
      />

      {error ? (
        <LoadError what="upcoming payments" message={error} onRetry={retry} />
      ) : next?.length === 0 ? (
        <p className="my-auto py-10 text-center text-sm text-gray-500">Nothing is due in the next {WINDOW_DAYS} days.</p>
      ) : (
        <ul className="mt-4" aria-busy={!next}>
          {next
            ? next.map((p) => (
                <li
                  key={`${p.subscription_id} ${p.date}`}
                  className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-x-3 border-b border-gray-100 py-3.5 sm:gap-x-5"
                >
                  <ServiceIcon name={p.name} category={p.category} />
                  <span className="min-w-0">
                    <span className="block truncate text-sm">{p.name}</span>
                    {/* The label never truncates, a long category does. */}
                    <span className="mt-0.5 flex gap-1 text-[0.6875rem] text-gray-500">
                      <span className="truncate">{p.category ?? 'Uncategorized'}</span>
                      {p.label === 'manual' && <span className="shrink-0">· Manual</span>}
                    </span>
                  </span>
                  <span className="min-w-16">
                    <span className="block text-[0.8125rem] font-medium">{formatDay(p.date)}</span>
                    <span className={`mt-0.5 block text-[0.6875rem] ${p.date === today ? 'text-secondary-600' : 'text-gray-500'}`}>
                      {relativeDay(p.date, today)}
                    </span>
                  </span>
                  <span className="min-w-14 text-right text-sm font-semibold tabular-nums">{money(p.amount)}</span>
                </li>
              ))
            : Array.from({ length: SHOWN }, (_, i) => (
                <li key={i} className="border-b border-gray-100 py-3.5">
                  <Skeleton className="h-9 w-full" />
                </li>
              ))}
        </ul>
      )}

      <div className="mt-auto flex flex-wrap justify-between gap-x-4 gap-y-2 pt-5">
        <Link to="/payments" className={textLink}>
          View payment schedule <ArrowRightIcon size={14} aria-hidden />
        </Link>
        <Link to="/payments?tab=past" className={textLink}>
          Payment history
        </Link>
      </div>
    </Card>
  )
}
