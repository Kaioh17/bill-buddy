from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.oauth2 import CurrentUser
from app.core.config import get_settings
from app.core.logging import logging

router = APIRouter(prefix="/health", tags=["health"])

logger = logging.getLogger(__name__)


class Health(BaseModel):
    status: str


class TokenInfo(BaseModel):
    user_id: str
    issued_at: datetime
    expires_at: datetime
    session_started_at: datetime
    session_expires_at: datetime  # hard cap, renewal stops here
    token_id: str


@router.get("/")
def get_health() -> Health:
    return Health(status="ok")


@router.get("/me")
def get_me(user: CurrentUser) -> TokenInfo:
    """Test route for auth: echoes the caller's token content, so session life and
    the current-user guard can be checked. Remove or hide before production."""
    cap = timedelta(hours=get_settings().session_max_hours)
    logger.debug(f"User -  {user}")
    return TokenInfo(
        user_id=user.sub,
        issued_at=user.iat,
        expires_at=user.exp,
        session_started_at=user.sat,
        session_expires_at=user.sat + cap,
        token_id=user.jti,
    )
