"""add 5 cuisines to cuisine_type enum: greek, spanish, malaysian, german, indonesian

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-10 19:30:00

Same shape as 0005_vietnamese_cuisine and 0006_french_cuisine: PG enums
require an out-of-tx `ALTER TYPE ... ADD VALUE`, and there's no clean way
to remove an enum value once written, so downgrade is intentionally a
no-op.

The five values are added in one logical step but as separate statements
because each `ALTER TYPE ... ADD VALUE` must run outside the surrounding
migration transaction. `IF NOT EXISTS` makes the script idempotent — safe
to re-run on databases that were patched by hand before the migration
landed.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_CUISINES = ("greek", "spanish", "malaysian", "german", "indonesian")


def upgrade() -> None:
    for value in _NEW_CUISINES:
        op.execute(f"ALTER TYPE cuisine_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Dropping an enum value in Postgres requires tearing the type down
    # and rebuilding it plus recasting the column, and any rows already
    # written with these values would have to be migrated or deleted
    # first. Not worth it for an additive change — leave the values in
    # place on downgrade.
    pass
