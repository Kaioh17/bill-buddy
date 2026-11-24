import { useState } from 'react'
import { formatMonth, money, moneyRounded } from '../../lib/format'
import { axisTicks, monthsEnding, type MonthSpend } from '../../lib/spending'
import Select from '../Select'
import { ButtonLink, Card } from '../ui'
import { LoadError, SectionHeader, Skeleton } from './Section'

const RANGES = [3, 6, 12]

// Manual spend keeps the hue of its bar and is set apart by a hatch and a 2px gap.
const fill = {
  on: 'bg-secondary-600',
  off: 'bg-secondary-200 group-hover:bg-[#a5cbc1]',
}
const hatch = {
  on: 'bg-[repeating-linear-gradient(45deg,var(--color-secondary-600)_0_3px,#6fb0a7_3px_6px)]',
  off: 'bg-[repeating-linear-gradient(45deg,var(--color-secondary-200)_0_3px,var(--color-secondary-50)_3px_6px)]',
}

type Props = { months?: MonthSpend[]; endMonth: string; error?: string; onRetry: () => void }

export default function SpendingChart({ months, endMonth, error, onRetry }: Props) {
  const [range, setRange] = useState(6)
  const shown = months && monthsEnding(months, endMonth, range)
  const isEmpty = shown?.every((m) => m.total === 0)
  const isNew = months?.every((m) => m.total === 0)

  return (
    <Card className="flex flex-col">
      <SectionHeader
        title="Monthly spending"
        lede="A little perspective on your recurring costs"
        aside={
          <Select compact label="Chart period" value={range} onChange={(e) => setRange(Number(e.target.value))}>
            {RANGES.map((n) => (
              <option key={n} value={n}>
                Last {n} months
              </option>
            ))}
          </Select>
        }
      />
      {error ? (
        <LoadError what="your spending" message={error} onRetry={onRetry} />
      ) : !shown ? (
        <Skeleton className="mt-6 h-56 w-full" />
      ) : isEmpty ? (
        <div className="my-auto grid justify-items-center gap-4 py-10 text-center">
          <p className="max-w-xs text-sm text-gray-500">
            {isNew
              ? 'No spending to show yet. Add a subscription and your monthly costs appear here.'
              : 'No spending in this period. Pick a later month to see more.'}
          </p>
          {isNew && (
            <ButtonLink to="/subscriptions/new" variant="soft">
              Add your first subscription
            </ButtonLink>
          )}
        </div>
      ) : (
        // Remounting on a new end month puts the selection back on that month's bar.
        <Plot key={endMonth} months={shown} endMonth={endMonth} />
      )}
    </Card>
  )
}

