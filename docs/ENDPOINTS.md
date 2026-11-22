# Bill Buddy - Prototype Endpoint Plan

Source: docs/CHECKLIST.md.
Scope: prototype only.
Focus is overall functionality: Plaid sandbox onboarding, subscription detection, manual entry, reporting, then reminders and in-app notifications last.

## Summary

About 29 endpoints for the prototype.
11 are built and tested: 4 auth and health, 7 Plaid onboarding.
18 are still open: 7 detection, 3 manual, 4 reporting, 4 notifications.
With the suggested cuts at the bottom (merchant links, and the month payments route), the open count drops to about 16.

## Already built (4)

| Method | Path |
|---|---|
| POST | `/auth/signup` |
| POST | `/auth/login` |
| GET | `/health/` |
| GET | `/health/me` |

## Plaid sandbox onboarding (7) [done]

| Method | Path | Purpose |
|---|---|---|
| POST | `/plaid/link-token` | Create the link token |
| POST | `/plaid/exchange` | Exchange the public token, save the account, run the first import |
| GET | `/accounts` | List linked accounts with last sync and `needs_reauth` |
| POST | `/accounts/{id}/sync` | Sync now, returns last sync time |
| DELETE | `/accounts/{id}` | Disconnect, optionally delete its transactions |
| POST | `/plaid/webhook` | Webhook that triggers an import, signature verified |
| POST | `/plaid/sandbox-link` | Dev only, 404 outside the sandbox: links Plaid's test bank with no Link UI |

All 7 are built with tests written first.
`/plaid/sandbox-link` was added so the flow can be tested from Swagger without the frontend.
The sandbox test user is set in `SANDBOX_USER` in `app/core/plaid.py`.
Not built yet: the reconnect flow for `needs_reauth` (Plaid update mode), the 15 minute scheduler, and the user notice when retries run out.

## Subscription detection and the assumed list (7) [open]

| Method | Path | Purpose |
|---|---|---|
| GET | `/subscriptions` | Active and LIKELY items with labels and similar-service flags |
| POST | `/subscriptions/{id}/confirm` | Confirm a LIKELY item |
| POST | `/subscriptions/{id}/dismiss` | Dismiss a LIKELY item, writes to `dismissed_subscriptions` |
| GET | `/catalog` | Catalog entries for the picker |
| PUT | `/assumed` | Save the catalog selection |
| GET | `/reconciliation` | Unexpected and unconfirmed in one response |
| POST | `/merchant-links` | Manually link a merchant to an assumed item |

Detection itself needs no endpoint, because it runs after each import.
A dev-only `POST /detect` is possible for manual testing, but is not planned.

## Manual subscriptions (3) [open]

| Method | Path |
|---|---|
| POST | `/subscriptions/manual` |
| PUT | `/subscriptions/manual/{id}` |
| DELETE | `/subscriptions/manual/{id}` |

These could share the `/subscriptions` list endpoint.
Manual rows would just carry a `manual` label.

## Reporting (4) [open]

| Method | Path | Purpose |
|---|---|---|
| GET | `/dashboard?from=&to=` | Monthly bars with a manual segment, total monthly spend, yearly projection per category, active count |
| GET | `/payments/past` | Last 12 months, sortable |
| GET | `/payments/upcoming` | Next 30 days, marked "estimated" |
| GET | `/payments/month/{yyyy-mm}` | What opens when a bar is clicked |

The last one could be dropped, since `/payments/past?month=` covers it.
That brings this group to 3.

## In-app notifications, built last (4) [open]

| Method | Path | Purpose |
|---|---|---|
| GET | `/notifications` | List, including sync-failure and stale-data notices |
| POST | `/notifications/{id}/read` | Mark one as read |
| GET | `/preferences/reminders` | Read lead times |
| PUT | `/preferences/reminders` | Set lead times, such as 1, 3, 7 days |


## we will need
- A scheduler for the 15-minute sync pickup and the reminder check.
  Use APScheduler or a plain asyncio loop in the app lifespan, not a worker and queue.
- The yearly detection job, which is internal.
- Reminder generation, which writes rows into the notifications table.

## Suggested cuts since this is a prototype

- **Merchant links:** the manual link flow is an edge case.
  Alias matching plus a Plaid entity ID is enough to demo detection.

