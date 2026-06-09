"""drop redundant indexes on users.email and tags.name

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-09 23:00:00

Migration 0001_initial created columns `users.email` and `tags.name` with
`unique=True`, which implicitly produces a UNIQUE B-tree index that Postgres
will pick for `WHERE email = ?` and `WHERE name = ?` lookups. The migration
then ALSO ran `op.create_index("ix_users_email", ...)` and
`op.create_index("ix_tags_name", ...)`, creating a SECOND non-unique B-tree
index on the same column.

The duplicates serve no query — Postgres always prefers the unique index,
which is cheaper to maintain. The non-unique copies just waste disk and
double the write amplification on INSERT/UPDATE.

This migration drops them. The unique indexes (auto-named
`users_email_key` and `tags_name_key` by Postgres) are preserved.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_tags_name", table_name="tags")


def downgrade() -> None:
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_tags_name", "tags", ["name"])
