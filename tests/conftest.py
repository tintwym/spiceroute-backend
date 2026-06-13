import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
# Pin the AI layer to stub mode in tests. Without this the client would
# probe `OLLAMA_BASE_URL` (default localhost:11434) on every test and
# fall back to stubs after a TCP failure, which is wasted time and a
# flake risk if the dev machine happens to be running Ollama.
os.environ.setdefault("AI_FORCE_STUB", "1")
os.environ.setdefault("CORS_ORIGINS", "*")
# Force Firebase dev-mode by pointing at a non-existent credentials path.
# In dev-mode the verifier accepts `dev:<uid>[:<email>][:<name>]` tokens.
os.environ.setdefault(
    "FIREBASE_CREDENTIALS_PATH", "/tmp/__no_such_firebase_creds.json"
)
# `app.main` enters LOCKDOWN MODE if dev-mode auth is active while
# DEBUG=false (safety gate against accidentally shipping dev-token
# acceptance to production). In that mode the service boots normally
# but `verify_id_token` rejects every credential with a 503. Tests
# legitimately run in dev mode and need `dev:<uid>` tokens to work,
# so flip DEBUG on here.
os.environ.setdefault("DEBUG", "true")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import *  # noqa: E402,F401,F403
from app.services.ai import rate_limit as _rate_limit  # noqa: E402


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    SessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(
    test_engine, monkeypatch
) -> AsyncGenerator[AsyncClient, None]:
    SessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    # Rate limiting uses Postgres-only SQL (INET cast, ON CONFLICT). In tests
    # we run on sqlite, so swap the checks for no-ops.
    async def _noop(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(_rate_limit, "check_recipe_quota", _noop)
    monkeypatch.setattr(_rate_limit, "check_chat_quota", _noop)

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


def auth_header(uid: str = "alice", email: str | None = None, name: str | None = None) -> dict[str, str]:
    """Construct an Authorization header that the dev-mode Firebase verifier
    will accept. Tokens take the form `dev:<uid>[:<email>][:<name>]`."""
    parts = ["dev", uid]
    if email is not None or name is not None:
        parts.append(email or "")
    if name is not None:
        parts.append(name)
    return {"Authorization": "Bearer " + ":".join(parts)}
