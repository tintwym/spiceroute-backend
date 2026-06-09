"""Per-IP daily / hourly rate limiting backed by Postgres.

Two counters because the AI Creator (recipe generation) and the AI Companion
(chat) have very different usage patterns: a user might send 30 chat messages
in a session but only generate a couple of recipes a day.
"""
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

settings = get_settings()


async def _bump(
    db: AsyncSession,
    *,
    table: Literal["ai_usage", "ai_chat_usage"],
    key_col: str,
    key_val: date | datetime,
    ip: str,
    limit: int,
    label: str,
) -> None:
    """Atomically increment the (ip, key) counter; raise 429 when over limit.

    Uses INSERT ... ON CONFLICT DO UPDATE so we don't need a transaction-level
    lock and we get a single round-trip.

    NOTE on commit ordering: we commit BEFORE raising 429. Otherwise the
    failed-attempt increment rolls back when the HTTPException propagates,
    which means a user spamming the endpoint past their quota never moves
    the counter past `limit` — the limit IS still enforced (subsequent
    requests still see `> limit` from the live UPDATE), but historical
    over-quota attempts are invisible to logs/dashboards. Committing first
    keeps the counter honest.
    """
    row = await db.execute(
        text(
            f"""
            INSERT INTO {table} (ip, {key_col}, count)
            VALUES (CAST(:ip AS inet), :key, 1)
            ON CONFLICT (ip, {key_col})
            DO UPDATE SET count = {table}.count + 1
            RETURNING count
            """
        ),
        {"ip": ip, "key": key_val},
    )
    count = row.scalar_one()
    await db.commit()
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{label} rate limit exceeded ({limit} per period)",
        )


async def check_recipe_quota(db: AsyncSession, *, ip: str) -> None:
    today = datetime.now(tz=UTC).date()
    await _bump(
        db,
        table="ai_usage",
        key_col="day",
        key_val=today,
        ip=ip,
        limit=settings.ai_rate_limit_per_day,
        label="recipe-generation",
    )


async def check_chat_quota(db: AsyncSession, *, ip: str) -> None:
    # Bucket by truncated hour, in UTC.
    now = datetime.now(tz=UTC).replace(minute=0, second=0, microsecond=0)
    await _bump(
        db,
        table="ai_chat_usage",
        key_col="hour",
        key_val=now,
        ip=ip,
        limit=settings.ai_chat_per_hour,
        label="chat",
    )
