"""The only module that talks to Plaid. Everything else gets a PlaidClient (get_plaid).

Plain httpx against Plaid's JSON API, no SDK. Credentials go in headers and the API
version is pinned by settings. Every failure becomes a PlaidError that says whether it
is worth retrying, and never carries the secret or an access token.
"""

import logging
from typing import NamedTuple

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Retrying cannot fix these, the user has to reconnect the bank.
PERMANENT_CODES = frozenset(
    {
        "ITEM_LOGIN_REQUIRED",
        "INVALID_ACCESS_TOKEN",
        "ITEM_NOT_FOUND",
        "USER_PERMISSION_REVOKED",
        "ACCESS_NOT_GRANTED",
    }
)

# Plaid's sandbox bank and its documented test user for transaction data (any password).
SANDBOX_INSTITUTION = "ins_109508"
SANDBOX_INSTITUTION_NAME = "First Platypus Bank"
SANDBOX_USER = "user_transactions_dynamic"
SANDBOX_PASSWORD = "pass_good"

# 24 months so yearly subscriptions can be spotted. Only 12 are stored (importer).
HISTORY_DAYS = 730
SYNC_PAGE_SIZE = 500
TIMEOUT_SECONDS = 20


class Exchanged(NamedTuple):
    access_token: str
    item_id: str


class PlaidError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message  # Plaid's wording, for logs only
        super().__init__(f"{code}: {message}" if message else code)

    @property
    def permanent(self) -> bool:
        return self.code in PERMANENT_CODES


class PlaidClient:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._settings = settings or get_settings()
        self._transport = transport

    async def _post(self, path: str, body: dict) -> dict:
        s = self._settings
        headers = {
            "PLAID-CLIENT-ID": s.plaid_client_id,
            "PLAID-SECRET": s.plaid_secret.get_secret_value(),
            "Plaid-Version": s.plaid_api_version,
        }
        try:
            async with httpx.AsyncClient(
                base_url=s.plaid_base_url,
                headers=headers,
                transport=self._transport,
                timeout=TIMEOUT_SECONDS,
            ) as http:
                response = await http.post(path, json=body)
        except httpx.HTTPError as exc:
            raise PlaidError("NETWORK_ERROR", type(exc).__name__) from None

        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code >= 400:
            code = data.get("error_code") or "PLAID_UNAVAILABLE"
            logger.warning(
                "plaid_error",
                extra={"path": path, "status": response.status_code, "code": code},
            )
            raise PlaidError(code, data.get("error_message", ""))
        return data

    async def create_link_token(self, user_id: str) -> dict:
        body = {
            "client_name": "Bill Buddy",
            "language": "en",
            "country_codes": ["US"],
            "user": {"client_user_id": user_id},
            "products": ["transactions"],
            "transactions": {"days_requested": HISTORY_DAYS},
        }
        if self._settings.plaid_webhook_url:
            body["webhook"] = self._settings.plaid_webhook_url
        data = await self._post("/link/token/create", body)
        return {"link_token": data["link_token"], "expiration": data["expiration"]}

    async def exchange_public_token(self, public_token: str) -> Exchanged:
        data = await self._post(
            "/item/public_token/exchange", {"public_token": public_token}
        )
        return Exchanged(data["access_token"], data["item_id"])

    async def transactions_sync(self, access_token: str, cursor: str | None) -> dict:
        body = {
            "access_token": access_token,
            "count": SYNC_PAGE_SIZE,
            "options": {"include_personal_finance_category": True},
        }
        if cursor:
            body["cursor"] = cursor
        return await self._post("/transactions/sync", body)

    async def item_remove(self, access_token: str) -> None:
        await self._post("/item/remove", {"access_token": access_token})

    async def sandbox_public_token(self) -> str:
        data = await self._post(
            "/sandbox/public_token/create",
            {
                "institution_id": SANDBOX_INSTITUTION,
                "initial_products": ["transactions"],
                "options": {
                    "override_username": SANDBOX_USER,
                    "override_password": SANDBOX_PASSWORD,
                },
            },
        )
        return data["public_token"]

    async def get_webhook_verification_key(self, key_id: str) -> dict:
        data = await self._post("/webhook_verification_key/get", {"key_id": key_id})
        return data["key"]


def get_plaid() -> PlaidClient:
    """FastAPI dependency. Tests replace it with a fake."""
    return PlaidClient()
