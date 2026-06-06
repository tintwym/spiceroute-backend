"""Auth integration tests (Firebase dev-mode tokens)."""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_me_requires_token(client: AsyncClient) -> None:
    r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_lazily_provisions_user(client: AsyncClient) -> None:
    headers = auth_header(uid="alice", email="alice@example.com", name="Alice")
    r = await client.get("/auth/me", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["firebase_uid"] == "alice"
    assert body["email"] == "alice@example.com"
    assert body["display_name"] == "Alice"

    # A second call returns the same row (no duplicate inserts).
    r2 = await client.get("/auth/me", headers=headers)
    assert r2.json()["id"] == body["id"]


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient) -> None:
    r = await client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-valid-token"}
    )
    assert r.status_code == 401
