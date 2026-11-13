# Models

## Tables

users (id pk, first_name, last_name, email unique, password_hash, created_at, updated_at)
One row per app account.

linked_accounts (id pk, user_id fk, plaid_item_id, institution_name, access_token_enc, status, cursor, history_ready, last_sync_at, next_sync, last_error, sync_locked_at, yearly_check_status, yearly_check_attempts, yearly_check_started_at, created_at)
A bank connection (Plaid item) for a user, plus its sync state (cursor, schedule, lock, errors) and yearly-check progress.

transactions (transaction_id pk, linked_account_id fk, user_id fk, plaid_account_id, amount, iso_currency_code, date, authorized_date, pending, merchant_name, merchant_entity_id, original_description, pfc_primary, pfc_detailed)
Bank transactions stored as Plaid sends them.

subscriptions (id pk, user_id fk, source, merchant_key, name, frequency, kind, service_type, category, status, likely_reasons, amount, last_payment_date, next_expected_date, is_active, created_at)
Recurring payments (subscriptions and bills), both auto-detected and manually added, in one table.

matched_payments (id pk, subscription_id fk, user_id fk, transaction_id unique, date, amount, merchant_name)
Links a transaction to the subscription it was identified as a payment for (transaction_id has no FK on purpose).

dismissed_subscriptions (user_id pk fk, merchant_key pk, frequency pk)
Detections the user rejected, so they are not suggested again.

reminders (id pk, subscription_id fk, user_id fk, due_date, lead_days, remind_at, sent_at)
Scheduled upcoming-payment reminders. Unique per subscription, due date and lead days. `sent_at` is null until sent.

catalog_entries (id pk, name unique, service_type, category, aliases, merchant_entity_ids)
Preseeded list of known services. It is data, not code.

assumed_entries (user_id pk fk, catalog_entry_id pk fk)
Catalog services the user says they pay for.

merchant_links (user_id pk fk, merchant_key pk, catalog_entry_id fk)
Remembers that a user's merchant maps to a given catalog service.

## Enums

link_status: active, needs_reauth, disconnected (linked_accounts.status)
subscription_source: DETECTED, MANUAL
subscription_frequency: WEEKLY, MONTHLY, YEARLY (also used by dismissed_subscriptions)
subscription_kind: SUBSCRIPTION, BILL
subscription_status: ACTUAL, LIKELY (null for manual entries)
