"""add difficulty enum + column to spice_routes

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-16 09:00:00

Adds a first-class `difficulty` field so the Explore grid's difficulty
chip is no longer derived from a flawed `totalMinutes + steps*5`
client-side heuristic (which hid the chip on narrow viewports and
mis-labelled long-braised recipes like Taiwanese Beef Noodle Soup
as EASY because the bucket math didn't account for unattended
simmering time).

Design notes:
  * `difficulty_type` is a native Postgres enum (`easy` / `medium` /
    `hard`). Same pattern as `cuisine_type` in migration 0001 — keeps
    inserts type-safe at the DB layer.
  * The column is `NOT NULL` with a server-side default of `medium`.
    Existing rows get `medium` on column-add (Postgres applies the
    server default to all current rows in one shot when the column
    is created NOT NULL with a DEFAULT); the curated seed script and
    the user-recipe backfill script (`scripts/backfill_difficulty.py`)
    then over-write that placeholder with the real value.
  * `medium` is the safest blanket default — it skews neither toward
    "the chip is meaningless because everything looks the same" nor
    toward "the chip lies in either direction".

Why NOT a separate fill-then-make-nullable dance:
  * One column at write time + one default is materially simpler than
    add-nullable / backfill / alter-not-null, and the latter pattern
    only matters when the default is expensive to compute or
    application-specific. `medium` qualifies as neither.

Downgrade drops both the column and the enum type. It's safe to run
because nothing else references `difficulty_type`.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Inline rather than imported from app.models.difficulty so the
# migration is hermetic — Alembic runs without the application's full
# import graph available, and a stale model file should never be able
# to silently change what an old migration creates.
_VALUES = ("easy", "medium", "hard")


def upgrade() -> None:
    difficulty_enum = sa.Enum(
        *_VALUES,
        name="difficulty_type",
        # The type is created out-of-band below so we can control naming;
        # `create_type=False` tells SQLAlchemy not to issue a second
        # CREATE TYPE when the column is added.
        create_type=False,
    )
    # Create the enum type FIRST so `add_column` can reference it.
    # CHECKFIRST guards against re-runs against a DB that was patched
    # manually before the migration landed.
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE difficulty_type AS ENUM ('easy', 'medium', 'hard'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )
    op.add_column(
        "spice_routes",
        sa.Column(
            "difficulty",
            difficulty_enum,
            nullable=False,
            server_default=sa.text("'medium'::difficulty_type"),
        ),
    )
    # Index because the API exposes filtering by difficulty (or will);
    # cheap to add now while the column is fresh, expensive to add
    # later behind a CONCURRENTLY workaround on a hot table.
    op.create_index(
        "ix_spice_routes_difficulty",
        "spice_routes",
        ["difficulty"],
    )


def downgrade() -> None:
    op.drop_index("ix_spice_routes_difficulty", table_name="spice_routes")
    op.drop_column("spice_routes", "difficulty")
    op.execute("DROP TYPE IF EXISTS difficulty_type")
