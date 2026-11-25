# Bill Buddy - Build Checklist

Source: Analysis Report, Design Report, Test Plan (docs/).
FR = functional requirement, NFR = non-functional requirement, TC = test case.

## Backend and logic

### Foundation
- [x] FastAPI app, health route, uv/ruff/pytest setup
- [x] Async SQLAlchemy engine and session (`db/database.py`)
- [x] Models for all 9 tables plus enums (`app/models/`)
- [x] Register `matched_payments` in `app/main.py` model imports
- [ ] Rename `merchnant_links.py` typo
- [ ] Add migrations (Alembic is not installed yet)
- [ ] Add notification preference storage on users (design says users hold it, model has none)
- [x] Config module: Plaid keys, encryption key, session timeout (15 min), detection thresholds (gap ranges, amount change, date drift)
  - Detection thresholds are constants at the top of `app/services/detection.py` (`RULES`, `AMOUNT_TOLERANCE`), not environment settings.
- [x] Seed script for `catalog_entries` (about 20 services, a few sharing a service_type)
  - `db/seed_catalog.py`, 22 services, safe to re-run, also run by `db.init_db`. Plaid merchant entity IDs are empty until real ones are known.
- [x] Test database and a way to fake "today" (needed for 59/60/61 and day 30/31 tests)

### Auth and security (NFR 1)
- [x] Register and login with bcrypt or argon2 password hashing
- [x] Session token on every request, 15 min inactivity expiry (TC-16)
- [x] `current_user` dependency, every query filtered by the session user ID, never a request ID (TC-17)
- [x] Encrypt Plaid access token before saving
- [x] Verify signature on every Plaid webhook
- [ ] HTTPS only, secrets from env or secret store

### Plaid integration (FR 1)
- [x] One Plaid module that wraps all calls, API version pinned in config
- [x] Create link token (transactions product, 24 months requested)
- [x] Exchange public token, save linked account with encrypted token (FR 1a, TC-01)
- [ ] Handle cancelled link: nothing saved, clear message (TC-04)
  - Backend saves nothing until `/plaid/exchange` is called. The message is a frontend task.
- [x] `importAccount`: fetch changes by cursor, one DB transaction, skip pending and older than 12 months, skip duplicates by `transaction_id`, apply modified and removed, save cursor last (FR 1b, TC-02, TC-18)
- [x] Rollback on error, keep old data and old cursor (TC-19)
- [ ] Retry temporary errors 3 times (15 min, 1 hr, 4 hr) via `next_sync`, then notify user and retry in 24 hr
  - Backoff and 24 hr retry are done, the user notice waits for in-app notifications.
- [ ] Do not retry permanent errors (expired login): set `needs_reauth`, ask user to reconnect
  - `needs_reauth` is set and sync is refused. The reconnect flow (Plaid update mode) is not built yet.
- [x] Per-account lock so two imports never run at once
- [ ] Scheduled sync: cron every 15 min picks accounts where `next_sync` has passed (FR 1c)
- [x] "Sync now" endpoint, returns last sync time (TC-03)
- [x] Webhook endpoint that triggers an import
- [x] Disconnect account: revoke token, delete that account's transactions on request (NFR 2)

### Subscription detection (FR 2)
- [x] `detectSubscriptions` after each import for WEEKLY and MONTHLY (3 charges minimum, TC-05, TC-06)
- [ ] Yearly detection as a one-time background job per account, 2 charges gives LIKELY, resumable via `yearly_check_status`
  - The scoring is done and `detect_subscriptions` accepts `YEARLY`.
  - The job is not built: it must pull 24 months from Plaid, and the importer stores only 12.
- [x] `scoreSeries`: ACTUAL, LIKELY (one unmet rule, with `likely_reasons`), or none
- [x] Only eligible charges: money out, not pending, not an excluded category
  - Excluded Plaid categories: `TRANSFER_IN`, `TRANSFER_OUT`, `INCOME`, `BANK_FEES`.
- [x] Save matched payments on detection, no duplicates (FR 4c)
  - A payment whose transaction Plaid later removes is kept, there is no FK on purpose. Past payments (reporting) should decide whether to hide those.
- [x] Confirm and dismiss LIKELY items, use `dismissed_subscriptions` so they are not suggested again
  - A confirmed item is never demoted back to LIKELY by a later detection run.
- [x] Assumed list: save catalog selection, ignore unknown IDs (FR 2b, TC-07)
- [ ] Merchant to catalog matching: user link, then Plaid entity ID, then alias in name
  - Entity ID then alias is done (`app/services/catalog.py`), and an entity ID match beats an alias match.
  - The user link step waits for the merchant links route, which is cut for the prototype.
- [ ] Manual link of an unmatched merchant to an assumed item, remembered in `merchant_links`
- [x] Flag 2 or more active subscriptions with the same `service_type` (FR 2c, TC-08)
  - Only ACTUAL items count. Returned as `similar_to` on each subscription.

### Reconciliation (FR 3)
- [x] Unexpected: ACTUAL and active, matches nothing on assumed list (TC-09)
  - Needs `subscriptions.catalog_entry_id`, set at detection time. A detected service with no catalog match is always unexpected.
- [x] Unconfirmed: assumed item with no matching bank payment in last 60 days, exactly 60 counts as paid, 61 does not (TC-10)
- [x] Each item returns service name, last payment date, amount

