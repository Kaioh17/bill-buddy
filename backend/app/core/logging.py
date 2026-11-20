"""Logging setup: readable console in dev, one JSON object per line in prod.

Log events as a short name plus structured fields, never secrets:
    logger.info("login_ok", extra={"user_id": str(user.id)})
"""

import json
import logging
import time
from datetime import UTC, datetime

from fastapi import Request

# Attributes every LogRecord has; anything else came from `extra=`.
_STANDARD = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}

access_logger = logging.getLogger("app.access")


def _extras(record: logging.LogRecord) -> dict:
    return {k: v for k, v in record.__dict__.items() if k not in _STANDARD}


class DevFormatter(logging.Formatter):
    """`time LEVEL logger - message key=value ...`"""

    def __init__(self):
        super().__init__("%(asctime)s %(levelname)-8s %(name)s - %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)  # also appends the traceback if any
        extras = " ".join(f"{k}={v}" for k, v in _extras(record).items())
        head, sep, tb = line.partition("\n")
        return f"{head} {extras}".rstrip() + sep + tb


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **_extras(record),
        }
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str)


def setup_logging(env: str, level: str) -> None:
    """Install one stderr handler on the root logger. Safe to call repeatedly."""
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if not getattr(h, "_billbuddy", False)]
    handler = logging.StreamHandler()
    handler._billbuddy = (
        True  # marks it as ours so reruns and test handlers are left alone
    )
    handler.setFormatter(JsonFormatter() if env == "prod" else DevFormatter())
    root.addHandler(handler)
    # Our own loggers get the requested level. Libraries stay at INFO or above,
    # otherwise DEBUG in dev drowns the output in asyncio/sqlalchemy noise.
    root.setLevel(max(logging.getLevelNamesMapping()[level.upper()], logging.INFO))
    logging.getLogger("app").setLevel(level.upper())
    # Replaced by log_requests below, otherwise every request is logged twice.
    logging.getLogger("uvicorn.access").disabled = True


def mask_email(email: str) -> str:
    """ada@example.com -> a***@example.com: correlatable, but not stored PII."""
    local, at, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if at and local else "***"


async def log_requests(request: Request, call_next):
    """HTTP middleware: one line per request. Path only, the query may hold tokens."""
    start = time.perf_counter()
    status = 500  # stays 500 if the app raises
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        level = (
            logging.ERROR
            if status >= 500
            else logging.WARNING
            if status >= 400
            else logging.INFO
        )
        access_logger.log(
            level,
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
