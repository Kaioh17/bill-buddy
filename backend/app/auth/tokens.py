"""JWT access tokens: create and verify.

Claims: sub (user id), iat, exp, jti (unique id, for revocation later), type, and
sat ("session at", when the login happened) which survives renewals so a session
can be capped in absolute length. All times are epoch seconds.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.exception import InvalidTokenError, TokenExpiredError

_TYPE = "access"  # lets a future refresh token type be told apart from this one
_REQUIRED = ["sub", "exp", "iat", "sat", "jti", "type"]


class TokenClaims(BaseModel):
    sub: str  # user_id
    iat: datetime
    exp: datetime
    sat: datetime
    jti: str


def create_access_token(
    sub: uuid.UUID | str,
    *,
    expires_delta: timedelta | None = None,
    session_start: datetime | None = None,
) -> str:
    s = get_settings()
    now = int(datetime.now(UTC).timestamp())
    ttl = expires_delta or timedelta(minutes=s.access_token_expire_minutes)
    payload = {
        "sub": str(sub),
        "type": _TYPE,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + int(ttl.total_seconds()),
        "sat": int(session_start.timestamp()) if session_start else now,
    }
    return jwt.encode(
        payload, s.jwt_secret_key.get_secret_value(), algorithm=s.jwt_algorithm
    )


def decode_token(token: str) -> TokenClaims:
    """Verify signature, expiry and required claims. Raises our own auth errors."""
    s = get_settings()
    try:
        payload = jwt.decode(
            token,
            s.jwt_secret_key.get_secret_value(),
            algorithms=[
                s.jwt_algorithm
            ],  # fixed list, so "alg: none" and key confusion fail
            options={"require": _REQUIRED},
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError() from None
    except jwt.InvalidTokenError:
        raise InvalidTokenError() from None
    if payload["type"] != _TYPE:
        raise InvalidTokenError()
    return TokenClaims(**{k: payload[k] for k in TokenClaims.model_fields})
