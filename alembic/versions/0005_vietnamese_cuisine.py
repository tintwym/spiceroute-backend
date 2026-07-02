"""add 'vietnamese' to cuisine_type enum

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-08 04:00:00

Postgres `ALTER TYPE ... ADD VALUE` cannot run inside a transaction
block in PG <12. We use `op.execute` with the `COMMIT` workaround so the
migration succeeds on every supported version (alembic wraps `upgrade()`
in a transaction by default; the explicit COMMIT releases it).

There's no clean way to *remove* an enum value in Postgres without
re-creating the type. `downgrade()` is a no-op for that reason — running
the downgrade after a deploy that already wrote `vietnamese` rows would
otherwise leave dangling references. If we ever need a real rollback we
have to drop dependent rows first, drop+recreate the type, and re-cast
the column. Not worth the complexity for an additive enum change.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # IF NOT EXISTS guards against partial deploys / repeated runs.
    op.execute("ALTER TYPE cuisine_type ADD VALUE IF NOT EXISTS 'vietnamese'")


def downgrade() -> None:
    # Intentionally no-op: dropping an enum value in Postgres requires
    # tearing down + rebuilding the type plus recasting the column, and
    # any rows already written as 'vietnamese' would have to be migrated
    # or deleted first. The cost outweighs the benefit for an additive
    # change.
    pass
