"""The one place "now" comes from, so tests can fake today (conftest frozen_now).

Call it as `clock.now()`, never `from app.core.clock import now`,
or the fake can't reach it.
"""

from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC)
