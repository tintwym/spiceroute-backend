import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

log = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    """Always returns 200 so the load balancer / Render's health probe
    treats the process as alive even when the database is unreachable.
    The body discloses WHICH dependency is failing, which is what
    operators (and any human eyeballing the deploy) actually need.

    Returning 500 here when only the DB is sick caused Render to mark
    the whole service as unhealthy and refuse traffic — including the
    AI Companion + AI Creator endpoints which don't need Postgres at
    all. The split status object below gives the load balancer
    something honest to flip on (`status == "ok"`) while still
    surfacing partial failures."""
    db_status = "ok"
    db_error: str | None = None
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() != 1:
            db_status = "down"
            db_error = "select 1 did not return 1"
    except Exception as exc:
        log.warning("health: database probe failed: %s", exc)
        db_status = "down"
        # Surface the class name only — full repr would leak host /
        # credential fragments from asyncpg's error strings into the
        # public health endpoint.
        db_error = type(exc).__name__

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "database_error": db_error,
    }
