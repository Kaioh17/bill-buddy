import { CalendarDotsIcon, PlusIcon } from '@phosphor-icons/react'
import { useState } from 'react'
import { LoadError } from '../components/dashboard/Section'
import SpendingChart from '../components/dashboard/SpendingChart'
import { ActiveSubscriptions, MonthlySpend } from '../components/dashboard/StatCards'
import UpcomingPayments from '../components/dashboard/UpcomingPayments'
import YearlySpend from '../components/dashboard/YearlySpend'
import PageHeader from '../components/PageHeader'
import Select from '../components/Select'
import { ButtonLink, Card } from '../components/ui'
import { getDashboard } from '../lib/api'
import { addMonths, formatMonth, toDay, toMonth } from '../lib/format'
import { percentChange, toMonthSpend } from '../lib/spending'
import { useApi } from '../lib/useApi'

// The backend keeps 12 months. Loading them all once makes the pickers instant.
const HISTORY_MONTHS = 12

function loadDashboard() {
  const current = toMonth(new Date())
  return getDashboard(addMonths(current, 1 - HISTORY_MONTHS), current)
}

export default function Dashboard() {
  const { data, error, retry } = useApi(loadDashboard)
  const [today] = useState(() => toDay(new Date()))
  const currentMonth = today.slice(0, 7)
  const [month, setMonth] = useState(currentMonth)

  const isCurrent = month === currentMonth
  const previousMonth = addMonths(month, -1)
  const months = data?.months.map(toMonthSpend)
  const spendIn = (m: string) => months?.find((x) => x.month === m)?.total
  // The current month is not over, so it shows the projection rather than payments so far.
  const total = data && (isCurrent ? Number(data.total_monthly_spend) : (spendIn(month) ?? 0))
  const change = total === undefined ? null : percentChange(total, spendIn(previousMonth))

  return (
    <div className="page">
      <title>Dashboard - Bill Buddy</title>
      <PageHeader
        title="Dashboard"
        lede={`Your bills, in one clear view. Here\u2019s how ${formatMonth(month, 'long')} ${isCurrent ? 'is looking' : 'looked'}.`}
        actions={
          <>
            <Select label="Month" icon={<CalendarDotsIcon size={18} aria-hidden />} value={month} onChange={(e) => setMonth(e.target.value)}>
              {Array.from({ length: HISTORY_MONTHS }, (_, ago) => addMonths(currentMonth, -ago)).map((m) => (
                <option key={m} value={m}>
                  {formatMonth(m)}
                </option>
              ))}
            </Select>
            <ButtonLink to="/subscriptions/new">
              <PlusIcon size={16} aria-hidden />
              Add subscription
            </ButtonLink>
          </>
        }
      />

      <div className="mt-7 grid gap-6 md:grid-cols-2">
        {error ? (
          <Card className="md:col-span-2">
            <h2 className="text-sm font-medium text-gray-500">Overview</h2>
            <LoadError what="your totals" message={error} onRetry={retry} />
          </Card>
        ) : (
          <>
            <MonthlySpend month={month} isCurrent={isCurrent} total={total} change={change} previousMonth={previousMonth} />
            <ActiveSubscriptions count={data?.active_count} />
          </>
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,49fr)_minmax(0,79fr)]">
        <UpcomingPayments today={today} />
        <SpendingChart months={months} endMonth={month} error={error} onRetry={retry} />
      </div>

      <div className="mt-6">
        <YearlySpend categories={data?.yearly_by_category} error={error} onRetry={retry} />
      </div>
    </div>
  )
}
