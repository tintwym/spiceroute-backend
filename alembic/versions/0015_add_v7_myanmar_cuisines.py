"""add v7 Myanmar regional cuisines to cuisine_type enum

Expands Myanmar from a single national `burmese` cuisine to 21 by
appending 20 regional / ethnic cuisines (Shan, Rakhine, Mon, Kachin,
Kayin, Chin, Kayah, Mandalay, Yangon, Ayeyarwady, Tanintharyi, Intha,
Naga, Pa'O, Danu, Wa, Magway, Bago, Sagaing, Taunggyi).

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-18 12:00:00
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_CUISINES = (
    "shan",
    "rakhine",
    "mon",
    "kachin",
    "kayin",
    "chin",
    "kayah",
    "mandalay",
    "yangon",
    "ayeyarwady",
    "tanintharyi",
    "intha",
    "naga",
    "pa_o",
    "danu",
    "wa",
    "magway",
    "bago",
    "sagaing",
    "taunggyi",
)


def upgrade() -> None:
    for value in _NEW_CUISINES:
        op.execute(f"ALTER TYPE cuisine_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    pass
