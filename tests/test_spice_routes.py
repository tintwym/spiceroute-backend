import pytest
from httpx import AsyncClient

from tests.conftest import auth


def sample_spice_route(**overrides):
    base = {
        "title": "Pad See Ew",
        "description": "Thai stir-fried noodles",
        "prep_minutes": 15,
        "cook_minutes": 10,
        "servings": 2,
        "is_public": True,
        "ingredients": [
            {"quantity": 200, "unit": "g", "name": "wide rice noodles"},
            {"quantity": 2, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "cup", "name": "Chinese broccoli"},
        ],
        "steps": [
            {"body": "Soak noodles in warm water."},
            {"body": "Stir-fry sauce and noodles."},
            {"body": "Add greens, toss, serve."},
        ],
        "tags": ["Thai", "Noodles", "weeknight"],
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_create_and_get_spice_route(client: AsyncClient, alice_token: str):
    res = await client.post("/spice_routes", json=sample_spice_route(), headers=auth(alice_token))
    assert res.status_code == 201, res.text
    body = res.json()
    rid = body["id"]
    assert body["title"] == "Pad See Ew"
    assert len(body["ingredients"]) == 3
    assert len(body["steps"]) == 3
    assert sorted(t["name"] for t in body["tags"]) == ["noodles", "thai", "weeknight"]
    assert body["owner"]["display_name"] == "Alice"

    res = await client.get(f"/spice_routes/{rid}", headers=auth(alice_token))
    assert res.status_code == 200
    assert res.json()["id"] == rid


@pytest.mark.asyncio
async def test_create_requires_auth(client: AsyncClient):
    res = await client.post("/spice_routes", json=sample_spice_route())
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_returns_public_and_own(
    client: AsyncClient, alice_token: str, bob_token: str
):
    await client.post(
        "/spice_routes",
        json=sample_spice_route(title="Alice private", is_public=False),
        headers=auth(alice_token),
    )
    await client.post(
        "/spice_routes",
        json=sample_spice_route(title="Alice public", is_public=True),
        headers=auth(alice_token),
    )
    await client.post(
        "/spice_routes",
        json=sample_spice_route(title="Bob public", is_public=True),
        headers=auth(bob_token),
    )

    res = await client.get("/spice_routes")
    titles = {r["title"] for r in res.json()["items"]}
    assert titles == {"Alice public", "Bob public"}

    res = await client.get("/spice_routes", headers=auth(alice_token))
    titles = {r["title"] for r in res.json()["items"]}
    assert titles == {"Alice public", "Alice private", "Bob public"}


@pytest.mark.asyncio
async def test_search_by_title(client: AsyncClient, alice_token: str):
    await client.post(
        "/spice_routes",
        json=sample_spice_route(title="Spaghetti Carbonara"),
        headers=auth(alice_token),
    )
    await client.post(
        "/spice_routes",
        json=sample_spice_route(title="Lemon Tart"),
        headers=auth(alice_token),
    )
    res = await client.get("/spice_routes?q=spaghetti")
    titles = [r["title"] for r in res.json()["items"]]
    assert titles == ["Spaghetti Carbonara"]


@pytest.mark.asyncio
async def test_search_by_ingredient(client: AsyncClient, alice_token: str):
    await client.post(
        "/spice_routes",
        json=sample_spice_route(
            title="Carbonara",
            ingredients=[{"name": "guanciale", "quantity": 100, "unit": "g"}],
        ),
        headers=auth(alice_token),
    )
    await client.post(
        "/spice_routes",
        json=sample_spice_route(
            title="Cacio e Pepe",
            ingredients=[{"name": "pecorino", "quantity": 50, "unit": "g"}],
        ),
        headers=auth(alice_token),
    )
    res = await client.get("/spice_routes?q=guanciale")
    titles = [r["title"] for r in res.json()["items"]]
    assert titles == ["Carbonara"]


@pytest.mark.asyncio
async def test_filter_by_tag_and_max_minutes(client: AsyncClient, alice_token: str):
    await client.post(
        "/spice_routes",
        json=sample_spice_route(title="Quick Thai", tags=["thai"], prep_minutes=5, cook_minutes=10),
        headers=auth(alice_token),
    )
    await client.post(
        "/spice_routes",
        json=sample_spice_route(title="Slow Italian", tags=["italian"], prep_minutes=30, cook_minutes=60),
        headers=auth(alice_token),
    )
    res = await client.get("/spice_routes?tag=thai")
    titles = [r["title"] for r in res.json()["items"]]
    assert titles == ["Quick Thai"]

    res = await client.get("/spice_routes?max_minutes=30")
    titles = [r["title"] for r in res.json()["items"]]
    assert titles == ["Quick Thai"]


@pytest.mark.asyncio
async def test_update_spice_route(client: AsyncClient, alice_token: str):
    create = await client.post(
        "/spice_routes", json=sample_spice_route(), headers=auth(alice_token)
    )
    rid = create.json()["id"]
    res = await client.patch(
        f"/spice_routes/{rid}",
        json={"title": "Updated", "tags": ["dessert"]},
        headers=auth(alice_token),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "Updated"
    assert [t["name"] for t in body["tags"]] == ["dessert"]


@pytest.mark.asyncio
async def test_non_owner_cannot_update_or_delete(
    client: AsyncClient, alice_token: str, bob_token: str
):
    create = await client.post(
        "/spice_routes", json=sample_spice_route(), headers=auth(alice_token)
    )
    rid = create.json()["id"]
    res = await client.patch(
        f"/spice_routes/{rid}", json={"title": "Bob's edit"}, headers=auth(bob_token)
    )
    assert res.status_code == 403
    res = await client.delete(f"/spice_routes/{rid}", headers=auth(bob_token))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_delete_spice_route(client: AsyncClient, alice_token: str):
    create = await client.post(
        "/spice_routes", json=sample_spice_route(), headers=auth(alice_token)
    )
    rid = create.json()["id"]
    res = await client.delete(f"/spice_routes/{rid}", headers=auth(alice_token))
    assert res.status_code == 204
    res = await client.get(f"/spice_routes/{rid}", headers=auth(alice_token))
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_private_spice_route_invisible_to_others(
    client: AsyncClient, alice_token: str, bob_token: str
):
    create = await client.post(
        "/spice_routes",
        json=sample_spice_route(is_public=False),
        headers=auth(alice_token),
    )
    rid = create.json()["id"]
    res = await client.get(f"/spice_routes/{rid}", headers=auth(bob_token))
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_tags_endpoint(client: AsyncClient, alice_token: str):
    await client.post(
        "/spice_routes",
        json=sample_spice_route(tags=["Thai", "spicy"]),
        headers=auth(alice_token),
    )
    res = await client.get("/tags")
    names = [t["name"] for t in res.json()]
    assert "thai" in names
    assert "spicy" in names

    res = await client.get("/tags?q=sp")
    names = [t["name"] for t in res.json()]
    assert names == ["spicy"]
