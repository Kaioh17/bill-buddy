"""Preset exceptions and the handlers that turn them into a consistent JSON error.

Raise these from services and routes instead of building responses by hand:
    raise EmailAlreadyRegisteredError()
Every error response looks like {"error": {"code", "message", "details"}}.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schema.general import ErrorBody, ErrorResponse, FieldError

logger = logging.getLogger("app.errors")

_BEARER = {"WWW-Authenticate": "Bearer"}


class AppException(Exception):
    """Base class. Subclasses only set the class attributes below."""

    status_code = 500
    code = "internal_error"
    message = "Something went wrong"
    headers: dict[str, str] | None = None

    def __init__(self, message: str | None = None):
        self.message = message or self.message
        super().__init__(self.message)


# Generic HTTP errors
class BadRequestError(AppException):
    status_code, code, message = 400, "bad_request", "Bad request"


class UnauthorizedError(AppException):
    status_code, code, message = 401, "unauthorized", "Unauthorized"
    headers = _BEARER


class ForbiddenError(AppException):
    status_code, code, message = (
        403,
        "forbidden",
        "You do not have access to this resource",
    )


class NotFoundError(AppException):
    status_code, code, message = 404, "not_found", "Not found"


class ConflictError(AppException):
    status_code, code, message = 409, "conflict", "Conflict"


# Auth logic errors
class InvalidCredentialsError(UnauthorizedError):
    # One message for wrong password and unknown email so neither can be probed.
    code, message = "invalid_credentials", "Invalid email or password"


class NotAuthenticatedError(UnauthorizedError):
    code, message = "not_authenticated", "Not authenticated"


class InvalidTokenError(UnauthorizedError):
    code, message = "invalid_token", "Invalid token"


class TokenExpiredError(UnauthorizedError):
    code, message = "token_expired", "Session expired, please log in again"


class EmailAlreadyRegisteredError(ConflictError):
    code, message = (
        "email_already_registered",
        "An account with this email already exists",
    )


# Bank link and sync errors. Messages are safe to show: Plaid's own wording and codes
# stay in the logs and never reach the client.
class BankProviderError(AppException):
    status_code, code, message = (
        502,
        "bank_provider_error",
        "We could not reach your bank provider. Please try again.",
    )


class SyncFailedError(BankProviderError):
    code, message = (
        "sync_failed",
        "Sync failed. Your data may be out of date. Try sync now.",
    )


class ReconnectRequiredError(ConflictError):
    code, message = (
        "reconnect_required",
        "Your bank login has expired. Reconnect this account.",
    )


class SyncInProgressError(ConflictError):
    code, message = "sync_in_progress", "A sync is already running for this account"


class InvalidWebhookError(UnauthorizedError):
    code, message = "invalid_webhook", "Invalid webhook signature"


def _error(
    status: int, code: str, message: str, details=None, headers=None
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(
        body.model_dump(mode="json"), status_code=status, headers=headers
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _app_exc(request: Request, exc: AppException):
        level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
        logger.log(
            level,
            "app_error",
            extra={
                "code": exc.code,
                "status": exc.status_code,
                "path": request.url.path,
            },
        )
        return _error(exc.status_code, exc.code, exc.message, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        # Built from loc + msg only: pydantic's default response echoes the submitted
        # input, which here would include passwords.
        details = [
            FieldError(
                field=".".join(str(p) for p in err["loc"][1:]),
                message=err["msg"].removeprefix("Value error, "),
            )
            for err in exc.errors()
        ]
        logger.warning(
            "validation_error",
            extra={"path": request.url.path, "fields": [d.field for d in details]},
        )
        return _error(422, "validation_error", "Invalid request", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        # Framework errors such as 404 on an unknown route or 405.
        return _error(
            exc.status_code,
            f"http_{exc.status_code}",
            str(exc.detail),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("unhandled_error", extra={"path": request.url.path})
        return _error(500, "internal_error", "Something went wrong")
