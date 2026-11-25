import type { Subscription } from '../lib/api'

const CHIPS = {
  actual: { text: 'Actual', tone: 'bg-secondary-50 text-secondary-700' },
  likely: { text: 'Likely', tone: 'bg-amber-50 text-amber-800' },
  manual: { text: 'Manual', tone: 'bg-gray-100 text-gray-600' },
  assumed: { text: 'On your list', tone: 'bg-sky-50 text-sky-800' },
  unconfirmed: { text: 'Unconfirmed', tone: 'bg-amber-50 text-amber-800' },
} as const

/** Status chip. Text plus colour, so colour is never the only signal (WCAG 1.4.1). */
export default function LabelChip({ kind }: { kind: Subscription['label'] | 'assumed' | 'unconfirmed' }) {
  const { text, tone } = CHIPS[kind]
  return <span className={`rounded-md px-2 py-1 text-[0.6875rem] font-medium whitespace-nowrap ${tone}`}>{text}</span>
}
