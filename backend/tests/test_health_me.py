"""GET /health/me: token checks and session life, driven through a real login."""

from datetime import UTC, datetime, timedelta

from app.auth.session import SESSION_HEADER
from app.auth.tokens import create_access_token
from app.core.config import get_settings
from tests.conftest import GOOD_SIGNUP


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def parse(ts):
    return datetime.fromisoformat(ts)


def test_me_without_token_is_401(client):
    r = client.get("/health/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "not_authenticated"
    assert r.headers["www-authenticate"] == "Bearer"


def test_me_with_garbage_token_is_401(client):
    r = client.get("/health/me", headers=bearer("not.a.jwt"))
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_token"


def test_me_with_expired_token_is_401(client):
    token = create_access_token("u1", expires_delta=timedelta(seconds=-5))
    r = client.get("/health/me", headers=bearer(token))
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "token_expired"


def test_me_after_real_login_returns_token_content(client):
    user = client.post("/auth/signup", json=GOOD_SIGNUP).json()["data"]
    login = client.post(
        "/auth/login",
        data={"username": GOOD_SIGNUP["email"], "password": GOOD_SIGNUP["password"]},
    )
    r = client.get("/health/me", headers=bearer(login.json()["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == user["id"]
    cap = timedelta(hours=get_settings().session_max_hours)
    assert parse(body["session_expires_at"]) - parse(body["session_started_at"]) == cap
    assert parse(body["expires_at"]) > parse(body["issued_at"])
    assert body["token_id"]


def test_me_renews_the_token_and_keeps_the_session_start(client):
    started = datetime.now(UTC) - timedelta(hours=2)
    token = create_access_token("u1", session_start=started)
    r = client.get("/health/me", headers=bearer(token))
    assert r.status_code == 200
    renewed = r.headers[SESSION_HEADER]
    assert renewed != token
    # The renewed token is itself accepted and still carries the original start.
    r2 = client.get("/health/me", headers=bearer(renewed))
    assert r2.status_code == 200
    assert r2.json()["session_started_at"] == r.json()["session_started_at"]


def test_me_past_the_session_cap_still_works_but_is_not_renewed(client):
    started = datetime.now(UTC) - timedelta(hours=13)
    token = create_access_token("u1", session_start=started)
    r = client.get("/health/me", headers=bearer(token))
    assert r.status_code == 200  # token itself is still valid
    assert SESSION_HEADER not in r.headers  # but the session can no longer be extended
