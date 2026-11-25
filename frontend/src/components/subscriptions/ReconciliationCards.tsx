import { Link } from 'react-router'
import type { Reconciliation } from '../../lib/api'
import { formatDay, money } from '../../lib/format'
import { LoadError, SectionHeader, Skeleton, textLink } from '../dashboard/Section'
import { Card } from '../ui'
import LabelChip from '../LabelChip'

type Props = { data?: Reconciliation; error?: string; onRetry: () => void }

/** Your list compared with your bank: what you did not expect, and what has gone quiet (FR 3). */
export default function ReconciliationCards({ data, error, onRetry }: Props) {
  if (error)
    return (
      <Card>
        <SectionHeader title="Your list and your bank" lede="Compared against the services you said you pay for." />
        <LoadError what="the comparison" message={error} onRetry={onRetry} />
      </Card>
    )

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <SectionHeader title="Not on your list" lede="Recurring payments in your bank that you did not tell us about." />
        {data ? (
          data.unexpected.length ? (
            <ul className="mt-4">
              {data.unexpected.map((u) => (
                <Row key={u.subscription_id} name={u.name} date={u.last_payment_date} amount={u.amount} />
              ))}
            </ul>
          ) : (
            <p className="py-8 text-center text-sm text-gray-500">Nothing unexpected. Every subscription we found is on your list.</p>
          )
        ) : (
          <Skeleton className="mt-4 h-24 w-full" />
        )}
      </Card>

      <Card>
        <SectionHeader title="Not seen recently" lede="On your list, but no payment in the last 60 days." />
        {data ? (
          data.unconfirmed.length ? (
            <ul className="mt-4">
              {data.unconfirmed.map((u) => (
                <Row key={u.catalog_entry_id} name={u.name} date={u.last_payment_date} amount={u.amount} chip />
              ))}
            </ul>
          ) : (
            <p className="py-8 text-center text-sm text-gray-500">
              Nothing missing. <Link to="/subscriptions/assumed" className={textLink}>Edit your list</Link>
            </p>
          )
        ) : (
          <Skeleton className="mt-4 h-24 w-full" />
        )}
      </Card>
    </div>
  )
}

function Row({ name, date, amount, chip = false }: { name: string; date: string | null; amount: string | null; chip?: boolean }) {
  return (
    <li className="flex items-center justify-between gap-4 border-b border-gray-100 py-3.5 last:border-0">
      <span className="min-w-0">
        <span className="flex flex-wrap items-center gap-2">
          <span className="truncate text-sm font-medium">{name}</span>
          {chip && <LabelChip kind="unconfirmed" />}
        </span>
        <span className="mt-0.5 block text-xs text-gray-500">
          {date ? `Last payment ${formatDay(date)}` : 'No payment found'}
        </span>
      </span>
      {amount && <span className="text-sm font-semibold tabular-nums">{money(amount)}</span>}
    </li>
  )
}
