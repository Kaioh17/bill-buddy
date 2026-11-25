import { CheckIcon, XIcon } from '@phosphor-icons/react'
import type { Subscription } from '../../lib/api'
import { formatDay, money } from '../../lib/format'
import { FREQUENCY_UNIT } from '../../lib/subscriptions'
import { SectionHeader } from '../dashboard/Section'
import LabelChip from '../LabelChip'
import ServiceIcon from '../ServiceIcon'
import { Button, Card } from '../ui'

type Props = {
  items: Subscription[]
  busy?: string
  onConfirm: (id: string) => void
  onDismiss: (id: string) => void
}

/** Likely detections. They count nowhere until the user confirms them (FR 2a). */
export default function ReviewList({ items, busy, onConfirm, onDismiss }: Props) {
  return (
    <Card>
      <SectionHeader
        title="Needs your review"
        lede="These look like subscriptions, but one thing did not add up. They are not counted until you confirm them."
      />
      <ul className="mt-4">
        {items.map((s) => (
          <li key={s.id} className="flex flex-wrap items-center gap-x-5 gap-y-3 border-b border-gray-100 py-4 last:border-0">
            <div className="flex min-w-0 flex-1 basis-64 items-center gap-3">
              <ServiceIcon name={s.name} category={s.category} />
              <span className="min-w-0">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-medium">{s.name}</span>
                  <LabelChip kind="likely" />
                </span>
                <span className="mt-0.5 block text-xs text-gray-500">
                  {reason(s)} · {money(s.amount)} / {FREQUENCY_UNIT[s.frequency]}
                  {s.last_payment_date && <> · last paid {formatDay(s.last_payment_date)}</>}
                </span>
              </span>
            </div>
            <div className="flex gap-2">
              <Button disabled={busy === s.id} onClick={() => onConfirm(s.id)} aria-label={`Confirm ${s.name}`}>
                <CheckIcon size={16} aria-hidden />
                Confirm
              </Button>
              <Button variant="soft" disabled={busy === s.id} onClick={() => onDismiss(s.id)} aria-label={`Dismiss ${s.name}`}>
                <XIcon size={16} aria-hidden />
                Dismiss
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}

const reason = (s: Subscription) => {
  const text = s.likely_reasons.join(', ') || 'Not enough to be sure'
  return text.charAt(0).toUpperCase() + text.slice(1)
}
