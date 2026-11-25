import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.oauth2 import UserId
from app.schema.general import ApiResponse, list_response
from app.schema.subscriptions import SubscriptionOut
from app.services import subscriptions as service
from db.database import get_db

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("")
async def list_subscriptions(
    user_id: UserId, db: DB
) -> ApiResponse[list[SubscriptionOut]]:
    return list_response(await service.list_subscriptions(db, user_id))


@router.post("/{subscription_id}/confirm", status_code=204)
async def confirm(subscription_id: uuid.UUID, user_id: UserId, db: DB) -> None:
    await service.confirm(db, user_id, subscription_id)


@router.post("/{subscription_id}/dismiss", status_code=204)
async def dismiss(subscription_id: uuid.UUID, user_id: UserId, db: DB) -> None:
    await service.dismiss(db, user_id, subscription_id)
