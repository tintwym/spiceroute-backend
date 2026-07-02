"""Per-IP daily / hourly rate limiting backed by Postgres.

Despite the `app/services/ai/` location (historical — the AI Creator was
the first endpoint to need throttling), this module is now the shared
home for ALL per-IP rate limits in the app. The full list:

  * AI Creator                  -> daily, `ai_usage` table
  * AI Companion (chat)         -> hourly, `ai_chat_usage` table
  * GET /spice_routes (list)    -> hourly, `recipe_list_usage` table
  * GET /spice_routes/{id}      -> hourly, `recipe_detail_usage` table
  * POST /spice_routes (create) -> daily, `recipe_write_usage` table

Different counters per endpoint because the usage patterns are
genuinely different: a chat session might send 30 messages but only
generate a couple of recipes; an anonymous browser might fetch 50
recipe details in a sitting but only ever POSTs a handful per day.
A unified counter would force the strictest limit on everything.
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
    table: Literal[
        "ai_usage",
        "ai_chat_usage",
        "recipe_list_usage",
        "recipe_detail_usage",
        "recipe_write_usage",
    ],
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


def _current_hour() -> datetime:
    """Truncate `now` to the start of the current UTC hour.

    Extracted so the list / detail / chat quota helpers all bucket
    against the exact same instant — a fractional-second skew between
    two calls in the same request would yield two different rows in
    the counter table (one with count=1, one with count=1) instead
    of the one row with count=2 we want.
    """
    return datetime.now(tz=UTC).replace(minute=0, second=0, microsecond=0)


async def check_recipe_list_quota(db: AsyncSession, *, ip: str) -> None:
    """Hourly cap on GET /spice_routes per client IP.

    Default ceiling is ~300/hour (see `settings.recipe_list_per_hour`)
    which is one request every 12 seconds for an hour straight — well
    above any realistic human browsing pattern, well below the rate
    a scraper would need to mirror the catalog quickly. The cap is
    intentionally soft enough that the Flutter Explore screen's
    repeated paginated calls (default `pageSize=30`, ~3 pages per
    user session) never approach it.
    """
    await _bump(
        db,
        table="recipe_list_usage",
        key_col="hour",
        key_val=_current_hour(),
        ip=ip,
        limit=settings.recipe_list_per_hour,
        label="recipe-list",
    )


async def check_recipe_detail_quota(db: AsyncSession, *, ip: str) -> None:
    """Hourly cap on GET /spice_routes/{id} per client IP.

    Sized 2x the list cap because detail-fetch is the natural follow-up
    to a list call (browsing a feed -> opening a recipe). Symmetry
    would force a 1:1 list-vs-detail user flow that doesn't match
    real behavior. Default is 600/hour.
    """
    await _bump(
        db,
        table="recipe_detail_usage",
        key_col="hour",
        key_val=_current_hour(),
        ip=ip,
        limit=settings.recipe_detail_per_hour,
        label="recipe-detail",
    )


async def check_recipe_write_quota(db: AsyncSession, *, ip: str) -> None:
    """Daily cap on POST /spice_routes per client IP.

    Daily (not hourly) because the legitimate publish pattern is bursty
    — a user might author 5 recipes in a single sitting then nothing
    for a week, and an hourly window would falsely throttle that.
    The auth requirement on the endpoint already gates anonymous
    abuse; this layer protects against a single attacker creating
    many accounts behind one IP. Default ceiling: 50/day.
    """
    today = datetime.now(tz=UTC).date()
    await _bump(
        db,
        table="recipe_write_usage",
        key_col="day",
        key_val=today,
        ip=ip,
        limit=settings.recipe_writes_per_day,
        label="recipe-write",
    )