### Manual subscriptions (FR 4)
- [ ] Validation: name required, amount greater than 0, frequency in WEEKLY/MONTHLY/YEARLY, next date today or later (TC-12)
- [ ] Add, edit, delete endpoints scoped to the user (TC-11)
- [ ] Sync never touches manual rows
- [ ] Manual rows carry a "manual" label through to tables and totals

### Reporting (FR 5)
- [ ] Past payments: last 12 months, confirmed only, sort by date or amount (TC-13)
- [ ] Upcoming payments: next 30 days, day 30 included and day 31 not, marked "estimated" (TC-14)
- [ ] Dashboard: monthly bar chart data for a chosen period with manual as its own segment, total monthly spend, projected yearly spend per category, active count (TC-15 for the empty case)
- [ ] `monthlyCost`: weekly x 52 / 12, monthly as is, yearly / 12
- [ ] Sum totals in SQL with an index on user and date, money as Decimal (TC-21)
- [ ] LIKELY items excluded from all counts and totals until confirmed

### Reminders and notifications (NFR 7)
- [ ] Create or update reminders when a subscription is saved or its date changes, cancel on delete
- [ ] Unique key of subscription, due date and lead days so each is sent once
- [ ] User sets one or more lead times (for example 1, 3, 7 days)
- [ ] Scheduler runs every minute, hands due reminders to the delivery service, sets `sent_at` (TC-20)
- [ ] Pick a delivery channel (email is the simplest, the docs do not say)
- [ ] Notify user when sync fails or data may be stale
- [ ] Log failed deliveries so they can be retried without duplicates

### Cross-cutting
- [ ] Pydantic schemas in `app/schema/`
  - Done for auth, plaid, accounts, subscriptions, catalog, reconciliation and the shared envelope. The rest come with their routes.
- [x] Logging of sync failures and errors with user ID, account ID, error
  - Covers imports (`sync_failed`, `import_crashed`), Plaid calls (`plaid_error`) and detection (`detection_ok`, `detection_failed`). Add the same for reminders when they exist.
- [ ] Background worker and queue for syncs and the yearly job
- [ ] Daily DB backups with point-in-time recovery, restore tested before launch (infra)
- [ ] Pytest for every TC that can be automated, Plaid sandbox only, mocked Plaid for load tests
  - Plaid onboarding, detection and reconciliation are covered (285 tests, FakePlaid, in-memory SQLite). Reporting and reminders are open.

## Frontend

### Setup
- [ ] Choose framework and set up the project (no frontend folder exists yet)
- [ ] API client with session handling, redirect to login on 401 or timeout (TC-16)
- [ ] Shared components, one date and currency format everywhere
- [x] Label chip component: actual, assumed, unconfirmed, likely, manual (text plus color)
  - `components/LabelChip.tsx`.
- [ ] Error and warning messages that say what happened and what to do, for example "Sync failed. Your data may be out of date. Try sync now."

### Screens
- [ ] Register and login
- [ ] Nav bar with Dashboard, Subscriptions, Payments, reachable from every page
- [ ] Link bank account: Plaid Link, cancel message with retry (TC-01, TC-04)
  - Not built. In `npm run dev` only, the empty Subscriptions page has a button that links Plaid's sandbox bank and syncs once.
  - Plaid's sandbox sends one month on the first pull and the rest on the second, so a single sync finds no recurring payments.
- [ ] Linked accounts list with institution, last sync time, "Sync now", disconnect, reconnect when `needs_reauth`
- [ ] Privacy info: what is collected, why, how long kept
- [ ] Dashboard: total monthly spend, active count, upcoming payments, interactive bar chart with period picker, click a bar to list that month, projected yearly spend per category, empty state with $0.00 (TC-15)
- [ ] Subscriptions page: list with labels, warnings, similar-subscription flags, confirm or dismiss LIKELY items, add and edit entry points
  - The list, labels, similar flags, and confirm and dismiss are done (`pages/Subscriptions.tsx`).
  - "Add subscription" opens a placeholder, and there is no edit entry point yet. Both wait for the manual group.
- [x] Assumed list picker from the catalog
  - `pages/AssumedList.tsx` at `/subscriptions/assumed`, grouped by service type.
- [x] Unexpected and unconfirmed report with name, last payment date, amount
  - Shown at the bottom of the Subscriptions page.
- [ ] Add and edit manual subscription form with inline validation errors, save and cancel (TC-11, TC-12)
- [ ] Payments page: Upcoming (30 days, "estimated") and Past tabs, sortable by date and amount (TC-13, TC-14)
- [ ] Notification preferences: lead times, multiple reminders

### Quality
- [ ] WCAG 2.1 AA: keyboard-only navigation, visible focus, text alternative for charts, contrast (TC-22)
- [ ] Dashboard under 3 s, tables under 2 s (TC-21)
- [ ] Works on current Chrome, Firefox, Brave, desktop and mobile
- [ ] Playwright tests for main flows, keyboard nav, and session timeout

## Doc inconsistencies to settle
- Design report, Notification Delivery Failure: says Bill Buddy "will not record" failures in logs, which contradicts NFR 9 and the logging section.
- Analysis says import 12 months, design requests 24 months from Plaid and stores 12.
That is intentional (24 for yearly detection, 12 stored), but the Analysis wording should match.
- Notification channel is never named.
- FR 2c in the Design Report says "same category", but the pseudocode groups by `serviceType` ("Music streaming", not "Entertainment").
  The code follows the pseudocode, and the catalog gives each entry both fields.
