"""CRUD tests for /spice_routes (Firebase-auth gated writes, anon reads)."""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


def _recipe_payload(**overrides):
    return {
        "title": "Pad Thai",
        "description": "Quick stir-fried rice noodles.",
        "prep_minutes": 10,
        "cook_minutes": 8,
        "servings": 2,
        "cuisine": "thai",
        "language": "en",
        "spice_level": 2,
        "ingredients": [
            {"quantity": 200, "unit": "g", "name": "rice noodles"},
            {"name": "tamarind paste"},
        ],
        "steps": [
            {"body": "Soak the rice noodles."},
            {"body": "Stir-fry with sauce."},
        ],
        "tags": ["thai", "noodles"],
        **overrides,
    }


@pytest.mark.asyncio
async def test_list_empty(client: AsyncClient) -> None:
    r = await client.get("/spice_routes")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_anonymous_create_is_rejected(client: AsyncClient) -> None:
    r = await client.post("/spice_routes", json=_recipe_payload())
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_authed_create_then_read(client: AsyncClient) -> None:
    headers = auth_header(uid="alice", email="alice@example.com", name="Alice")
    r = await client.post(
        "/spice_routes", json=_recipe_payload(), headers=headers
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "Pad Thai"
    assert body["owner"]["display_name"] == "Alice"
    assert body["is_premium"] is False
    rid = body["id"]

    # Anyone can read a public recipe.
    r = await client.get(f"/spice_routes/{rid}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_user_cannot_force_premium(client: AsyncClient) -> None:
    # The server now LOUDLY rejects client-set `is_premium=True` at
    # schema validation (422) instead of silently coercing to False
    # (201). Silent coercion was masking client bugs — a client
    # thinking it had successfully published a "premium" recipe had
    # no way to know its is_premium flag was being dropped.
    r = await client.post(
        "/spice_routes",
        json=_recipe_payload(title="Sneaky", is_premium=True),
        headers=auth_header(uid="bob"),
    )
    assert r.status_code == 422, r.text
    assert "is_premium" in r.text


@pytest.mark.asyncio
async def test_user_can_explicitly_set_is_premium_false(client: AsyncClient) -> None:
    # Explicit False is fine — it's the default and matches what
    # the server hardcodes anyway. Only `True` is rejected.
    r = await client.post(
        "/spice_routes",
        json=_recipe_payload(title="Honest", is_premium=False),
        headers=auth_header(uid="bob"),
    )
    assert r.status_code == 201, r.text
    assert r.json()["is_premium"] is False


@pytest.mark.asyncio
async def test_owner_can_patch_and_delete(client: AsyncClient) -> None:
    headers = auth_header(uid="carol")
    r = await client.post("/spice_routes", json=_recipe_payload(), headers=headers)
    rid = r.json()["id"]

    r = await client.patch(
        f"/spice_routes/{rid}",
        json={"title": "Spicy Pad Thai", "spice_level": 3},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "Spicy Pad Thai"
    assert r.json()["spice_level"] == 3

    r = await client.delete(f"/spice_routes/{rid}", headers=headers)
    assert r.status_code == 204
    assert (await client.get(f"/spice_routes/{rid}")).status_code == 404


@pytest.mark.asyncio
async def test_non_owner_cannot_patch_or_delete(client: AsyncClient) -> None:
    alice = auth_header(uid="alice")
    bob = auth_header(uid="bob")
    rid = (
        await client.post("/spice_routes", json=_recipe_payload(), headers=alice)
    ).json()["id"]

    # Bob masquerading as alice's recipe -> 404 (we deliberately don't 403).
    r = await client.patch(
        f"/spice_routes/{rid}", json={"title": "hijack"}, headers=bob
    )
    assert r.status_code == 404
    r = await client.delete(f"/spice_routes/{rid}", headers=bob)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_and_delete_require_auth(client: AsyncClient) -> None:
    alice = auth_header(uid="alice")
    rid = (
        await client.post("/spice_routes", json=_recipe_payload(), headers=alice)
    ).json()["id"]

    assert (await client.patch(f"/spice_routes/{rid}", json={})).status_code == 401
    assert (await client.delete(f"/spice_routes/{rid}")).status_code == 401


@pytest.mark.asyncio
async def test_cuisine_filter(client: AsyncClient) -> None:
    headers = auth_header(uid="alice")
    for spec in [
        {"title": "Italian Toast", "cuisine": "italian"},
        {"title": "Korean Bowl", "cuisine": "korean"},
        {"title": "Thai Bowl", "cuisine": "thai"},
    ]:
        await client.post(
            "/spice_routes", json=_recipe_payload(**spec), headers=headers
        )

    r = await client.get("/spice_routes", params={"cuisine": "thai"})
    assert r.status_code == 200
    titles = [i["title"] for i in r.json()["items"]]
    assert titles == ["Thai Bowl"]


@pytest.mark.asyncio
async def test_private_recipe_not_visible_to_others(client: AsyncClient) -> None:
    alice = auth_header(uid="alice")
    bob = auth_header(uid="bob")
    rid = (
        await client.post(
            "/spice_routes",
            json=_recipe_payload(title="Secret", is_public=False),
            headers=alice,
        )
    ).json()["id"]

    # Anonymous list excludes it.
    items = (await client.get("/spice_routes")).json()["items"]
    assert all(i["id"] != rid for i in items)

    # Bob can't read it.
    assert (await client.get(f"/spice_routes/{rid}", headers=bob)).status_code == 404

    # Alice can.
    assert (await client.get(f"/spice_routes/{rid}", headers=alice)).status_code == 200


@pytest.mark.asyncio
async def test_mine_filter(client: AsyncClient) -> None:
    alice = auth_header(uid="alice")
    bob = auth_header(uid="bob")
    await client.post(
        "/spice_routes", json=_recipe_payload(title="Alice 1"), headers=alice
    )
    await client.post(
        "/spice_routes",
        json=_recipe_payload(title="Alice private", is_public=False),
        headers=alice,
    )
    await client.post(
        "/spice_routes", json=_recipe_payload(title="Bob 1"), headers=bob
    )

    r = await client.get("/spice_routes", params={"mine": "true"}, headers=alice)
    titles = sorted(i["title"] for i in r.json()["items"])
    assert titles == ["Alice 1", "Alice private"]

    r = await client.get("/spice_routes", params={"mine": "true"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_translate_to_swaps_title_and_description(
    client: AsyncClient, db_session
) -> None:
    """`?translate_to=<locale>` overlays the per-locale title +
    description on the response. Locales not present in `translations`
    fall back silently to the source columns; rows whose `translations`
    is null/empty are unaffected.

    Regression guard for the "Burmese UI shows English Quiche Lorraine
    title + description" bug — without per-locale overrides + the
    `translate_to` query param the seeded English copy would leak into
    every non-English user's grid forever.
    """
    from app.models.spice_route import SpiceRoute

    row = SpiceRoute(
        title="Quiche Lorraine",
        description="Buttery shortcrust filled with bacon, eggs, and cream.",
        cuisine="french",
        language="en",
        prep_minutes=30,
        cook_minutes=45,
        servings=6,
        is_public=True,
        is_premium=True,
        spice_level=0,
        translations={
            "ko": {
                "title": "키슈 로렌",
                "description": "버터 향 가득한 쇼트크러스트에 베이컨과 크림.",
            },
            # Burmese intentionally omits "title" — the fallback path
            # should keep the original "Quiche Lorraine" but swap in
            # the Burmese description, which is the exact contract
            # the curated seed relies on for dishes whose names have
            # no settled Burmese transliteration.
            "my": {"description": "ပြင်သစ်ဆား​လက်ပန်း"},
        },
    )
    db_session.add(row)
    await db_session.commit()

    # No translate_to: source columns flow through untouched, and
    # the JSONB `translations` blob never leaks into the wire shape.
    r = await client.get("/spice_routes")
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["title"] == "Quiche Lorraine"
    assert "Buttery shortcrust" in item["description"]
    assert "translations" not in item

    # Korean: both title AND description get swapped.
    r = await client.get("/spice_routes", params={"translate_to": "ko"})
    item = r.json()["items"][0]
    assert item["title"] == "키슈 로렌"
    assert item["description"] == "버터 향 가득한 쇼트크러스트에 베이컨과 크림."

    # Burmese: title falls back (no override), description swaps.
    r = await client.get("/spice_routes", params={"translate_to": "my"})
    item = r.json()["items"][0]
    assert item["title"] == "Quiche Lorraine"
    assert item["description"] == "ပြင်သစ်ဆား​လက်ပန်း"

    # Vietnamese: not in translations — silent fall-through to source.
    r = await client.get("/spice_routes", params={"translate_to": "vi"})
    item = r.json()["items"][0]
    assert item["title"] == "Quiche Lorraine"
    assert "Buttery shortcrust" in item["description"]

    # Detail endpoint follows the same contract.
    rid = item["id"]
    detail = (
        await client.get(
            f"/spice_routes/{rid}", params={"translate_to": "ko"}
        )
    ).json()
    assert detail["title"] == "키슈 로렌"


@pytest.mark.asyncio
async def test_translate_to_ignores_rows_without_translations(
    client: AsyncClient, db_session
) -> None:
    """Rows whose `translations` column is NULL pass through unchanged
    regardless of the `translate_to` value. The 30 curated seeds that
    haven't been hand-translated yet rely on this — they should keep
    serving English content while the localised copy gets backfilled
    rather than 500ing or going blank.
    """
    from app.models.spice_route import SpiceRoute

    row = SpiceRoute(
        title="Bibimbap",
        description="Mixed rice bowl.",
        cuisine="korean",
        language="en",
        prep_minutes=25,
        cook_minutes=15,
        servings=2,
        is_public=True,
        is_premium=True,
        spice_level=1,
        translations=None,
    )
    db_session.add(row)
    await db_session.commit()

    r = await client.get("/spice_routes", params={"translate_to": "ko"})
    item = r.json()["items"][0]
    assert item["title"] == "Bibimbap"
    assert item["description"] == "Mixed rice bowl."


@pytest.mark.asyncio
async def test_translate_to_does_not_mutate_source_row(
    client: AsyncClient, db_session
) -> None:
    """Critical safety regression: hitting `?translate_to=<locale>`
    must NOT persist the translated string back into
    `spice_routes.title` / `description`. Earlier versions of the
    overlay mutated the ORM row in place; that worked only because
    the read endpoints don't currently commit, but any future code
    path that triggered a commit on the same session (a future write
    endpoint sharing the session, a middleware, or just an
    accidental `await db.commit()`) would have silently corrupted
    the seed data with the translated string.

    The refactor returns an override tuple instead of writing to the
    row — this test pins that contract by issuing the translate
    request, then re-reading the row directly from the DB and
    asserting the source columns are untouched.
    """
    from sqlalchemy import select

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
        translations={
            "ko": {
                "title": "라따뚜이",
                "description": "프로방스식 채소 스튜.",
            },
        },
    )
    db_session.add(row)
    await db_session.commit()
    row_id = row.id

    r = await client.get("/spice_routes", params={"translate_to": "ko"})
    assert r.json()["items"][0]["title"] == "라따뚜이"

    detail = await client.get(
        f"/spice_routes/{row_id}", params={"translate_to": "ko"}
    )
    assert detail.json()["title"] == "라따뚜이"

    # Round-trip the row from the DB to prove the source columns
    # weren't silently mutated by the overlay path. expire_all() is
    # needed because the session may still hold the cached attrs
    # from the test's initial insert.
    db_session.expire_all()
    persisted = (
        await db_session.execute(
            select(SpiceRoute).where(SpiceRoute.id == row_id)
        )
    ).scalar_one()
    assert persisted.title == "Ratatouille"
    assert persisted.description == "Provençal stewed vegetables."


@pytest.mark.asyncio
async def test_translate_to_survives_malformed_translations(
    client: AsyncClient, db_session
) -> None:
    """Defensive regression: `/spice_routes?translate_to=…` must not
    500 when a row's `translations` JSONB column has drifted from
    the documented `dict | None` shape.

    The model types `translations` as `dict | None`, but the
    underlying Postgres JSONB column will faithfully return whatever
    JSON value got stored. A buggy future writer (or a hand-crafted
    UPDATE in psql) could plant a list, string, int, or a per-locale
    bundle that itself isn't a dict. The previous implementation
    called `.get(locale)` on whatever shape was returned, which
    raises AttributeError on any non-dict — taking the entire
    Explore listing down with HTTP 500 for every authenticated
    client across the app.

    This test pins the contract: every malformed shape silently
    falls back to the source columns (`title`, `description`),
    matching the "no translation available for this locale" branch.
    """
    from app.models.spice_route import SpiceRoute

    rows = [
        # `translations` is a JSON list — `.get()` would raise.
        SpiceRoute(
            title="ListShaped",
            description="src desc 1",
            cuisine="french",
            language="en",
            prep_minutes=5,
            cook_minutes=5,
            servings=1,
            is_public=True,
            is_premium=True,
            spice_level=0,
            translations=["ko", "ja"],
        ),
        # `translations[ko]` is a string — `.get("title")` would raise.
        SpiceRoute(
            title="StringBundle",
            description="src desc 2",
            cuisine="french",
            language="en",
            prep_minutes=5,
            cook_minutes=5,
            servings=1,
            is_public=True,
            is_premium=True,
            spice_level=0,
            translations={"ko": "not a dict"},
        ),
        # `translations[ko].title` is an int — coerce to None,
        # serializer must not see a non-string.
        SpiceRoute(
            title="IntTitle",
            description="src desc 3",
            cuisine="french",
            language="en",
            prep_minutes=5,
            cook_minutes=5,
            servings=1,
            is_public=True,
            is_premium=True,
            spice_level=0,
            translations={"ko": {"title": 123, "description": "ok"}},
        ),
        # `translations[ko].title` is an empty string — fallback to
        # source column rather than rendering a blank tile.
        SpiceRoute(
            title="EmptyTitle",
            description="src desc 4",
            cuisine="french",
            language="en",
            prep_minutes=5,
            cook_minutes=5,
            servings=1,
            is_public=True,
            is_premium=True,
            spice_level=0,
            translations={"ko": {"title": "", "description": "ok"}},
        ),
    ]
    for row in rows:
        db_session.add(row)
    await db_session.commit()

    r = await client.get("/spice_routes", params={"translate_to": "ko"})
    assert r.status_code == 200, r.text
    by_title = {item["title"]: item for item in r.json()["items"]}

    # List-shaped translations: full fallback to source columns.
    assert by_title["ListShaped"]["description"] == "src desc 1"

    # String-shaped bundle: full fallback to source columns.
    assert by_title["StringBundle"]["description"] == "src desc 2"

    # Int title: coerced to None, source title is rendered, but the
    # valid string description still wins.
    assert by_title["IntTitle"]["description"] == "ok"

    # Empty-string title: collapses to None, source title shows.
    assert by_title["EmptyTitle"]["description"] == "ok"
