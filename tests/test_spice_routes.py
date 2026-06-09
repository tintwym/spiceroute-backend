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
