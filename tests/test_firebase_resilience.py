"""Resilience guards for the Firebase verification path.

These tests pin the contract that a broken Firebase backend
configuration (malformed credentials JSON, missing service-account
file, ImportError, …) MUST NOT take public listing endpoints down
with it. The bug being guarded against: previously
`_ensure_initialized()` and the `from firebase_admin import auth`
import lived outside `verify_id_token`'s try/except, so any SDK
boot failure escaped as an uncaught exception and FastAPI returned
HTTP 500 for every request that carried an `Authorization` header
— including requests to public endpoints like `/spice_routes` that
should still serve their data to a "demoted to anonymous" caller.

The user-visible symptom was "Explore grid goes blank as soon as I
sign in" because the Flutter client's listRecipes call always
includes the Firebase token once the user is authed, and the
backend's 500 produced an ApiException that the explore controller
rendered as an empty state.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

import app.services.firebase as fb_module
from app.services.firebase import FirebaseTokenError, verify_id_token


@pytest.mark.asyncio
async def test_verify_id_token_wraps_init_failures_as_token_errors(
    monkeypatch,
) -> None:
    """If `_ensure_initialized` raises, `verify_id_token` must surface
    it as a `FirebaseTokenError` (which the optional-auth dep then
    cleanly demotes to anonymous) — NOT let the exception escape as
    an uncaught 500.
    """

    def _explode() -> None:
        raise RuntimeError("simulated firebase boot failure (bad JSON)")

    monkeypatch.setattr(fb_module, "_ensure_initialized", _explode)
    # `firebase_dev_mode` is a computed property on the pydantic
    # Settings; we can't monkeypatch the property itself but we
    # CAN flip the underlying field that feeds it so the dev-mode
    # short-circuit doesn't fire and we reach the init/import path
    # we're actually exercising here.
    monkeypatch.setattr(
        fb_module._settings,
        "firebase_credentials_json",
        '{"fake":"not used — _ensure_initialized is mocked"}',
    )

    with pytest.raises(FirebaseTokenError) as exc_info:
        await verify_id_token("any-token-shape")

    assert "simulated firebase boot failure" in str(exc_info.value)


@pytest.mark.asyncio
async def test_public_listing_works_even_when_firebase_init_broken(
    client: AsyncClient, db_session, monkeypatch
) -> None:
    """End-to-end version: when Firebase boot is broken and a caller
    hits `/spice_routes` with ANY Authorization header, the endpoint
    must still return the public listing (200 + JSON), NOT crash
    with HTTP 500.

    This is the regression case that took Explore offline for every
    signed-in user when the Render `FIREBASE_CREDENTIALS_JSON` env
    var was misconfigured. The Flutter client always sends the
    Firebase ID token once the user is authed; without this fence,
    a one-line Render misconfig blackholes the entire public-facing
    recipe grid.
    """
    from app.models.spice_route import SpiceRoute

    row = SpiceRoute(
        title="Ratatouille",
        description="Provençal stewed vegetables.",
        cuisine="french",
        language="en",
        prep_minutes=20,
        cook_minutes=40,
        servings=4,
        is_public=True,
        is_premium=True,
        spice_level=0,
    )
    db_session.add(row)
    await db_session.commit()

    def _explode() -> None:
        raise RuntimeError("simulated firebase boot failure")

    monkeypatch.setattr(fb_module, "_ensure_initialized", _explode)
    # Flip dev-mode off by populating the underlying credentials
    # field (the property derives from it). See the comment in the
    # unit test above for the rationale.
    monkeypatch.setattr(
        fb_module._settings,
        "firebase_credentials_json",
        '{"fake":"not used — _ensure_initialized is mocked"}',
    )

    # Send a token that doesn't trigger the dev-token short-circuit
    # so we actually reach _ensure_initialized() and prove the
    # wrapped-exception path resolves cleanly to "anonymous caller".
    r = await client.get(
        "/spice_routes",
        params={"limit": 1},
        headers={"Authorization": "Bearer eyJfake.token.shape"},
    )
    assert r.status_code == 200, (
        f"expected listing to survive broken auth init, got "
        f"{r.status_code}: {r.text}"
    )
    data = r.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Ratatouille"
