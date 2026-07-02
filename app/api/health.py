import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
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
    surfacing partial failures.

    The `ai` block exposes ENOUGH of the LLM config to debug a
    half-configured deploy from outside (e.g. `curl /health` from a
    laptop) without leaking the API key itself. We surface only:

      * `stub_mode`            — the boolean the AI endpoints actually
                                 branch on. If True, every AI call
                                 returns mock content regardless of
                                 the rest of the fields below.
      * `force_stub`           — `AI_FORCE_STUB=1`, the hard-override.
                                 Common cause of "I set the key but
                                 still see stub" — leftover from an
                                 older deploy that hasn't been pruned.
      * `provider_host`        — hostname only, never the path or
                                 credentials. Lets an operator spot a
                                 misconfigured `LLM_BASE_URL` (typo,
                                 forgot `/openai/v1`, etc.).
      * `model`                — the model name. Public info on every
                                 provider's docs site.
      * `api_key_set`          — boolean. NOT the key. NOT a hash.
                                 Just whether `LLM_API_KEY.strip()`
                                 is non-empty in the running process.

    The combination of those five fields uniquely identifies every
    misconfiguration case we've actually hit in production."""
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

    settings = get_settings()
    ai_block = {
        "stub_mode": settings.ai_stub_mode,
        "force_stub": settings.ai_force_stub,
        "provider_host": urlparse(settings.llm_base_url).hostname or None,
        "model": settings.llm_model or None,
        "api_key_set": bool(settings.llm_api_key.strip()),
    }

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "database_error": db_error,
        "ai": ai_block,
    }
