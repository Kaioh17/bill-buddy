from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exception import InvalidCredentialsError
from app.schema.auth import LoginRequest, SignupRequest, Token, UserOut
from app.schema.general import ApiResponse
from app.services import auth as service
from db.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/signup", status_code=201)
async def signup(data: SignupRequest, db: DB) -> ApiResponse[UserOut]:
    user = await service.signup(db, data)
    return ApiResponse(data=UserOut.model_validate(user))


@router.post("/login")
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB) -> Token:
    """The login route: OAuth2 password flow, form-encoded (also powers Swagger's
    Authorize button). The form's `username` is the email."""
    try:
        data = LoginRequest(email=form.username, password=form.password)
    except ValidationError:
        # Malformed input gets the same answer as a wrong password.
        raise InvalidCredentialsError() from None
    return await service.login(db, data)
