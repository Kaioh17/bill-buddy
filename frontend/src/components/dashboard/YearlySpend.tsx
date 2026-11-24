import type { Dashboard } from '../../lib/api'
import { money, sumMoney } from '../../lib/format'
import { Card } from '../ui'
import { Estimated, LoadError, SectionHeader, Skeleton } from './Section'

type Props = { categories?: Dashboard['yearly_by_category']; error?: string; onRetry: () => void }

/** Projected yearly spend per category (FR 5b iii). */
export default function YearlySpend({ categories, error, onRetry }: Props) {
  const rows = categories?.toSorted((a, b) => Number(b.amount) - Number(a.amount))
  const largest = Number(rows?.[0]?.amount ?? 0)

  return (
    <Card>
      <SectionHeader
        title="Projected yearly spend"
        lede="What a year of your current subscriptions adds up to, by category"
        aside={<Estimated />}
      />
      {error ? (
        <LoadError what="your yearly projection" message={error} onRetry={onRetry} />
      ) : !rows ? (
        <Skeleton className="mt-5 h-32 w-full" />
      ) : (
        <div className="mt-5 grid gap-x-12 gap-y-6 md:grid-cols-[auto_1fr] md:items-center">
          <div className="md:min-w-48">
            <p className="text-3xl font-semibold tracking-tight">{money(sumMoney(rows.map((r) => r.amount)))}</p>
            <p className="mt-1.5 text-xs text-gray-500">Total per year</p>
          </div>
          {rows.length === 0 ? (
            <p className="text-sm text-gray-500">No categories yet. They show up with your first subscription.</p>
          ) : (
            <ul className="grid gap-3.5">
              {rows.map((r) => (
                <li
                  key={r.category ?? ''}
                  className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1.5 text-sm sm:grid-cols-[9rem_1fr_6rem]"
                >
                  <span className="truncate">{r.category ?? 'Uncategorized'}</span>
                  <span className="text-right font-semibold tabular-nums sm:order-last">{money(r.amount)}</span>
                  <span aria-hidden className="col-span-2 h-2 rounded-r bg-secondary-50 sm:col-span-1">
                    <span
                      className="block h-full rounded-r bg-secondary-600"
                      style={{ width: `${(Number(r.amount) / largest) * 100}%` }}
                    />
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  )
}
