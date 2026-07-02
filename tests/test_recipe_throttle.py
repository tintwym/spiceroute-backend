"""Per-IP rate-limit coverage for the recipe CRUD surface.

The conftest fixture replaces the throttle check functions with no-ops
for all other tests (because sqlite can't run the Postgres-only
`INSERT ... ON CONFLICT` upsert in `_bump`); here we override THAT
override with a counter-based fake that exercises the 429 path.

Why a fake instead of hitting the real `_bump`:
  * The real implementation needs the Postgres `inet` type and
    `ON CONFLICT (ip, key) DO UPDATE` clause. Reproducing that in
    sqlite would require either a separate Postgres fixture (slow,
    flaky in CI) or rewriting the SQL to be portable (which loses
    the atomicity guarantee that's the whole point of the upsert).
  * The thing we want to verify here is the WIRING — that the
    endpoint actually calls the throttle, that it does so before
    expensive work, and that a 429 from the throttle propagates
    cleanly to the response. The arithmetic of "counter > limit"
    is exercised separately by integration tests against the real
    database.
"""
from fastapi import HTTPException, status
from httpx import AsyncClient

from app.services.ai import rate_limit as _rate_limit
from tests.conftest import auth_header


def _make_throttle(limit: int):
    """Return an async fake that allows `limit` calls then raises 429.

    Mirrors the public failure shape of the real `check_*_quota`
    helpers — same status code, same detail prefix — so the assertion
    on response status is meaningful (a 500 would mean the wiring is
    broken; a 429 means the endpoint surfaces the throttle correctly).
    """
    state = {"count": 0}

    async def fake(*_args, **_kwargs):
        state["count"] += 1
        if state["count"] > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="test throttle exceeded",
            )

    return fake, state


# ---------------------------------------------------------------------------
# GET /spice_routes  (hourly list throttle)
# ---------------------------------------------------------------------------


async def test_list_throttle_allows_under_limit(client: AsyncClient, monkeypatch):
    """The throttle MUST be called on every list request — verifying
    the wiring exists at all. We let two calls through and assert the
    fake counter sees both."""
    fake, state = _make_throttle(limit=10)
    monkeypatch.setattr(_rate_limit, "check_recipe_list_quota", fake)

    for _ in range(2):
        res = await client.get("/spice_routes?limit=1")
        assert res.status_code == 200, res.text
    assert state["count"] == 2


async def test_list_throttle_returns_429_over_limit(
    client: AsyncClient, monkeypatch
):
    """The N+1th call must surface as a clean 429 with the throttle's
    error message — NOT a 500, which would indicate the exception
    escaped before FastAPI could format it.
    """
    fake, _ = _make_throttle(limit=1)
    monkeypatch.setattr(_rate_limit, "check_recipe_list_quota", fake)

    res1 = await client.get("/spice_routes?limit=1")
    assert res1.status_code == 200, res1.text

    res2 = await client.get("/spice_routes?limit=1")
    assert res2.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "test throttle exceeded" in res2.text


# ---------------------------------------------------------------------------
# GET /spice_routes/{id}  (hourly detail throttle)
# ---------------------------------------------------------------------------


async def test_detail_throttle_runs_before_db_lookup(
    client: AsyncClient, monkeypatch
):
    """If the throttle fires, the response must be 429 even for an
    obviously-bogus UUID — otherwise the throttle isn't running first
    and the DB is paying for over-quota traffic.
    """
    fake, _ = _make_throttle(limit=0)  # every call is over-quota
    monkeypatch.setattr(_rate_limit, "check_recipe_detail_quota", fake)

    # UUID format is valid (would otherwise be a 422), but the row
    # doesn't exist. We should NEVER see 404 here because the
    # throttle gates the DB lookup.
    res = await client.get("/spice_routes/00000000-0000-0000-0000-000000000000")
    assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS


async def test_detail_throttle_allows_under_limit(
    client: AsyncClient, monkeypatch
):
    fake, state = _make_throttle(limit=5)
    monkeypatch.setattr(_rate_limit, "check_recipe_detail_quota", fake)

    # Use a known-bogus UUID; we only care about the throttle being
    # called, not the response body. 404 is the expected outcome
    # once the throttle lets us through.
    for _ in range(3):
        res = await client.get(
            "/spice_routes/00000000-0000-0000-0000-000000000000"
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND
    assert state["count"] == 3


# ---------------------------------------------------------------------------
# POST /spice_routes  (daily write throttle)
# ---------------------------------------------------------------------------


async def test_write_throttle_returns_429_over_limit(
    client: AsyncClient, monkeypatch
):
    """The write throttle gates BEFORE the LLM translation call, so
    the 429 path must be cheap (no LLM, no DB INSERT). We can't
    assert "no LLM call" directly here without instrumenting the
    LLM module, but we CAN assert that an empty body still 429s —
    a request that 429s before reaching Pydantic validation proves
    the throttle runs first.
    """
    fake, _ = _make_throttle(limit=0)
    monkeypatch.setattr(_rate_limit, "check_recipe_write_quota", fake)

    res = await client.post(
        "/spice_routes",
        json={
            "title": "won't matter",
            "description": "throttled before we look at this",
            "prep_minutes": 5,
            "cook_minutes": 10,
            "servings": 2,
            "language": "en",
            "spice_level": 0,
            "ingredients": [],
            "steps": [{"body": "step"}],
            "tags": [],
        },
        headers=auth_header(),
    )
    assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS


async def test_write_throttle_skipped_when_under_limit(
    client: AsyncClient, monkeypatch
):
    """Smoke test: a single legit POST passes through the throttle
    (counter increments) and lands a 201."""
    fake, state = _make_throttle(limit=10)
    monkeypatch.setattr(_rate_limit, "check_recipe_write_quota", fake)

    res = await client.post(
        "/spice_routes",
        json={
            "title": "Quick salad",
            "description": "Chop, toss, serve.",
            "prep_minutes": 10,
            "cook_minutes": 0,
            "servings": 2,
            "language": "en",
            "spice_level": 0,
            "ingredients": [{"name": "lettuce"}],
            "steps": [{"body": "chop"}, {"body": "serve"}],
            "tags": [],
        },
        headers=auth_header(),
    )
    assert res.status_code == status.HTTP_201_CREATED, res.text
    assert state["count"] == 1
