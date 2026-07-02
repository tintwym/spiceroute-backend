"""switch users table to firebase identities

Drops the password_hash column (we no longer store passwords; Firebase does)
and adds firebase_uid as the unique identity. Email becomes nullable because
Apple Sign-In with private relay can withhold it.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-06 06:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add firebase_uid as nullable first so we can backfill existing rows
    # (none in production yet, but be safe). Then enforce NOT NULL.
    op.add_column(
        "users",
        sa.Column("firebase_uid", sa.String(128), nullable=True),
    )
    # If any legacy rows exist (none expected in v0.2), seed a placeholder
    # so the NOT NULL + UNIQUE constraints succeed. Production safety net.
    op.execute(
        "UPDATE users SET firebase_uid = 'legacy:' || id::text "
        "WHERE firebase_uid IS NULL"
    )
    op.alter_column("users", "firebase_uid", nullable=False)
    op.create_unique_constraint(
        "uq_users_firebase_uid", "users", ["firebase_uid"]
    )
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"])

    # Email is no longer required and no longer required to be unique
    # (Apple's private relay can produce duplicates of `null` or stable
    # but per-app aliases). We keep the index for lookups.
    op.drop_index("ix_users_email", table_name="users")
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.alter_column("users", "email", nullable=True)
    op.create_index("ix_users_email", "users", ["email"])

    # password_hash is gone — Firebase owns credentials now.
    op.drop_column("users", "password_hash")


def downgrade() -> None:
    """One-way-ish migration.

    The upgrade deliberately drops `users.email`'s NOT NULL and UNIQUE
    constraints because Apple Sign-In with private relay can produce
    either NULL emails or stable-but-per-app aliases that may collide
    if the same human signs in twice. After running real users
    through the upgrade, the table will almost certainly contain
    duplicates or NULLs that would cause a naive `CREATE UNIQUE`
    here to fail mid-rollback and leave the schema half-migrated.

    Bail loudly BEFORE attempting the constraint create so the
    operator sees a clear, actionable error rather than a cryptic
    constraint-violation stack trace partway through the downgrade.
    """
    bind = op.get_bind()
    null_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE email IS NULL")
    ).scalar() or 0
    dupe_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM ("
            "  SELECT email FROM users WHERE email IS NOT NULL "
            "  GROUP BY email HAVING COUNT(*) > 1"
            ") AS dupes"
        )
    ).scalar() or 0
    if null_count > 0 or dupe_count > 0:
        raise RuntimeError(
            "Refusing to downgrade 0003: users.email has "
            f"{null_count} NULL rows and {dupe_count} duplicate-email "
            "groups. The downgrade re-applies NOT NULL + UNIQUE which "
            "would fail mid-migration. Resolve the data first (delete "
            "or merge the offending rows) then re-run."
        )

    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(255), nullable=True),
    )
    op.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
    op.alter_column("users", "password_hash", nullable=False)

    op.drop_index("ix_users_email", table_name="users")
    op.alter_column("users", "email", nullable=False)
    op.create_unique_constraint("users_email_key", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])

    op.drop_index("ix_users_firebase_uid", table_name="users")
    op.drop_constraint("uq_users_firebase_uid", "users", type_="unique")
    op.drop_column("users", "firebase_uid")
