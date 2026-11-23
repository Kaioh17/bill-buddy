import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.oauth2 import UserId
from app.core.plaid import PlaidClient, get_plaid
from app.schema.accounts import AccountOut, SyncOut
from app.schema.general import ApiResponse, list_response
from app.services import accounts as service
from db.database import get_db

router = APIRouter(prefix="/accounts", tags=["accounts"])

DB = Annotated[AsyncSession, Depends(get_db)]
Plaid = Annotated[PlaidClient, Depends(get_plaid)]


@router.get("")
async def list_accounts(user_id: UserId, db: DB) -> ApiResponse[list[AccountOut]]:
    rows = await service.list_accounts(db, user_id)
    return list_response([AccountOut.model_validate(r) for r in rows])


@router.post("/{account_id}/sync")
async def sync_now(
    account_id: uuid.UUID, user_id: UserId, db: DB, plaid: Plaid
) -> ApiResponse[SyncOut]:
    return ApiResponse(data=await service.sync_now(db, plaid, user_id, account_id))


@router.delete("/{account_id}", status_code=204)
async def disconnect(
    account_id: uuid.UUID,
    user_id: UserId,
    db: DB,
    plaid: Plaid,
    delete_transactions: bool = False,
) -> None:
    await service.disconnect(db, plaid, user_id, account_id, delete_transactions)
