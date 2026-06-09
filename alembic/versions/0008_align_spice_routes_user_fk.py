"""align spice_routes.user_id FK ondelete with the ORM (CASCADE → SET NULL)

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-10 00:30:00

Schema drift fix.

Timeline:
  * 0001_initial: created `spice_routes.user_id` as `ON DELETE CASCADE`,
    nullable=False — i.e. "every recipe belongs to a user, and deleting
    the user wipes their recipes."
  * 0002_savor_global: flipped `user_id` to `nullable=True` (so the
    seeded curated catalog can have orphan recipes with no author),
    BUT did not touch the FK action.
  * `app/models/spice_route.py`: ORM declares `ondelete="SET NULL"`,
    consistent with the new nullable column — the intent is "deleting
    a user orphans their recipes back into the public catalog rather
    than removing them entirely."

The DB and the ORM disagreed for several releases. Anyone hard-deleting
a user (GDPR erasure, admin tooling, manual SQL) would silently
CASCADE-delete every recipe that user ever published — including the
seeded curated ones if their `user_id` happened to point at a real
user. This migration re-creates the constraint with the action the
model has always claimed.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Postgres' default name for an implicit FK is `<table>_<col>_fkey`.
# `0001_initial` did not name the constraint explicitly so the live
# DB will have exactly this name.
_FK_NAME = "spice_routes_user_id_fkey"


def upgrade() -> None:
    op.drop_constraint(_FK_NAME, "spice_routes", type_="foreignkey")
    op.create_foreign_key(
        _FK_NAME,
        "spice_routes",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Restore the (incorrect) CASCADE behaviour to match the
    # pre-0008 schema state, in case someone needs to roll back to
    # an older app version that depended on the cascade.
    op.drop_constraint(_FK_NAME, "spice_routes", type_="foreignkey")
    op.create_foreign_key(
        _FK_NAME,
        "spice_routes",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
