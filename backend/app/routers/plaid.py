import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.oauth2 import UserId
from app.core.exception import BadRequestError
from app.core.plaid import PlaidClient, get_plaid
from app.schema.accounts import AccountOut
from app.schema.general import ApiResponse
from app.schema.plaid import ExchangeRequest, LinkTokenOut
from app.services import plaid as service
from db.database import get_db

router = APIRouter(prefix="/plaid", tags=["plaid"])

DB = Annotated[AsyncSession, Depends(get_db)]
Plaid = Annotated[PlaidClient, Depends(get_plaid)]


@router.post("/link-token")
async def link_token(user_id: UserId, plaid: Plaid) -> ApiResponse[LinkTokenOut]:
    return ApiResponse(data=await service.create_link_token(plaid, user_id))


@router.post("/exchange", status_code=201)
async def exchange(
    data: ExchangeRequest, user_id: UserId, db: DB, plaid: Plaid
) -> ApiResponse[AccountOut]:
    """Called after Plaid Link succeeds. Saves the bank and runs the first import."""
    account = await service.exchange(db, plaid, user_id, data)
    return ApiResponse(data=AccountOut.model_validate(account))


@router.post("/sandbox-link", status_code=201)
async def sandbox_link(
    user_id: UserId, db: DB, plaid: Plaid
) -> ApiResponse[AccountOut]:
    """Dev only (404 outside the sandbox): links Plaid's test bank with no Link UI."""
    account = await service.sandbox_link(db, plaid, user_id)
    return ApiResponse(data=AccountOut.model_validate(account))


@router.post("/webhook")
async def webhook(
    request: Request,
    db: DB,
    plaid: Plaid,
    plaid_verification: Annotated[str | None, Header()] = None,
) -> dict:
    """Called by Plaid, not by the frontend. The signature is the credential."""
    body = await request.body()  # the signature covers these exact bytes
    await service.verify_webhook(plaid, body, plaid_verification)
    try:
        payload = json.loads(body)
    except ValueError:
        raise BadRequestError("Webhook body is not JSON") from None
    if isinstance(payload, dict):
        await service.handle_webhook(db, plaid, payload)
    return {"status": "ok"}
