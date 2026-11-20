"""Test setup: env first, then a stateful fake AsyncSession (no database yet)."""

import os
import uuid
from datetime import UTC, datetime

# Must be set before app modules are imported. Plain assignment beats any local .env.
os.environ.update(
    {
        "APP_ENV": "dev",
        "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-chars-long",
        "CORS_ORIGINS": "http://localhost:5173",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        "SESSION_MAX_HOURS": "12",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.main import create_app  # noqa: E402
from db.database import get_db  # noqa: E402


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
