import { PlusIcon, SlidersHorizontalIcon } from '@phosphor-icons/react'
import { useState } from 'react'
import { LoadError } from '../components/dashboard/Section'
import PageHeader from '../components/PageHeader'
import ReconciliationCards from '../components/subscriptions/ReconciliationCards'
import ReviewList from '../components/subscriptions/ReviewList'
import SubscriptionRows from '../components/subscriptions/SubscriptionRows'
import { Alert, Button, ButtonLink, Card } from '../components/ui'
import {
  ApiError,
  confirmSubscription,
  dismissSubscription,
  getReconciliation,
  getSubscriptions,
  linkSandboxBank,
} from '../lib/api'
import { GENERIC_ERROR } from '../lib/form'
import { useApi } from '../lib/useApi'

export default function Subscriptions() {
  const subs = useApi(getSubscriptions)
  const recon = useApi(getReconciliation)
  const [busy, setBusy] = useState<string>()
  const [gone, setGone] = useState<ReadonlySet<string>>(new Set()) // hidden at once, the reload confirms
  const [actionError, setActionError] = useState<string>()

  /** Runs a confirm, dismiss or link, then reloads both lists (a confirm changes the comparison). */
  async function run(id: string, action: () => Promise<void>) {
    setBusy(id)
    setActionError(undefined)
    try {
      await action()
      if (id) setGone((g) => new Set(g).add(id))
      subs.retry()
      recon.retry()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : GENERIC_ERROR)
    } finally {
      setBusy(undefined)
    }
  }

  const all = subs.data?.filter((s) => !gone.has(s.id))
  const likely = all?.filter((s) => s.label === 'likely') ?? []
  const confirmed = all?.filter((s) => s.label !== 'likely')

  return (
    <div className="page">
      <title>Subscriptions - Bill Buddy</title>
      <PageHeader
        title="Subscriptions"
        lede="Recurring payments we found in your bank, and the ones you added yourself."
        actions={
          <>
            <ButtonLink to="/subscriptions/assumed" variant="soft">
              <SlidersHorizontalIcon size={16} aria-hidden />
              Edit my list
            </ButtonLink>
            <ButtonLink to="/subscriptions/new">
              <PlusIcon size={16} aria-hidden />
              Add subscription
            </ButtonLink>
          </>
        }
      />

      <div className="mt-7 grid gap-6">
        {actionError && <Alert tone="error">{actionError}</Alert>}

        {subs.error ? (
          <Card>
            <LoadError what="your subscriptions" message={subs.error} onRetry={subs.retry} />
          </Card>
        ) : (
          <>
            {likely.length > 0 && (
              <ReviewList
                items={likely}
                busy={busy}
                onConfirm={(id) => run(id, () => confirmSubscription(id))}
                onDismiss={(id) => run(id, () => dismissSubscription(id))}
              />
            )}
            <SubscriptionRows
              items={confirmed}
              empty={
                <>
                  <p>No subscriptions yet. Once a bank is linked we look for payments that repeat.</p>
                  {import.meta.env.DEV ? (
                    <Button className="mt-5" disabled={busy === ''} onClick={() => run('', linkSandboxBank)}>
                      {busy === '' ? 'Linking...' : 'Link the sandbox bank'}
                    </Button>
                  ) : (
                    <p className="mt-2">Bank linking is not available in this version yet.</p>
                  )}
                </>
              }
            />
          </>
        )}

        <ReconciliationCards data={recon.data} error={recon.error} onRetry={recon.retry} />
      </div>
    </div>
  )
}
