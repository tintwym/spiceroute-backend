"""add translations JSONB column to spice_routes

Stores per-locale title / description overrides keyed by ISO 639-1 code,
e.g. `{"my": {"title": "...", "description": "..."}}`. The list / detail
endpoints accept a `translate_to=<locale>` query parameter and swap the
matching entry onto the row before serialising. Nullable + default-null
so existing rows are unaffected; the API endpoint already handles a
missing / empty `translations` dict by returning the original
`title` / `description` columns.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-12 11:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Mirror the model column's `with_variant`: native JSONB on
    # Postgres (binary storage, GIN-indexable) and plain JSON on any
    # other dialect (the test suite runs against SQLite).
    #
    # Nullable on purpose — an explicit empty `{}` default would force
    # every existing row to be rewritten by the migration, which is
    # wasteful at scale (the table is the largest in the schema). The
    # endpoint treats `NULL` and `{}` identically (no translation
    # available → use the original title/description).
    op.add_column(
        "spice_routes",
        sa.Column(
            "translations",
            sa.JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("spice_routes", "translations")
