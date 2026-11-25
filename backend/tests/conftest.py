"""Test setup: env first, then a stateful fake AsyncSession (no database yet)."""

import datetime as dt
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

# Must be set before app modules are imported. Plain assignment beats any local .env.
os.environ.update(
    {
        "APP_ENV": "dev",
        "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-chars-long",
        "CORS_ORIGINS": "http://localhost:5173",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        "SESSION_MAX_HOURS": "12",
        "PLAID_CLIENT_ID": "test-client-id",
        "PLAID_SECRET": "test-plaid-secret",
        "PLAID_ENV": "sandbox",
        "PLAID_WEBHOOK_URL": "",
        "TOKEN_ENCRYPTION_KEY": "hLDLg6EamhHY5C1yygf6am8X4MgRwy-Awkdp7VbBBPA=",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.auth.encryption import encrypt_token  # noqa: E402
from app.auth.tokens import create_access_token  # noqa: E402
from app.core import clock  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.plaid import get_plaid  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.catalog_entries import CatalogEntry  # noqa: E402
from app.models.linked_accounts import LinkedAccount, LinkStatus  # noqa: E402
from app.models.subscriptions import (  # noqa: E402
    Frequency,
    Subscription,
    SubscriptionSource,
    SubscriptionStatus,
)
from app.models.transactions import Transaction  # noqa: E402
from app.models.users import User  # noqa: E402
from db.database import Base, get_db  # noqa: E402
from tests.fakes import FROZEN_NOW, PLAIN_TOKEN, FakePlaid  # noqa: E402


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeDB:
    """Stands in for AsyncSession. Looks users up by the one bound param (the email)."""

    def __init__(self):
        self.users = {}
        self.pending = []
        self.rollbacks = 0
        self.race = False  # simulate another request inserting the same email first

    async def execute(self, stmt):
        email = next(iter(stmt.compile().params.values()))
        return _Result(self.users.get(email))

    def add(self, obj):
        self.pending.append(obj)

    async def commit(self):
        pending, self.pending = self.pending, []
        for obj in pending:
            if self.race or obj.email in self.users:
                raise IntegrityError("INSERT users", {}, Exception("duplicate key"))
            obj.id = uuid.uuid4()  # server defaults
            obj.created_at = datetime.now(UTC)
            self.users[obj.email] = obj

    async def refresh(self, obj):
        pass

    async def rollback(self):
        self.rollbacks += 1
        self.pending = []


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def app(fake_db):
    app = create_app()

    async def override():
        yield fake_db

    app.dependency_overrides[get_db] = override
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


GOOD_SIGNUP = {
    "first_name": "Ada",
    "last_name": "Lovelace",
    "email": "ada@example.com",
    "password": "correct horse battery",
    "confirm_password": "correct horse battery",
}


# ---- Real (in-memory SQLite) database fixtures, for the Plaid and sync tests ----
# Use these with `pytestmark = pytest.mark.anyio`. FakeDB above only knows users.


@pytest.fixture
async def sessions():
    # StaticPool keeps one connection so the in-memory DB survives across sessions.
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def session(sessions):
    async with sessions() as s:
        yield s


@pytest.fixture
def fake_plaid():
    return FakePlaid()


@pytest.fixture
def frozen_now(monkeypatch):
    """Fakes "today" for everything that reads app.core.clock.now()."""
    monkeypatch.setattr(clock, "now", lambda: FROZEN_NOW)
    return FROZEN_NOW


@pytest.fixture
def production_env(monkeypatch):
    monkeypatch.setenv("PLAID_ENV", "production")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


async def _make_user(sessions, email: str) -> uuid.UUID:
    async with sessions() as s:
        user = User(
            first_name="Ada", last_name="Lovelace", email=email, password_hash="x"
        )
        s.add(user)
        await s.commit()
        return user.id


@pytest.fixture
async def user_id(sessions):
    return await _make_user(sessions, "ada@example.com")


@pytest.fixture
async def other_user_id(sessions):
    return await _make_user(sessions, "grace@example.com")


@pytest.fixture
def auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


@pytest.fixture
def other_auth(other_user_id):
    return {"Authorization": f"Bearer {create_access_token(other_user_id)}"}


@pytest.fixture
def make_account(sessions):
    async def make(user_id, **overrides) -> LinkedAccount:
        fields = {
            "user_id": user_id,
            "plaid_item_id": "item-1",
            "institution_name": "First Platypus Bank",
            "access_token_enc": encrypt_token(PLAIN_TOKEN),
            "status": LinkStatus.ACTIVE,
        } | overrides
        async with sessions() as s:
            account = LinkedAccount(**fields)
            s.add(account)
            await s.commit()
            return account

    return make


@pytest.fixture
def add_txn(sessions):
    async def add(account: LinkedAccount, id: str = "t1", **overrides) -> None:
        fields = {
            "transaction_id": id,
            "linked_account_id": account.id,
            "user_id": account.user_id,
            "plaid_account_id": "acc-1",
            "amount": Decimal("9.99"),
            "date": dt.date(2026, 11, 1),
            "pending": False,
        } | overrides
        async with sessions() as s:
            s.add(Transaction(**fields))
            await s.commit()

    return add


@pytest.fixture
def add_series(add_txn):
    """`await add_series(account, "Netflix", ago(70, 40, 10), amounts=[...])`: one
    charge per date, 15.99 each unless `amounts` is given. Keywords go to every row."""

    async def series(account, merchant, dates, amounts=None, **overrides) -> None:
        for i, day in enumerate(dates):
            await add_txn(
                account,
                f"{merchant}-{day}-{i}",
                merchant_name=merchant,
                date=day,
                amount=Decimal(str((amounts or [15.99] * len(dates))[i])),
                **overrides,
            )

    return series


@pytest.fixture
def make_entry(sessions):
    async def make(name: str = "Netflix", **overrides) -> CatalogEntry:
        fields = {
            "name": name,
            "service_type": "Video streaming",
            "category": "Entertainment",
            "aliases": [name.lower()],
            "merchant_entity_ids": [],
        } | overrides
        async with sessions() as s:
            entry = CatalogEntry(**fields)
            s.add(entry)
            await s.commit()
            return entry

    return make


@pytest.fixture
def make_sub(sessions):
    """A detected ACTUAL monthly subscription unless overridden. For a manual one pass
    `source=SubscriptionSource.MANUAL, merchant_key=None, status=None`."""

    async def make(user_id, **overrides) -> Subscription:
        fields = {
            "user_id": user_id,
            "source": SubscriptionSource.DETECTED,
            "merchant_key": "name:netflix",
            "name": "Netflix",
            "frequency": Frequency.MONTHLY,
            "status": SubscriptionStatus.ACTUAL,
            "amount": Decimal("15.99"),
            "last_payment_date": dt.date(2026, 11, 12),
            "next_expected_date": dt.date(2026, 12, 12),
            "is_active": True,
        } | overrides
        async with sessions() as s:
            sub = Subscription(**fields)
            s.add(sub)
            await s.commit()
            return sub

    return make


@pytest.fixture
def all_rows(sessions):
    """`await all_rows(Model)` reads the table through a fresh session."""

    async def read(model) -> list:
        async with sessions() as s:
            return list((await s.scalars(select(model))).all())

    return read


@pytest.fixture
def fetch(sessions):
    """`await fetch(Model, pk)` re-reads one row through a fresh session."""

    async def read(model, pk):
        async with sessions() as s:
            return await s.get(model, pk)

    return read


@pytest.fixture
async def api(sessions, fake_plaid):
    """Async HTTP client on the real app, with the SQLite DB and FakePlaid wired in."""
    app = create_app()

    async def db_override():
        async with sessions() as s:
            yield s

    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_plaid] = lambda: fake_plaid
    # raise_app_exceptions=False so an unhandled error is a 500 response, as in prod.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
