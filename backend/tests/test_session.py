from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Response

from app.auth.session import SESSION_HEADER, renew_session
from app.auth.tokens import create_access_token, decode_token
from app.core.config import get_settings

SECRET = get_settings().jwt_secret_key.get_secret_value()


def token_started(hours_ago):
    started = datetime.now(UTC) - timedelta(hours=hours_ago)
    return jwt.encode(
        {
            "sub": "u1",
            "type": "access",
            "jti": "j",
            "iat": started,
            "sat": int(started.timestamp()),
            "exp": datetime.now(UTC) + timedelta(minutes=1),
        },
        SECRET,
        algorithm="HS256",
    )


def test_renew_extends_expiry_and_keeps_session_start():
    old = decode_token(token_started(1))
    resp = Response()
    renew_session(resp, old)
    new = decode_token(resp.headers[SESSION_HEADER])
    assert new.sub == "u1"
    assert new.sat == old.sat  # absolute cap measured from login
    assert new.exp - new.iat == timedelta(minutes=15)
    assert new.jti != old.jti


def test_renew_stops_after_absolute_session_limit():
    old = decode_token(token_started(13))  # limit is 12h in tests
    resp = Response()
    renew_session(resp, old)
    assert SESSION_HEADER not in resp.headers


def test_fresh_login_token_is_renewable():
    resp = Response()
    renew_session(resp, decode_token(create_access_token("u1")))
    assert SESSION_HEADER in resp.headers
