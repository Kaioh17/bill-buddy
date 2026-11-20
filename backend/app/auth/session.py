"""Session control on top of stateless JWTs.

Inactivity timeout: every authenticated response carries a fresh token in the
X-Access-Token header, so a token only dies after ACCESS_TOKEN_EXPIRE_MINUTES
without requests. The client replaces its stored token whenever it sees the header.
Absolute limit: renewal stops SESSION_MAX_HOURS after login (the `sat` claim).
"""

from datetime import UTC, datetime, timedelta

from fastapi import Response

from app.auth.tokens import TokenClaims, create_access_token
from app.core.config import get_settings

SESSION_HEADER = "X-Access-Token"


def renew_session(response: Response, claims: TokenClaims) -> None:
    max_age = timedelta(hours=get_settings().session_max_hours)
    if datetime.now(UTC) - claims.sat >= max_age:
        return  # no new token: the user is sent to log in again when this one expires
    response.headers[SESSION_HEADER] = create_access_token(
        claims.sub, session_start=claims.sat
    )
