from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.auth.tokens import create_access_token, decode_token
from app.core.config import get_settings
from app.core.exception import InvalidTokenError, TokenExpiredError

SECRET = get_settings().jwt_secret_key.get_secret_value()


def forge(**claims):
    now = datetime.now(UTC)
    base = {
        "sub": "u1",
        "type": "access",
        "iat": now,
        "sat": int(now.timestamp()),
        "exp": now + timedelta(minutes=5),
        "jti": "x",
    }
    return jwt.encode({**base, **claims}, SECRET, algorithm="HS256")


def test_roundtrip():
    c = decode_token(create_access_token("u1"))
    assert c.sub == "u1"
    assert c.exp - c.iat == timedelta(minutes=15)
    assert c.sat == c.iat


def test_jti_unique():
    a, b = (decode_token(create_access_token("u1")) for _ in range(2))
    assert a.jti != b.jti


def test_expired():
    with pytest.raises(TokenExpiredError):
        decode_token(create_access_token("u1", expires_delta=timedelta(seconds=-5)))


def test_tampered_and_garbage():
    t = create_access_token("u1")
    for bad in (t[:-2] + ("AA" if not t.endswith("AA") else "BB"), "garbage", ""):
        with pytest.raises(InvalidTokenError):
            decode_token(bad)


def test_wrong_secret():
    bad = jwt.encode(
        {"sub": "u1", "type": "access", "exp": 9999999999}, "x" * 40, algorithm="HS256"
    )
    with pytest.raises(InvalidTokenError):
        decode_token(bad)


def test_alg_none_rejected():
    bad = jwt.encode(
        {"sub": "u1", "type": "access", "exp": 9999999999}, None, algorithm="none"
    )
    with pytest.raises(InvalidTokenError):
        decode_token(bad)


def test_wrong_type_rejected():
    with pytest.raises(InvalidTokenError):
        decode_token(forge(type="refresh"))


@pytest.mark.parametrize("missing", ["sub", "exp", "sat", "jti"])
def test_missing_claims_rejected(missing):
    now = datetime.now(UTC)
    claims = {
        "sub": "u1",
        "type": "access",
        "iat": now,
        "sat": int(now.timestamp()),
        "exp": now + timedelta(minutes=5),
        "jti": "x",
    }
    del claims[missing]
    with pytest.raises(InvalidTokenError):
        decode_token(jwt.encode(claims, SECRET, algorithm="HS256"))
