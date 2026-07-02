"""add calories_per_serving to spice_routes

Stores an approximate per-serving calorie count. Nullable so existing rows
and AI generations that fail to estimate are unaffected.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-07 04:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "spice_routes",
        sa.Column("calories_per_serving", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("spice_routes", "calories_per_serving")
