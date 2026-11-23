"""OAuth2 bearer scheme and the dependency that protects routes.

Usage:  def route(user: CurrentUser): ...
It rejects missing, invalid and expired tokens and renews the session on success.
Returns the token claims only. Loading the User row (and rejecting disabled users)
gets added here once routes need it, so every route picks it up at once.
"""

import uuid
from typing import Annotated

from fastapi import Depends, Response
from fastapi.security import OAuth2PasswordBearer

from app.auth.session import renew_session
from app.auth.tokens import TokenClaims, decode_token
from app.core.exception import InvalidTokenError, NotAuthenticatedError

# auto_error=False so a missing token goes through our error format, not FastAPI's.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_claims(
    response: Response, token: Annotated[str | None, Depends(oauth2_scheme)]
) -> TokenClaims:
    if not token:
        raise NotAuthenticatedError()
    claims = decode_token(token)
    renew_session(response, claims)
    return claims


CurrentUser = Annotated[TokenClaims, Depends(get_current_claims)]


def get_user_id(claims: CurrentUser) -> uuid.UUID:
    """The logged-in user's id. Routes use this and never an id from the request."""
    try:
        return uuid.UUID(claims.sub)
    except ValueError:
        raise InvalidTokenError() from None


UserId = Annotated[uuid.UUID, Depends(get_user_id)]
