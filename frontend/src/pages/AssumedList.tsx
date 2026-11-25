import { useState } from 'react'
import { useNavigate } from 'react-router'
import { LoadError } from '../components/dashboard/Section'
import PageHeader from '../components/PageHeader'
import { Alert, Button, ButtonLink, Card } from '../components/ui'
import { ApiError, getCatalog, saveAssumed, type CatalogEntry } from '../lib/api'
import { GENERIC_ERROR } from '../lib/form'
import { useApi } from '../lib/useApi'

/** Pick the services you expect to pay for. Matched against your bank to find gaps (FR 2b, FR 3). */
export default function AssumedList() {
  const { data, error, retry } = useApi(getCatalog)

  return (
    <div className="page">
      <title>My list - Bill Buddy</title>
      <PageHeader
        title="My list"
        lede="Choose the services you expect to pay for. We compare them with your bank and flag anything missing or unexpected."
      />
      <Card className="mt-7">
        {error ? (
          <LoadError what="the service list" message={error} onRetry={retry} />
        ) : data ? (
          <Picker entries={data} />
        ) : (
          <p className="text-sm text-gray-500" role="status">
            Loading services...
          </p>
        )}
      </Card>
    </div>
  )
}

function Picker({ entries }: { entries: CatalogEntry[] }) {
  const navigate = useNavigate()
  const [chosen, setChosen] = useState(() => new Set(entries.filter((e) => e.selected).map((e) => e.id)))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string>()

  // Same kind of service side by side, so two music apps are easy to spot.
  const byType = new Map<string, CatalogEntry[]>()
  for (const e of entries) byType.set(e.service_type, [...(byType.get(e.service_type) ?? []), e])
  const groups = [...byType].sort(([a], [b]) => a.localeCompare(b))

  function toggle(id: string) {
    setChosen((c) => {
      const next = new Set(c)
      if (!next.delete(id)) next.add(id)
      return next
    })
  }

  async function save(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(undefined)
    try {
      await saveAssumed([...chosen])
      navigate('/subscriptions')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : GENERIC_ERROR)
      setSaving(false)
    }
  }

  return (
    <form onSubmit={save} className="grid gap-6">
      {groups.map(([type, items]) => (
        <fieldset key={type}>
          <legend className="text-sm font-semibold">{type}</legend>
          <div className="mt-2 grid gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((e) => (
              <label key={e.id} className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg px-1 text-sm hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={chosen.has(e.id)}
                  onChange={() => toggle(e.id)}
                  className="size-5 accent-secondary-600"
                />
                {e.name}
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      {error && <Alert tone="error">{error}</Alert>}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={saving}>
          {saving ? 'Saving...' : `Save ${chosen.size} ${chosen.size === 1 ? 'service' : 'services'}`}
        </Button>
        <ButtonLink to="/subscriptions" variant="soft">
          Cancel
        </ButtonLink>
      </div>
    </form>
  )
}
