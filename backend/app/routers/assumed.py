from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.oauth2 import UserId
from app.schema.catalog import AssumedIn, AssumedOut
from app.schema.general import ApiResponse
from app.services import catalog as service
from db.database import get_db

router = APIRouter(prefix="/assumed", tags=["assumed"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.put("")
async def save_assumed(
    data: AssumedIn, user_id: UserId, db: DB
) -> ApiResponse[AssumedOut]:
    saved = await service.save_assumed(db, user_id, data.catalog_entry_ids)
    return ApiResponse(data=AssumedOut(catalog_entry_ids=saved))
