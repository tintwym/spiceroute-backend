"""add v5 East Asia regional cuisines to cuisine_type enum

Expands the East Asia region from 4 → 30 cuisines by appending 26
regional / national cuisines (Mongolian, Tibetan, Hong Kong, Macanese,
Sichuan, Cantonese, Shanghainese, Fujian, Hunan, Yunnan, Beijing,
Dongbei, Hakka, Uyghur, Okinawan, Shandong, Guangxi, Teochew,
Hainanese, Jiangsu, Zhejiang, Anhui, Jiangxi, Guizhou, Manchurian,
Shaanxi).

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-17 12:00:00
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_CUISINES = (
    "mongolian",
    "tibetan",
    "hong_kong",
    "macanese",
    "sichuan",
    "cantonese",
    "shanghainese",
    "fujian",
    "hunan",
    "yunnan",
    "beijing",
    "dongbei",
    "hakka",
    "uyghur",
    "okinawan",
    "shandong",
    "guangxi",
    "teochew",
    "hainanese",
    "jiangsu",
    "zhejiang",
    "anhui",
    "jiangxi",
    "guizhou",
    "manchurian",
    "shaanxi",
)


def upgrade() -> None:
    for value in _NEW_CUISINES:
        op.execute(f"ALTER TYPE cuisine_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    pass
