"""retag provincial Chinese recipe rows as chinese

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-22 12:00:00
"""
from collections.abc import Sequence

from alembic import op
from app.models.cuisine_catalog import CHINESE_PROVINCIAL_WIRES

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    wires = ", ".join(f"'{w}'" for w in CHINESE_PROVINCIAL_WIRES)
    op.execute(
        f"UPDATE spice_routes SET cuisine = 'chinese' "
        f"WHERE cuisine::text IN ({wires})"
    )


def downgrade() -> None:
    # Irreversible — provincial assignment was discarded on upgrade.
    pass
