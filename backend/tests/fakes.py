"""Test doubles and builders for the Plaid tests (no network, no real Plaid)."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.plaid import Exchanged, PlaidError

FROZEN_NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
PLAIN_TOKEN = "access-sandbox-test-token"

# One signing key plays "Plaid" for webhook tests, the fake serves its public half.
_PLAID_KEY = ec.generate_private_key(ec.SECP256R1())
PLAID_JWK = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(_PLAID_KEY.public_key()))
_OTHER_KEY = ec.generate_private_key(ec.SECP256R1())


def as_utc(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes, Postgres aware ones. Compare as UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def txn(
    id: str = "t1",
    *,
    amount: float = 12.5,
    date: str = "2026-11-01",
    pending: bool = False,
    account_id: str = "acc-1",
    merchant: str | None = "Netflix",
    pfc: tuple[str, str] | None = ("ENTERTAINMENT", "ENTERTAINMENT_TV_AND_MOVIES"),
) -> dict:
    """One transaction in the shape Plaid's /transactions/sync returns."""
    return {
        "transaction_id": id,
        "account_id": account_id,
        "amount": amount,
        "iso_currency_code": "USD",
        "date": date,
        "authorized_date": None,
        "pending": pending,
        "merchant_name": merchant,
        "merchant_entity_id": "ent-1" if merchant else None,
        "original_description": f"{merchant or 'UNKNOWN'} 123",
        "personal_finance_category": (
            {"primary": pfc[0], "detailed": pfc[1]} if pfc else None
        ),
    }


def page(
    added=(),
    modified=(),
    removed=(),
    *,
    cursor: str = "c1",
    has_more: bool = False,
    status: str = "HISTORICAL_UPDATE_COMPLETE",
) -> dict:
    """One /transactions/sync response. `removed` takes plain transaction ids."""
    return {
        "added": list(added),
        "modified": list(modified),
        "removed": [{"transaction_id": i} for i in removed],
        "next_cursor": cursor,
        "has_more": has_more,
        "transactions_update_status": status,
    }


def signed_webhook(
    body: bytes,
    *,
    iat: datetime = FROZEN_NOW,
    alg: str = "ES256",
    wrong_key: bool = False,
    body_hash: bytes | None = None,
) -> str:
    """A Plaid-Verification JWT for `body`. The flags build the bad variants."""
    claims = {
        "iat": int(iat.timestamp()),
        "request_body_sha256": hashlib.sha256(
            body if body_hash is None else body_hash
        ).hexdigest(),
    }
    key = _OTHER_KEY if wrong_key else _PLAID_KEY
    if alg == "HS256":
        return jwt.encode(claims, "x" * 40, algorithm=alg, headers={"kid": "kid-1"})
    return jwt.encode(claims, key, algorithm=alg, headers={"kid": "kid-1"})


class FakePlaid:
    """Same methods as PlaidClient. Set the *_error fields to make a call fail."""

    def __init__(self):
        # Sync responses are returned in order, an exception in the list is raised.
        # When the list runs out, an empty page comes back.
        self.pages: list = []
        self.sync_calls: list[tuple[str, str | None]] = []
        self.link_calls: list[str] = []
        self.exchanged: list[str] = []
        self.removed: list[str] = []
        self.link_error: PlaidError | None = None
        self.exchange_error: PlaidError | None = None
        self.remove_error: PlaidError | None = None
        self.webhook_key_error: PlaidError | None = None
        self.webhook_key: dict = PLAID_JWK

    async def create_link_token(self, user_id: str) -> dict:
        if self.link_error:
            raise self.link_error
        self.link_calls.append(user_id)
        return {"link_token": "link-sandbox-abc", "expiration": "2026-11-22T16:00:00Z"}

    async def exchange_public_token(self, public_token: str) -> Exchanged:
        if self.exchange_error:
            raise self.exchange_error
        self.exchanged.append(public_token)
        return Exchanged(access_token=PLAIN_TOKEN, item_id="item-1")

    async def transactions_sync(self, access_token: str, cursor: str | None) -> dict:
        self.sync_calls.append((access_token, cursor))
        item = self.pages.pop(0) if self.pages else page(cursor=cursor or "c0")
        if isinstance(item, Exception):
            raise item
        return item

    async def item_remove(self, access_token: str) -> None:
        if self.remove_error:
            raise self.remove_error
        self.removed.append(access_token)

    async def sandbox_public_token(self) -> str:
        return "public-sandbox-abc"

    async def get_webhook_verification_key(self, key_id: str) -> dict:
        if self.webhook_key_error:
            raise self.webhook_key_error
        return self.webhook_key


def minutes_ago(n: int) -> datetime:
    return FROZEN_NOW - timedelta(minutes=n)
