from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.oauth2 import UserId
from app.schema.general import ApiResponse
from app.schema.reconciliation import ReconciliationOut
from app.services import reconciliation as service
from db.database import get_db

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("")
async def reconciliation(user_id: UserId, db: DB) -> ApiResponse[ReconciliationOut]:
    return ApiResponse(data=await service.reconcile(db, user_id))
