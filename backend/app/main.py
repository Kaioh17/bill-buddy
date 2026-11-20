from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.session import SESSION_HEADER
from app.core.config import get_settings
from app.core.exception import register_exception_handlers
from app.core.logging import log_requests, setup_logging
from app.models import (  # noqa: F401  (registers tables on Base.metadata)
    assumed_entries,
    catalog_entries,
    linked_accounts,
    matched_payments,
    merchnant_links,
    reminders,
    subscriptions,
    transactions,
    users,
)
from app.routers import auth, health


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.app_env, settings.effective_log_level)

    app = FastAPI(title="Bill Buddy API")
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)

    # Rate limiting on login and signup is intentionally not here yet.
    # It is out of scope for the school project, add it before any real deployment.
    app.middleware("http")(log_requests)
    # Added last so it is outermost and CORS headers also cover error responses.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=[SESSION_HEADER],  # lets browser JS read the renewed token
    )
    return app


app = create_app()
