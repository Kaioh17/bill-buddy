"""PlaidClient against a mock HTTP transport: request shape and error mapping."""

import json

import httpx
import pytest

from app.core.config import get_settings
from app.core.plaid import Exchanged, PlaidClient, PlaidError

pytestmark = pytest.mark.anyio


def client_for(response_json=None, status=200, *, settings=None, text=None):
    """Returns (client, seen) where seen collects every request that was sent."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if text is not None:
            return httpx.Response(status, text=text)
        return httpx.Response(status, json=response_json or {})

    return PlaidClient(settings, transport=httpx.MockTransport(handler)), seen


def body_of(request: httpx.Request) -> dict:
    return json.loads(request.content)


async def test_link_token_request_shape():
    client, seen = client_for(
        {"link_token": "link-abc", "expiration": "2026-01-01T00:00:00Z"}
    )
    out = await client.create_link_token("user-123")

    assert out == {"link_token": "link-abc", "expiration": "2026-01-01T00:00:00Z"}
    [req] = seen
    assert req.url.host == "sandbox.plaid.com"
    assert req.url.path == "/link/token/create"
    assert req.headers["PLAID-CLIENT-ID"] == "test-client-id"
    assert req.headers["PLAID-SECRET"] == "test-plaid-secret"
    assert req.headers["Plaid-Version"] == "2020-09-14"
    body = body_of(req)
    assert body["user"] == {"client_user_id": "user-123"}
    assert body["products"] == ["transactions"]
    assert body["transactions"] == {"days_requested": 730}
    assert body["country_codes"] == ["US"]
    assert "webhook" not in body


async def test_link_token_includes_webhook_url_when_configured():
    settings = get_settings().model_copy(
        update={"plaid_webhook_url": "https://x.test/plaid/webhook"}
    )
    client, seen = client_for({"link_token": "l", "expiration": "e"}, settings=settings)
    await client.create_link_token("user-123")
    assert body_of(seen[0])["webhook"] == "https://x.test/plaid/webhook"


async def test_production_env_uses_the_production_host():
    settings = get_settings().model_copy(update={"plaid_env": "production"})
    client, seen = client_for({"link_token": "l", "expiration": "e"}, settings=settings)
    await client.create_link_token("user-123")
    assert seen[0].url.host == "production.plaid.com"


async def test_exchange_public_token():
    client, seen = client_for({"access_token": "access-1", "item_id": "item-1"})
    out = await client.exchange_public_token("public-1")

    assert out == Exchanged(access_token="access-1", item_id="item-1")
    assert seen[0].url.path == "/item/public_token/exchange"
    assert body_of(seen[0]) == {"public_token": "public-1"}


async def test_transactions_sync_first_call_has_no_cursor():
    client, seen = client_for({"added": [], "next_cursor": "c1", "has_more": False})
    out = await client.transactions_sync("access-1", None)

    assert out["next_cursor"] == "c1"
    assert seen[0].url.path == "/transactions/sync"
    body = body_of(seen[0])
    assert body["access_token"] == "access-1"
    assert "cursor" not in body


async def test_transactions_sync_sends_the_cursor():
    client, seen = client_for({"next_cursor": "c2"})
    await client.transactions_sync("access-1", "c1")
    assert body_of(seen[0])["cursor"] == "c1"


async def test_item_remove():
    client, seen = client_for({"request_id": "r"})
    await client.item_remove("access-1")
    assert seen[0].url.path == "/item/remove"
    assert body_of(seen[0]) == {"access_token": "access-1"}


async def test_sandbox_public_token():
    client, seen = client_for({"public_token": "public-sandbox-1"})
    assert await client.sandbox_public_token() == "public-sandbox-1"
    assert seen[0].url.path == "/sandbox/public_token/create"
    assert body_of(seen[0])["initial_products"] == ["transactions"]


async def test_webhook_verification_key():
    jwk = {"kty": "EC", "kid": "kid-1"}
    client, seen = client_for({"key": jwk})
    assert await client.get_webhook_verification_key("kid-1") == jwk
    assert seen[0].url.path == "/webhook_verification_key/get"
    assert body_of(seen[0]) == {"key_id": "kid-1"}


async def test_api_error_keeps_plaid_code_and_login_required_is_permanent():
    client, _ = client_for(
        {
            "error_type": "ITEM_ERROR",
            "error_code": "ITEM_LOGIN_REQUIRED",
            "error_message": "the login details of this item have changed",
        },
        status=400,
    )
    with pytest.raises(PlaidError) as err:
        await client.transactions_sync("access-1", None)
    assert err.value.code == "ITEM_LOGIN_REQUIRED"
    assert err.value.permanent


async def test_rate_limit_is_temporary():
    client, _ = client_for(
        {"error_type": "RATE_LIMIT_EXCEEDED", "error_code": "RATE_LIMIT_EXCEEDED"},
        status=429,
    )
    with pytest.raises(PlaidError) as err:
        await client.transactions_sync("access-1", None)
    assert err.value.code == "RATE_LIMIT_EXCEEDED"
    assert not err.value.permanent


async def test_non_json_server_error_is_temporary():
    client, _ = client_for(status=502, text="bad gateway")
    with pytest.raises(PlaidError) as err:
        await client.transactions_sync("access-1", None)
    assert err.value.code == "PLAID_UNAVAILABLE"
    assert not err.value.permanent


async def test_network_failure_is_temporary():
    def boom(request):
        raise httpx.ConnectError("no route")

    client = PlaidClient(transport=httpx.MockTransport(boom))
    with pytest.raises(PlaidError) as err:
        await client.transactions_sync("access-1", None)
    assert err.value.code == "NETWORK_ERROR"
    assert not err.value.permanent


async def test_errors_never_contain_credentials_or_tokens():
    client, _ = client_for(
        {"error_type": "API_ERROR", "error_code": "INTERNAL_SERVER_ERROR"}, status=500
    )
    with pytest.raises(PlaidError) as err:
        await client.transactions_sync("access-super-secret", None)
    shown = f"{err.value!s} {err.value!r}"
    assert "access-super-secret" not in shown
    assert "test-plaid-secret" not in shown
