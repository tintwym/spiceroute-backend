"""add 'french' to cuisine_type enum

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-08 12:45:00

Same shape as 0005_vietnamese_cuisine: PG enums require an out-of-tx
`ALTER TYPE ... ADD VALUE`, and there's no clean way to remove an enum
value once written, so downgrade is intentionally a no-op.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE cuisine_type ADD VALUE IF NOT EXISTS 'french'")


def downgrade() -> None:
    # Dropping an enum value in Postgres requires tearing the type
    # down and rebuilding it plus recasting the column, and any rows
    # already written as 'french' would have to be migrated or
    # deleted first. Not worth it for an additive change.
    pass
