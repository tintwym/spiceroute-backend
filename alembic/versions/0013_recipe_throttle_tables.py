"""recipe-endpoint per-IP throttle tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-16 10:00:00

Adds three sibling counter tables so we can rate-limit the non-AI
recipe endpoints by client IP:

  * `recipe_list_usage`    -> GET /spice_routes               (hourly)
  * `recipe_detail_usage`  -> GET /spice_routes/{id}          (hourly)
  * `recipe_write_usage`   -> POST /spice_routes              (daily)

Shape mirrors `ai_usage` / `ai_chat_usage` from migration 0002 (see
`app/services/ai/rate_limit.py::_bump` for the upsert-on-conflict
pattern that consumes these tables). One table per (scope, granularity)
pair keeps the SQL trivial — no `kind` discriminator column, no extra
index for hot-path lookups.

Why separate tables per endpoint instead of a unified `endpoint_usage`
with a `kind` column:
  * The primary-key tuple `(ip, hour)` / `(ip, day)` already defines
    the lookup; adding a `kind` column would force every upsert to
    name it in both the `INSERT` and `ON CONFLICT` clauses, which is
    boilerplate that's easy to get wrong.
  * Each endpoint has its OWN ceiling. A unified table would have to
    do a per-row JOIN against a config table or carry the limit
    inline, neither of which is worth the savings on three small
    counter tables.

Why hourly (not daily) on the GETs:
  * Daily lets a single attacker burst 300 reqs in the first 10
    seconds of the day and then go silent for 24h. Hourly amortises
    the limit across the day, which is what we actually want.

Why daily on the POST:
  * Writes are expensive (LLM translation + DB INSERT cascade) but
    legitimate use is bursty — a user might publish 5 recipes in one
    sitting, then nothing for a week. A daily window forgives that
    pattern.

Downgrade drops all three. Safe to run because nothing else
references the tables.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recipe_list_usage",
        sa.Column("ip", postgresql.INET(), nullable=False),
        sa.Column("hour", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("ip", "hour"),
    )
    op.create_table(
        "recipe_detail_usage",
        sa.Column("ip", postgresql.INET(), nullable=False),
        sa.Column("hour", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("ip", "hour"),
    )
    op.create_table(
        "recipe_write_usage",
        sa.Column("ip", postgresql.INET(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("ip", "day"),
    )


def downgrade() -> None:
    op.drop_table("recipe_write_usage")
    op.drop_table("recipe_detail_usage")
    op.drop_table("recipe_list_usage")
