"""Real DB check: every table builds on SQLite, and signup/login work end to end."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app
from db.database import Base, get_db
from tests.conftest import GOOD_SIGNUP

pytestmark = pytest.mark.anyio


@pytest.fixture
async def sqlite_client():
    # StaticPool keeps one connection so the in-memory DB survives across sessions.
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    app = create_app()

    async def override():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    await engine.dispose()


async def test_all_tables_created():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    assert len(Base.metadata.tables) == 10


async def test_signup_then_login(sqlite_client):
    r = sqlite_client.post("/auth/signup", json=GOOD_SIGNUP)
    assert r.status_code == 201
    assert r.json()["data"]["email"] == "ada@example.com"

    r = sqlite_client.post(
        "/auth/login",
        data={"username": GOOD_SIGNUP["email"], "password": GOOD_SIGNUP["password"]},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


async def test_duplicate_signup_conflicts(sqlite_client):
    sqlite_client.post("/auth/signup", json=GOOD_SIGNUP)
    r = sqlite_client.post("/auth/signup", json=GOOD_SIGNUP)
    assert r.status_code == 409
