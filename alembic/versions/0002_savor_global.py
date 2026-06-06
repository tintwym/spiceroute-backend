"""savor global recipes pivot

Adds cuisine/language/spice_level/is_premium to spice_routes, makes user_id
nullable (anonymous creates), drops the favorites table (saves move to client
localStorage in v1), and creates ai_usage / ai_chat_usage tables for per-IP
rate limiting on the new /ai/* endpoints.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-06 04:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CUISINE_VALUES = (
    "korean",
    "japanese",
    "chinese",
    "burmese",
    "thai",
    "indian",
    "italian",
    "american_western",
    "mexican",
)


def upgrade() -> None:
    # 1) Cuisine enum and the new columns on spice_routes.
    cuisine_enum = postgresql.ENUM(*CUISINE_VALUES, name="cuisine_type")
    cuisine_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "spice_routes",
        sa.Column("cuisine", cuisine_enum, nullable=True),
    )
    op.add_column(
        "spice_routes",
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
    )
    op.add_column(
        "spice_routes",
        sa.Column("spice_level", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "spice_routes",
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_index("ix_spice_routes_cuisine", "spice_routes", ["cuisine"])
    op.create_index("ix_spice_routes_language", "spice_routes", ["language"])
    op.create_index(
        "ix_spice_routes_cuisine_premium",
        "spice_routes",
        ["cuisine", "is_premium"],
    )

    # 2) Allow anonymous recipe creation (no auth in v1).
    op.alter_column("spice_routes", "user_id", existing_type=sa.Uuid(), nullable=True)

    # 3) Drop the favorites table — saves now live in the client.
    op.drop_table("favorites")

    # 4) Per-IP AI rate-limit counters.
    op.create_table(
        "ai_usage",
        sa.Column("ip", postgresql.INET(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("ip", "day"),
    )
    op.create_table(
        "ai_chat_usage",
        sa.Column("ip", postgresql.INET(), nullable=False),
        sa.Column("hour", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("ip", "hour"),
    )


def downgrade() -> None:
    op.drop_table("ai_chat_usage")
    op.drop_table("ai_usage")

    # Restore favorites (best-effort — original migration's shape).
    op.create_table(
        "favorites",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "spice_route_id",
            sa.Uuid(),
            sa.ForeignKey("spice_routes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.alter_column("spice_routes", "user_id", existing_type=sa.Uuid(), nullable=False)

    op.drop_index("ix_spice_routes_cuisine_premium", table_name="spice_routes")
    op.drop_index("ix_spice_routes_language", table_name="spice_routes")
    op.drop_index("ix_spice_routes_cuisine", table_name="spice_routes")

    op.drop_column("spice_routes", "is_premium")
    op.drop_column("spice_routes", "spice_level")
    op.drop_column("spice_routes", "language")
    op.drop_column("spice_routes", "cuisine")

    postgresql.ENUM(name="cuisine_type").drop(op.get_bind(), checkfirst=True)
