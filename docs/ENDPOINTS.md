# Bill Buddy - Prototype Endpoint Plan

Source: docs/CHECKLIST.md.
Scope: prototype only.
Focus is overall functionality: Plaid sandbox onboarding, subscription detection, manual entry, reporting, then reminders and in-app notifications last.

## Summary

About 27 endpoints for the prototype.
4 already exist, so about 23 are new.
With the suggested cuts at the bottom, about 24 total and roughly 20 new.

## Already built (4)

| Method | Path |
|---|---|
| POST | `/auth/signup` |
| POST | `/auth/login` |
| GET | `/health/` |
| GET | `/health/me` |

## Plaid sandbox onboarding (6) [in progress]

| Method | Path | Purpose |
|---|---|---|
| POST | `/plaid/link-token` | Create the link token |
| POST | `/plaid/exchange` | Exchange the public token, save the account, run the first import |
| GET | `/accounts` | List linked accounts with last sync and `needs_reauth` |
| POST | `/accounts/{id}/sync` | Sync now, returns last sync time |
| DELETE | `/accounts/{id}` | Disconnect, optionally delete its transactions |
| POST | `/plaid/webhook` | Webhook that triggers an import |

For the sandbox, Plaid has `/sandbox/public_token/create`.
It makes a public token with no Link UI.
That lets `exchange` be tested from the API alone, so link-token can wait for the frontend.

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

- **Webhook and signature verification:** the sandbox can be driven by "Sync now" alone.
  This takes 1 endpoint off the Plaid group.
- **Merchant links:** the manual link flow is an edge case.
  Alias matching plus a Plaid entity ID is enough to demo detection.

