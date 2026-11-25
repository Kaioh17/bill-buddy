from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.oauth2 import UserId
from app.schema.catalog import CatalogEntryOut
from app.schema.general import ApiResponse, list_response
from app.services import catalog as service
from db.database import get_db

router = APIRouter(prefix="/catalog", tags=["catalog"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("")
async def list_catalog(user_id: UserId, db: DB) -> ApiResponse[list[CatalogEntryOut]]:
    return list_response(await service.list_catalog(db, user_id))
