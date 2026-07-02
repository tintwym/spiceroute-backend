"""retag sub-national recipe rows to parent country cuisines

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-22 14:00:00
"""
from collections.abc import Sequence

from alembic import op
from app.models.cuisine_catalog import (
  CHINESE_SUBNATIONAL_WIRES,
  JAPANESE_SUBNATIONAL_WIRES,
  MYANMAR_REGIONAL_WIRES,
)

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _retag(wires: tuple[str, ...], parent: str) -> None:
  wires_sql = ", ".join(f"'{w}'" for w in wires)
  op.execute(
      f"UPDATE spice_routes SET cuisine = '{parent}' "
      f"WHERE cuisine::text IN ({wires_sql})"
  )


def upgrade() -> None:
    _retag(CHINESE_SUBNATIONAL_WIRES, "chinese")
    _retag(MYANMAR_REGIONAL_WIRES, "burmese")
    _retag(JAPANESE_SUBNATIONAL_WIRES, "japanese")


def downgrade() -> None:
    pass
