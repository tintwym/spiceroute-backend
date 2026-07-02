"""Unit tests for the dev-mode safety guardrail in `app.core.config`.

The guardrail's job is narrow but high-value: refuse to boot when ALL
THREE of the following are true at once —

    1. `firebase_dev_mode` is active (no Firebase service-account
       credentials resolved) AND
    2. `DEBUG=true`            (dev-mode tokens are actually accepted) AND
    3. `DATABASE_URL` points at a remote host (i.e. the dev-token
       writes would land in a production-shaped DB).

Any other combination — REAL MODE, LOCKDOWN MODE, or DEV MODE pointed
at a local DB — is safe and must be allowed through. These tests
construct `Settings` instances directly (not via env) so each scenario
is reproducible without leaking state across tests.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings

# ---------------------------------------------------------------------------
# is_local_database
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        # Common dev-machine targets — all of these have to keep working.
        "postgresql+asyncpg://u:p@localhost:5432/db",
        "postgresql+asyncpg://u:p@127.0.0.1:5432/db",
        "postgresql+asyncpg://u:p@[::1]:5432/db",
        # Docker-compose service name. Matches the default value of
        # `database_url` in Settings and the `db` service in
        # docker-compose.yml.
        "postgresql+asyncpg://spiceroute:spiceroute@db:5432/spiceroute",
        # Container → host laptop (used when the backend runs in a
        # container but Postgres is on the developer's host machine).
        "postgresql+asyncpg://u:p@host.docker.internal:5432/db",
        # SQLite / in-memory URLs have no hostname; the property
        # treats "no host" as local-by-construction.
        "sqlite+aiosqlite:///:memory:",
        "sqlite:///./local.db",
    ],
)
def test_is_local_database_true_for_local_targets(url: str) -> None:
    s = Settings(database_url=url)
    assert s.is_local_database is True


@pytest.mark.parametrize(
    "url",
    [
        # Real production-shaped hosts — none of these should slip past
        # the dev-mode guardrail. We deliberately enumerate variations
        # of the Neon URL because that's the host that bit us in the
        # incident this guardrail is named after.
        "postgresql+asyncpg://u:p@ep-withered-lab-ao2xvtq6.c-2.ap-southeast-1.aws.neon.tech/neondb?ssl=require",
        "postgresql+asyncpg://u:p@some-pooler.us-east-2.rds.amazonaws.com/db",
        "postgresql+asyncpg://u:p@dpg-xxx.singapore-postgres.render.com/db",
        # Innocuous-looking hostname that happens to NOT match the
        # allowlist. Better to be cautious here — if a future user
        # adds a new local-friendly hostname, the fix is one line in
        # the property, not a debugging session in production.
        "postgresql+asyncpg://u:p@my-laptop.local:5432/db",
    ],
)
def test_is_local_database_false_for_remote_targets(url: str) -> None:
    s = Settings(database_url=url)
    assert s.is_local_database is False


def test_is_local_database_is_case_insensitive() -> None:
    """Hostname comparisons in DNS are case-insensitive, so the
    allowlist must be too — otherwise `LOCALHOST` (uppercased by a
    Windows .env loader, say) would be treated as a remote host."""
    s = Settings(database_url="postgresql+asyncpg://u:p@LOCALHOST:5432/db")
    assert s.is_local_database is True


# ---------------------------------------------------------------------------
# assert_safe_dev_mode — the actual guardrail
# ---------------------------------------------------------------------------


def _settings(
    *,
    debug: bool,
    creds_json: str = "",
    database_url: str = "postgresql+asyncpg://u:p@localhost/db",
) -> Settings:
    """Build a Settings instance with explicit overrides.

    Pinning `firebase_credentials_path` to a definitely-missing path
    forces `firebase_dev_mode` into the "no creds" state UNLESS
    `creds_json` is non-empty (which short-circuits to REAL MODE)."""
    return Settings(
        debug=debug,
        firebase_credentials_path="/tmp/__nonexistent_for_test.json",
        firebase_credentials_json=creds_json,
        database_url=database_url,
    )


def test_real_mode_remote_db_allowed() -> None:
    """REAL MODE (Firebase creds present) — remote DB is the standard
    production deploy. Must not raise."""
    s = _settings(
        debug=False,
        creds_json='{"type":"service_account"}',
        database_url="postgresql+asyncpg://u:p@neon.example.com/db",
    )
    s.assert_safe_dev_mode()  # no raise


def test_lockdown_mode_remote_db_allowed() -> None:
    """LOCKDOWN MODE (no creds + DEBUG=false) — auth verifier rejects
    every token, so dev impersonation is impossible regardless of which
    DB the writes would land in. This is the "blueprint provisioned
    the infra but the operator hasn't pasted the Firebase key yet"
    state and MUST not block boot — the operator needs the service
    running to verify health checks before they can fix the cause."""
    s = _settings(
        debug=False,
        database_url="postgresql+asyncpg://u:p@neon.example.com/db",
    )
    s.assert_safe_dev_mode()  # no raise


def test_dev_mode_local_db_allowed() -> None:
    """DEV MODE pointed at a local DB — the intended developer
    experience. Must not raise."""
    s = _settings(
        debug=True,
        database_url="postgresql+asyncpg://u:p@localhost/db",
    )
    s.assert_safe_dev_mode()  # no raise


def test_dev_mode_sqlite_allowed() -> None:
    """The pytest suite itself runs in this configuration
    (`AI_FORCE_STUB=1`, `DEBUG=true`, sqlite in-memory). If the
    guardrail rejected this, every test would fail at conftest
    import. Keep this assertion in place as a smoke test for that
    exact combination."""
    s = _settings(debug=True, database_url="sqlite+aiosqlite:///:memory:")
    s.assert_safe_dev_mode()  # no raise


def test_dev_mode_remote_db_refuses() -> None:
    """The single failure mode this guardrail exists to catch: dev
    tokens are accepted AND a forgotten remote DATABASE_URL means any
    `dev:<uid>` API call writes to production. Must raise with a
    message that names the host and points at the three remediations."""
    s = _settings(
        debug=True,
        database_url="postgresql+asyncpg://u:p@neon.example.com/db",
    )
    with pytest.raises(RuntimeError) as exc_info:
        s.assert_safe_dev_mode()

    msg = str(exc_info.value)
    # Surface the offending host so the operator immediately sees
    # which database connection caused the refusal — not just "remote
    # DB" in the abstract.
    assert "neon.example.com" in msg
    # All three remediations must be present in the message; the
    # whole point of raising here is to give the operator a concrete
    # next step without making them read the source.
    assert "DATABASE_URL" in msg
    assert "FIREBASE_CREDENTIALS" in msg
    assert "DEBUG=false" in msg
