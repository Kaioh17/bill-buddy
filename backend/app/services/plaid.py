"""Bank linking: link token, token exchange, the sandbox shortcut and webhooks."""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import encrypt_token
from app.core import clock
from app.core.config import get_settings
from app.core.exception import (
    AppException,
    BankProviderError,
    InvalidWebhookError,
    NotFoundError,
    ReconnectRequiredError,
    SyncFailedError,
)
from app.core.plaid import SANDBOX_INSTITUTION_NAME, PlaidClient, PlaidError
from app.models.linked_accounts import LinkedAccount, LinkStatus
from app.schema.plaid import ExchangeRequest, LinkTokenOut
from app.services.importer import import_account

logger = logging.getLogger(__name__)

WEBHOOK_MAX_AGE = timedelta(minutes=5)  # Plaid's advice, stops replays of old webhooks


async def create_link_token(plaid: PlaidClient, user_id: uuid.UUID) -> LinkTokenOut:
    try:
        return LinkTokenOut(**await plaid.create_link_token(str(user_id)))
    except PlaidError:
        raise BankProviderError() from None  # PlaidClient already logged the details


async def exchange(
    db: AsyncSession, plaid: PlaidClient, user_id: uuid.UUID, data: ExchangeRequest
) -> LinkedAccount:
    try:
        exchanged = await plaid.exchange_public_token(data.public_token)
    except PlaidError:
        raise BankProviderError() from None

    account = LinkedAccount(
        user_id=user_id,
        plaid_item_id=exchanged.item_id,
        institution_name=data.institution_name,
        access_token_enc=encrypt_token(exchanged.access_token),
    )
    db.add(account)
    await db.commit()  # saved before importing so a failed import never loses the link
    await db.refresh(account)
    logger.info(
        "account_linked", extra={"user_id": str(user_id), "account_id": str(account.id)}
    )

    try:
        await import_account(db, plaid, account)
    except (SyncFailedError, ReconnectRequiredError):
        pass  # already recorded on the account, the retry schedule picks it up
    return account


async def sandbox_link(
    db: AsyncSession, plaid: PlaidClient, user_id: uuid.UUID
) -> LinkedAccount:
    """Dev shortcut: link Plaid's sandbox bank without the Link UI."""
    if get_settings().plaid_env != "sandbox":
        raise NotFoundError()
    try:
        public_token = await plaid.sandbox_public_token()
    except PlaidError:
        raise BankProviderError() from None
    data = ExchangeRequest(
        public_token=public_token, institution_name=SANDBOX_INSTITUTION_NAME
    )
    return await exchange(db, plaid, user_id, data)


async def verify_webhook(plaid: PlaidClient, body: bytes, token: str | None) -> None:
    """Plaid signs each webhook with a JWT (ES256) that carries the SHA-256 of the body.
    Raises InvalidWebhookError unless signature, age and body all check out."""
    if not token:
        raise InvalidWebhookError()
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "ES256" or not header.get("kid"):
            raise InvalidWebhookError()
        # ponytail: key fetched on every webhook, cache it by kid if volume grows.
        jwk = await plaid.get_webhook_verification_key(header["kid"])
        key = jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(jwk))
        claims = jwt.decode(
            token,
            key,
            algorithms=["ES256"],
            # Age is checked below against our own clock (which tests can fake).
            options={"require": ["iat"], "verify_iat": False},
        )
        issued = datetime.fromtimestamp(claims["iat"], UTC)
    except (jwt.PyJWTError, PlaidError, ValueError, KeyError, TypeError):
        raise InvalidWebhookError() from None

    if abs(clock.now() - issued) > WEBHOOK_MAX_AGE:
        raise InvalidWebhookError()
    expected = hashlib.sha256(body).hexdigest()
    if not hmac.compare_digest(str(claims.get("request_body_sha256", "")), expected):
        raise InvalidWebhookError()


async def handle_webhook(db: AsyncSession, plaid: PlaidClient, payload: dict) -> None:
    """Import when Plaid says new transactions are ready. Everything else is ignored.
    Never raises for a sync problem: that is recorded on the account, and Plaid should
    still get its 200 so it does not resend."""
    if (
        payload.get("webhook_type") != "TRANSACTIONS"
        or payload.get("webhook_code") != "SYNC_UPDATES_AVAILABLE"
    ):
        return
    account = await db.scalar(
        select(LinkedAccount).where(
            LinkedAccount.plaid_item_id == payload.get("item_id"),
            LinkedAccount.status == LinkStatus.ACTIVE,
        )
    )
    if account is None:
        return
    try:
        await import_account(db, plaid, account)
    except AppException:
        pass
