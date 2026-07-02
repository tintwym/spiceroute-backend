"""widen spice_routes.image_path for long Wikimedia URLs

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-25 10:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "spice_routes",
        "image_path",
        existing_type=sa.String(500),
        type_=sa.String(1024),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "spice_routes",
        "image_path",
        existing_type=sa.String(1024),
        type_=sa.String(500),
        existing_nullable=True,
    )
