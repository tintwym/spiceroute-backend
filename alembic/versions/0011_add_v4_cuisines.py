"""add v4 cuisines to cuisine_type enum

Phase 1 (fill empty / sparse regions): lebanese, turkish, moroccan, ethiopian
(seed Middle East & Africa from zero), filipino (Maritime SE Asia), pakistani
+ sri_lankan (balance South Asia), cambodian (round out Mainland SE Asia).

Phase 2 (opportunistic expansion + umbrella cuisines): brazilian, peruvian,
taiwanese, portuguese, british plus two umbrellas (caribbean, eastern_european)
deliberately kept at the cluster level instead of country-by-country to avoid
the granularity trap (a "Maldivian" pill with three recipes is worse than no
pill at all).

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-15 10:30:00

Same shape as `0009_add_five_cuisines.py`: PG enums require an out-of-tx
`ALTER TYPE ... ADD VALUE`, and there's no clean way to remove an enum value
once written, so downgrade is intentionally a no-op.

Each value is added as a separate `ALTER TYPE` because that statement must
run outside the surrounding migration transaction. `IF NOT EXISTS` makes the
script idempotent — safe to re-run on databases patched by hand before the
migration landed.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_CUISINES = (
    # Phase 1
    "lebanese",
    "turkish",
    "moroccan",
    "ethiopian",
    "filipino",
    "pakistani",
    "sri_lankan",
    "cambodian",
    # Phase 2
    "brazilian",
    "peruvian",
    "caribbean",
    "taiwanese",
    "portuguese",
    "british",
    "eastern_european",
)


def upgrade() -> None:
    for value in _NEW_CUISINES:
        op.execute(f"ALTER TYPE cuisine_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Dropping an enum value in Postgres requires tearing the type down and
    # rebuilding it plus recasting the column, and any rows already written
    # with these values would have to be migrated or deleted first. Not
    # worth it for an additive change — leave the values in place on
    # downgrade.
    pass
