"""Shared response shapes. Add cross-feature keys (pagination, request id, ...) here."""

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    """Base for schemas built straight from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class Meta(BaseModel):
    count: int | None = None  # number of items when data is a list


class ApiResponse[T](BaseModel):
    """Envelope for successful responses: the payload plus metadata."""

    meta: Meta = Field(default_factory=Meta)
    data: T


def list_response[T](items: list[T]) -> ApiResponse[list[T]]:
    return ApiResponse(data=items, meta=Meta(count=len(items)))


class FieldError(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str  # stable machine readable key, e.g. "invalid_credentials"
    message: str  # safe to show to the user
    details: list[FieldError] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
