"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-05 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
    )
    op.create_index("ix_tags_name", "tags", ["name"])

    op.create_table(
        "mecipes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prep_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cook_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("servings", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mecipes_user_id", "mecipes", ["user_id"])
    op.create_index("ix_mecipes_title", "mecipes", ["title"])
    op.create_index("ix_mecipes_is_public", "mecipes", ["is_public"])
    op.create_index(
        "ix_mecipes_public_recent",
        "mecipes",
        ["is_public", sa.text("created_at DESC")],
    )
    op.execute(
        "CREATE INDEX ix_mecipes_title_trgm ON mecipes USING GIN (lower(title) gin_trgm_ops)"
    )

    op.create_table(
        "ingredients",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mecipe_id", sa.Uuid(), sa.ForeignKey("mecipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=True),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_ingredients_mecipe_id", "ingredients", ["mecipe_id"])
    op.create_index("ix_ingredients_name", "ingredients", ["name"])
    op.execute(
        "CREATE INDEX ix_ingredients_name_trgm ON ingredients USING GIN (lower(name) gin_trgm_ops)"
    )

    op.create_table(
        "steps",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mecipe_id", sa.Uuid(), sa.ForeignKey("mecipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("body", sa.Text(), nullable=False),
    )
    op.create_index("ix_steps_mecipe_id", "steps", ["mecipe_id"])

    op.create_table(
        "mecipe_tags",
        sa.Column("mecipe_id", sa.Uuid(), sa.ForeignKey("mecipes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Uuid(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "favorites",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mecipe_id", sa.Uuid(), sa.ForeignKey("mecipes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("favorites")
    op.drop_table("mecipe_tags")
    op.drop_index("ix_steps_mecipe_id", table_name="steps")
    op.drop_table("steps")
    op.execute("DROP INDEX IF EXISTS ix_ingredients_name_trgm")
    op.drop_index("ix_ingredients_name", table_name="ingredients")
    op.drop_index("ix_ingredients_mecipe_id", table_name="ingredients")
    op.drop_table("ingredients")
    op.execute("DROP INDEX IF EXISTS ix_mecipes_title_trgm")
    op.drop_index("ix_mecipes_public_recent", table_name="mecipes")
    op.drop_index("ix_mecipes_is_public", table_name="mecipes")
    op.drop_index("ix_mecipes_title", table_name="mecipes")
    op.drop_index("ix_mecipes_user_id", table_name="mecipes")
    op.drop_table("mecipes")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
