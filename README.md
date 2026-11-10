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
