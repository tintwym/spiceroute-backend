"""Auth integration tests (Firebase dev-mode tokens)."""
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
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


@pytest.mark.asyncio
async def test_lockdown_returns_503_with_generic_detail(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the server is in LOCKDOWN MODE (no Firebase creds + DEBUG
    off) authenticated requests must return 503, not 401, so the client
    can distinguish "your token is bad" from "the server isn't set up
    yet" and surface the right banner. And the response body MUST NOT
    name the missing env-var — that's operator-facing detail that
    belongs in server logs only.
    """
    # Flip DEBUG off on the cached settings singleton. The auth code
    # paths read `_settings.debug` and `_settings.firebase_dev_mode`
    # directly off the same object, so this single mutation pushes
    # both into LOCKDOWN MODE for the duration of the test.
    monkeypatch.setattr(get_settings(), "debug", False)

    r = await client.get(
        "/auth/me", headers=auth_header(uid="alice")
    )
    assert r.status_code == 503, r.text
    body = r.json()
    # Generic detail — no env-var name, no Firebase SDK text.
    detail = (body.get("detail") or "").lower()
    assert "firebase" not in detail
    assert "credentials" not in detail
    assert "env" not in detail


@pytest.mark.asyncio
async def test_lockdown_still_allows_public_endpoints(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Public endpoints (e.g. listing public recipes) MUST keep working
    in lockdown — only authenticated paths return 503. Otherwise an
    operator missing the Firebase env var would take the whole catalog
    offline.
    """
    monkeypatch.setattr(get_settings(), "debug", False)

    r = await client.get("/spice_routes")
    assert r.status_code == 200, r.text
