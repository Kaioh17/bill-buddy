# Bill Buddy - agent instructions

A finance tracking web app that finds a user's recurring subscriptions from their bank transactions.
This is a prototype, so the goal is working end-to-end functionality, not production hardening.
`CLAUDE.md` is a symlink to this file, edit `AGENTS.md`.

## Read first

Read everything in `docs/` before starting any task.
- `docs/CHECKLIST.md` is the build checklist and the source of truth for what is done and what is open.
- `docs/ENDPOINTS.md` is the endpoint plan with the current build status of each group.
- The PDFs (Analysis Report, Design Report, Test Plan) are the requirements.
  FR is a functional requirement, NFR is non-functional, TC is a test case.
  Checklist items cite them, for example `(FR 1a, TC-01)`.

## Keeping the docs current

Update the docs in the same change as the code, not afterwards.
- **CHECKLIST.md:** tick items you finish.
  If an item is only partly done, leave it unticked and add an indented note saying what is done and what is missing.
  Add items you discover.
  Note any conflict between the code and the PDFs under "Doc inconsistencies to settle".
- **ENDPOINTS.md:** keep the status tag on each group (`[open]`, `[in progress]`, `[done]`) and the counts in the Summary correct.
  Record endpoints you add, rename or cut, and why.
- **Tell the user to share in-progress work.**
  When you set a group to `[in progress]`, remind the user to `git add` and commit `docs/ENDPOINTS.md` right away, so other developers can see what is being worked on and do not start the same group.
  Do the same when a group moves to `[done]`.
  Give the commands, do not run them.

## Backend (`backend/`)

Stack: FastAPI, async SQLAlchemy, Pydantic, uv, pytest, ruff.
Plaid is called with plain httpx, there is no Plaid SDK.

```bash
cd backend
uv sync
uv run fastapi dev                  # http://localhost:8000, docs at /docs
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
uv run python -m db.init_db         # dev only, creates missing tables
```

There are no migrations yet.
`init_db` skips tables that already exist, so after a column is added to a model the dev database must be deleted and recreated (or altered by hand).
Say so to the user whenever you change a model.

### Layout

One new file per endpoint parent (resource), in each layer, with the same name:
`app/routers/<name>.py`, `app/services/<name>.py`, `app/schema/<name>.py`, `tests/test_<name>_*.py`.
- **Routers** stay thin: parse the request, call a service, wrap the result.
- **Services** hold the logic and take the DB session (and the Plaid client) as arguments.
- **Models** are in `app/models/`, one table per file, documented in `app/models/model.md`.
- **`app/core/plaid.py`** is the only module that talks to Plaid.
- **`app/services/importer.py`** is the shared transaction import used by exchange, sync now and the webhook.

### Conventions

- **Tests first.**
  Write the tests for each service and route before the logic, and confirm they fail.
- **Errors:** raise the exceptions in `app/core/exception.py`.
  Add a new subclass there rather than building responses by hand.
  Messages must be safe to show a user: never put Plaid's wording, tokens or secrets in them.
- **Responses:** success is `ApiResponse(data=...)` or `list_response([...])`.
  Errors are `{"error": {"code", "message", "details"}}`.
- **Auth and ownership:** protect routes with `UserId` or `CurrentUser` from `app/auth/oauth2.py`.
  Every query is filtered by that user id, never an id from the request.
  Someone else's row looks exactly like a missing one (404).
- **Time:** call `clock.now()` from `app/core/clock.py`, never `datetime.now()`, so tests can fake today.
  Import the module (`from app.core import clock`), not the function.
- **Money** is `Decimal`.
  Plaid amounts are positive for money out, and are stored as Plaid sends them.
- **Secrets** come from settings (`app/core/config.py`) and `.env`, which is gitignored.
  Every new setting goes into `backend/.env.example` with a comment.
  Plaid access tokens are encrypted at rest (`app/auth/encryption.py`) and never returned by the API.
- **Logging:** log an event name plus structured fields, with user id and account id where relevant, never secrets.
- **Deliberate shortcuts** get a `# ponytail:` comment that names the ceiling and the upgrade path.

### Test setup

- **Fakes:** `tests/fakes.py` has `FakePlaid` and the `txn()`, `page()` and `signed_webhook()` builders.
  Tests never call the network.
- **Fixtures:** `tests/conftest.py` has an in-memory SQLite database (`sessions`, `session`), `frozen_now`, `make_account`, `add_txn`, `all_rows`, `fetch`, and an async HTTP client `api` wired to the fakes.
  Mark async test modules with `pytestmark = pytest.mark.anyio`.
- **Env:** test settings are set in `tests/conftest.py`, so a local `.env` never affects the tests.
- **Dates:** SQLite returns naive datetimes, so compare with `as_utc()` from `tests/fakes.py`.

## Frontend (`frontend/`)

React 19, Vite and TypeScript.
Run `npm run dev`, `npm run lint`, `npm run test`, `npm run build` from `frontend/`.
Auth uses the `X-Access-Token` response header: the client must replace its stored token whenever that header appears.

## Working rules

- Do not commit, push or stage.
  Give the exact git commands and let the user run them.
- Do not use em dashes, use a plain dash.
- In Markdown files, put each sentence on its own line.
- Tell the user when a change needs a manual step: a new `.env` value, a database recreate, or something to try in the frontend.
- Push back on a request that is contradictory or likely to produce a worse result, before acting.
