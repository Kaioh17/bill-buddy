# bill-buddy
A finance tracking web app for tracking user subscriptions.

## Backend

### Install uv

Linux and macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

macOS with Homebrew:

```bash
brew install uv
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart the terminal afterwards, then check with `uv --version`.
uv installs Python 3.12 for you if it is missing.

### Run

The commands are the same on Linux, macOS and Windows.

```bash
cd backend
uv sync
uv run fastapi dev
```

The API runs at http://localhost:8000.
Interactive docs are at http://localhost:8000/docs.

## Test and lint

```bash
cd backend
uv run pytest
uv run ruff check . && uv run ruff format .
```


## Frontend

Needs Node 22 or newer.

```bash
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:5173.

To work without the backend, create `frontend/.env.local` with `VITE_USE_MOCKS=true` and restart.
You can then sign in with any email and password and see sample data.
An email starting with `empty`, `error` or `slow` shows that state.
This only works in `npm run dev`, never in a production build.

Check your work with `npm run lint`, `npm run test` and `npm run build`.

# sqllite setup
```bash
uv run python -m db.init_db 
``` 