function Plot({ months, endMonth }: { months: MonthSpend[]; endMonth: string }) {
  const [picked, setPicked] = useState(endMonth)
  const [hovered, setHovered] = useState<string>()

  // A picked bar can drop out of view when the range gets shorter.
  const selected = months.find((m) => m.month === picked) ?? months[months.length - 1]
  const ticks = axisTicks(Math.max(...months.map((m) => m.total)))
  const top = ticks[ticks.length - 1]
  const hasManual = months.some((m) => m.manual > 0)
  const crowded = months.length > 6 // value labels no longer fit on a phone

  return (
    <>
      <div
        role="group"
        aria-label="Spending per month. Choose a month to see its total."
        // The bleed keeps twelve bars at least 24px wide on a phone.
        className={`relative mt-9 h-48 pl-9 sm:pl-12 ${crowded ? 'max-sm:-mr-3' : ''}`}
        onKeyDown={(e) => e.key === 'Escape' && setHovered(undefined)}
      >
        {/* Grid and axis. The bottom 1.5rem is the month labels. */}
        <div aria-hidden className="absolute inset-x-0 top-0 bottom-6">
          {ticks.map((t) => (
            <div key={t} className="absolute inset-x-0 flex h-0 items-center" style={{ bottom: `${(t / top) * 100}%` }}>
              <span className="absolute left-0 text-[0.6875rem] leading-none text-gray-500 tabular-nums">
                {Number.isInteger(t) ? moneyRounded(t) : money(t)}
              </span>
              <span className="ml-9 h-px flex-1 bg-gray-100 sm:ml-12" />
            </div>
          ))}
        </div>

        <div className="relative flex h-full">
          {months.map((m, i) => {
            const isOn = m.month === selected.month
            const state = isOn ? 'on' : 'off'
            const label = formatMonth(m.month)
            return (
              <div key={m.month} className="group relative flex h-full min-w-0 flex-1 flex-col items-center">
                {/* The whole column is the target. What it draws is hidden, this is its name. */}
                <button
                  type="button"
                  aria-pressed={isOn}
                  aria-label={
                    `${label}: ${money(m.total)}` +
                    (m.manual > 0 ? `, ${money(m.confirmed)} bank payments and ${money(m.manual)} manual` : '')
                  }
                  onClick={() => setPicked(m.month)}
                  onPointerEnter={() => setHovered(m.month)}
                  onPointerLeave={() => setHovered(undefined)}
                  onFocus={(e) => e.currentTarget.matches(':focus-visible') && setHovered(m.month)}
                  onBlur={() => setHovered(undefined)}
                  className="absolute inset-0 z-1 cursor-pointer rounded-lg"
                />
                {/* Fixed plot height, so the bars' percentages resolve against it. */}
                <span aria-hidden className="relative block h-[calc(100%-1.5rem)] w-full">
                  <span className="absolute inset-x-0 bottom-0 mx-auto w-[72%] max-w-11" style={{ height: `${(m.total / top) * 100}%` }}>
                    <span className="flex h-full flex-col gap-0.5">
                      {m.manual > 0 && <span className={`block rounded-t ${hatch[state]}`} style={{ flexGrow: m.manual }} />}
                      {m.confirmed > 0 && (
                        <span
                          className={`block transition-colors ${m.manual > 0 ? '' : 'rounded-t'} ${fill[state]}`}
                          style={{ flexGrow: m.confirmed }}
                        />
                      )}
                    </span>
                    <span
                      className={`absolute bottom-full left-1/2 mb-1.5 -translate-x-1/2 text-[0.6875rem] leading-none tabular-nums ${
                        isOn ? 'font-medium text-gray-900' : 'text-gray-500'
                      } ${crowded ? 'max-sm:hidden' : ''}`}
                    >
                      {moneyRounded(m.total)}
                    </span>
                  </span>
                </span>
                <span aria-hidden className={`flex h-6 items-end text-xs leading-none ${isOn ? 'font-semibold text-secondary-700' : 'text-gray-500'}`}>
                  <span className={crowded ? 'max-sm:hidden' : ''}>{formatMonth(m.month, 'short')}</span>
                  {crowded && <span className="sm:hidden">{formatMonth(m.month, 'narrow')}</span>}
                </span>
                {hovered === m.month && <Tooltip spend={m} label={label} side={i < months.length / 2 ? 'left' : 'right'} />}
              </div>
            )
          })}
        </div>
      </div>

      <div className="mt-auto flex flex-wrap items-center justify-between gap-x-6 gap-y-2 pt-6 text-xs">
        <p aria-live="polite" className="flex items-center gap-2">
          <span aria-hidden className="size-2 rounded-xs bg-secondary-600" />
          <span className="text-gray-500">{formatMonth(selected.month)}</span>
          <span className="font-medium">{money(selected.total)}</span>
        </p>
        {hasManual && (
          <ul aria-label="Legend" className="flex gap-4 text-gray-500">
            <li className="flex items-center gap-1.5">
              <span aria-hidden className="size-3 rounded-xs bg-secondary-600" /> Bank payments
            </li>
            <li className="flex items-center gap-1.5">
              <span aria-hidden className={`size-3 rounded-xs ${hatch.on}`} /> Manual
            </li>
          </ul>
        )}
      </div>

      {/* Text alternative to the chart (NFR 5). A bare sr-only table still takes up width. */}
      <div className="sr-only">
        <table>
          <caption>Monthly spending</caption>
          <thead>
            <tr>
              <th scope="col">Month</th>
              <th scope="col">Bank payments</th>
              <th scope="col">Manual</th>
              <th scope="col">Total</th>
            </tr>
          </thead>
          <tbody>
            {months.map((m) => (
              <tr key={m.month}>
                <th scope="row">{formatMonth(m.month)}</th>
                <td>{money(m.confirmed)}</td>
                <td>{money(m.manual)}</td>
                <td>{money(m.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

/** Repeats the bar's accessible name, so it is hidden from screen readers. */
function Tooltip({ spend, label, side }: { spend: MonthSpend; label: string; side: 'left' | 'right' }) {
  return (
    <span
      aria-hidden
      className={`pointer-events-none absolute bottom-full z-10 mb-1 grid gap-1 rounded-lg border border-gray-200 bg-primary px-3 py-2 text-left text-xs whitespace-nowrap shadow-float ${
        // Starts at the bar, and opens inward so it stays on the page.
        side === 'left' ? 'left-[calc(50%-1.5rem)]' : 'right-[calc(50%-1.5rem)]'
      }`}
    >
      <span className="text-gray-500">{label}</span>
      <span className="text-sm font-semibold">{money(spend.total)}</span>
      {spend.manual > 0 && (
        <>
          <span className="text-gray-500">
            <span className="font-medium text-gray-900">{money(spend.confirmed)}</span> bank payments
          </span>
          <span className="text-gray-500">
            <span className="font-medium text-gray-900">{money(spend.manual)}</span> manual
          </span>
        </>
      )}
    </span>
  )
}
