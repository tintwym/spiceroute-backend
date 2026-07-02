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

Implementation note — constraint name discovery:
  The original FK in 0001_initial was created via `sa.ForeignKey(...)`
  inside `op.create_table(...)`, which lets Postgres auto-name the
  constraint. The convention is `<table>_<col>_fkey` →
  `spice_routes_user_id_fkey`, but the actual name can drift in
  practice (Postgres deduplicates by appending a numeric suffix if a
  name is already taken, an operator might have renamed it manually,
  a different SQLAlchemy naming_convention could have been active at
  creation time, etc.).

  We look up the live constraint name at runtime via information_schema
  so the migration works against any production DB whose schema matches
  the logical 0007 state, regardless of how the constraint ended up
  named.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Name we use when re-creating the constraint. Matches the Postgres
# auto-naming convention so a future `pg_dump` looks "natural"
# (i.e. as if it were created by `sa.ForeignKey(...)` without an
# explicit `name=` argument).
_FK_NAME = "spice_routes_user_id_fkey"


def _resolve_fk_name(bind: sa.Connection) -> str | None:
    """Return the live FK constraint name on
    `spice_routes.user_id`, or `None` if no such FK exists.

    Uses `information_schema` (portable across Postgres versions and
    SQLAlchemy releases). Returns the first match — there's only one
    FK on that column by definition.
    """
    row = bind.execute(
        sa.text(
            """
            SELECT tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = 'spice_routes'
              AND kcu.column_name = 'user_id'
            LIMIT 1
            """
        )
    ).first()
    return row[0] if row else None


def upgrade() -> None:
    bind = op.get_bind()
    # SQLite (used in tests) ignores ondelete-action changes anyway
    # and doesn't support ALTER on FKs, so skip the dance entirely.
    # The model + 0007 schema is correct on a fresh `create_all`.
    if bind.dialect.name == "sqlite":
        return

    live_name = _resolve_fk_name(bind)
    if live_name is not None:
        op.drop_constraint(live_name, "spice_routes", type_="foreignkey")
    # else: nothing to drop — the FK may have been removed by an
    # out-of-band schema edit. Either way, we still want to create
    # the canonical one below so the relationship exists.
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
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return

    live_name = _resolve_fk_name(bind) or _FK_NAME
    op.drop_constraint(live_name, "spice_routes", type_="foreignkey")
    op.create_foreign_key(
        _FK_NAME,
        "spice_routes",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
