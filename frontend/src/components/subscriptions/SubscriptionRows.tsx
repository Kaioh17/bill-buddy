import { WarningIcon } from '@phosphor-icons/react'
import type { Subscription } from '../../lib/api'
import { formatDay, money } from '../../lib/format'
import { FREQUENCY_UNIT } from '../../lib/subscriptions'
import { Estimated, SectionHeader, Skeleton } from '../dashboard/Section'
import LabelChip from '../LabelChip'
import ServiceIcon from '../ServiceIcon'
import { Card } from '../ui'

/** Active subscriptions, confirmed and manual, with a warning where two do the same job (FR 2c). */
export default function SubscriptionRows({ items, empty }: { items?: Subscription[]; empty: React.ReactNode }) {
  return (
    <Card>
      <SectionHeader
        title="Your subscriptions"
        lede={items ? `${items.length} active · next payment dates are estimates` : 'Loading your subscriptions'}
      />
      {items?.length === 0 ? (
        <div className="py-10 text-center text-sm text-gray-500">{empty}</div>
      ) : (
        <ul className="mt-4" aria-busy={!items}>
          {items
            ? items.map((s) => (
                <li key={s.id} className="border-b border-gray-100 py-4 last:border-0">
                  <div className="grid grid-cols-[auto_1fr_auto] items-center gap-x-3 sm:gap-x-5">
                    <ServiceIcon name={s.name} category={s.category} />
                    <span className="min-w-0">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="truncate text-sm font-medium">{s.name}</span>
                        <LabelChip kind={s.label} />
                        {s.on_assumed_list && <LabelChip kind="assumed" />}
                      </span>
                      <span className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-gray-500">
                        <span className="truncate">{s.category ?? 'Uncategorized'}</span>
                        <span aria-hidden>·</span>
                        <span>Expected {formatDay(s.next_expected_date)}</span>
                        <Estimated />
                      </span>
                    </span>
                    <span className="text-right">
                      <span className="block text-sm font-semibold tabular-nums">{money(s.amount)}</span>
                      <span className="block text-xs text-gray-500">per {FREQUENCY_UNIT[s.frequency]}</span>
                    </span>
                  </div>
                  {s.similar_to.length > 0 && (
                    <p className="mt-3 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
                      <WarningIcon size={16} aria-hidden className="mt-px shrink-0" />
                      <span>
                        Similar to {list(s.similar_to)}. You may be paying for {s.service_type?.toLowerCase() ?? 'the same service'}{' '}
                        twice.
                      </span>
                    </p>
                  )}
                </li>
              ))
            : [0, 1, 2].map((i) => (
                <li key={i} className="border-b border-gray-100 py-4">
                  <Skeleton className="h-9 w-full" />
                </li>
              ))}
        </ul>
      )}
    </Card>
  )
}

const list = (names: string[]) => new Intl.ListFormat('en-US').format(names)
