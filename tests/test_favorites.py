import pytest
from httpx import AsyncClient

from tests.conftest import auth


def sample(**o):
    base = {
        "title": "X",
        "is_public": True,
        "ingredients": [{"name": "a"}],
        "steps": [{"body": "b"}],
        "tags": [],
    }
    base.update(o)
    return base


@pytest.mark.asyncio
async def test_favorite_toggle(client: AsyncClient, alice_token: str, bob_token: str):
    create = await client.post(
        "/mecipes", json=sample(title="Alice public"), headers=auth(alice_token)
    )
    rid = create.json()["id"]

    res = await client.post(f"/mecipes/{rid}/favorite", headers=auth(bob_token))
    assert res.status_code == 200
    assert res.json()["favorited"] is True

    res = await client.post(f"/mecipes/{rid}/favorite", headers=auth(bob_token))
    assert res.json()["favorited"] is False


@pytest.mark.asyncio
async def test_favorites_only_filter(
    client: AsyncClient, alice_token: str, bob_token: str
):
    r1 = await client.post(
        "/mecipes", json=sample(title="r1"), headers=auth(alice_token)
    )
    await client.post("/mecipes", json=sample(title="r2"), headers=auth(alice_token))
    await client.post(
        f"/mecipes/{r1.json()['id']}/favorite", headers=auth(bob_token)
    )

    res = await client.get("/mecipes?favorites_only=true", headers=auth(bob_token))
    titles = [r["title"] for r in res.json()["items"]]
    assert titles == ["r1"]


@pytest.mark.asyncio
async def test_my_favorites(client: AsyncClient, alice_token: str, bob_token: str):
    r1 = await client.post(
        "/mecipes", json=sample(title="r1"), headers=auth(alice_token)
    )
    r2 = await client.post(
        "/mecipes", json=sample(title="r2"), headers=auth(alice_token)
    )
    for r in (r1, r2):
        await client.post(
            f"/mecipes/{r.json()['id']}/favorite", headers=auth(bob_token)
        )
    res = await client.get("/me/favorites", headers=auth(bob_token))
    assert {r["title"] for r in res.json()} == {"r1", "r2"}
    assert all(r["is_favorite"] for r in res.json())


@pytest.mark.asyncio
async def test_is_favorite_flag_in_list(
    client: AsyncClient, alice_token: str, bob_token: str
):
    r1 = await client.post(
        "/mecipes", json=sample(title="r1"), headers=auth(alice_token)
    )
    await client.post("/mecipes", json=sample(title="r2"), headers=auth(alice_token))
    await client.post(
        f"/mecipes/{r1.json()['id']}/favorite", headers=auth(bob_token)
    )

    res = await client.get("/mecipes", headers=auth(bob_token))
    by_title = {r["title"]: r for r in res.json()["items"]}
    assert by_title["r1"]["is_favorite"] is True
    assert by_title["r2"]["is_favorite"] is False


@pytest.mark.asyncio
async def test_favorites_endpoints_consistent_when_mecipe_made_private(
    client: AsyncClient, alice_token: str, bob_token: str
):
    """Regression: /me/favorites and /mecipes?favorites_only=true must agree
    on what's visible. Previously /me/favorites bypassed the visibility filter
    but /mecipes?favorites_only=true did not, so if Alice made a mecipe Bob
    favorited private, Bob would see different counts in the two endpoints.
    """
    create = await client.post(
        "/mecipes",
        json=sample(title="public-then-private"),
        headers=auth(alice_token),
    )
    rid = create.json()["id"]
    await client.post(f"/mecipes/{rid}/favorite", headers=auth(bob_token))

    # Sanity: both report 1
    favs = await client.get("/me/favorites", headers=auth(bob_token))
    listing = await client.get(
        "/mecipes?favorites_only=true", headers=auth(bob_token)
    )
    assert len(favs.json()) == 1
    assert len(listing.json()["items"]) == 1

    # Alice makes it private
    await client.patch(
        f"/mecipes/{rid}",
        json={"is_public": False},
        headers=auth(alice_token),
    )

    # Both endpoints should now hide it (Bob no longer has visibility)
    favs = await client.get("/me/favorites", headers=auth(bob_token))
    listing = await client.get(
        "/mecipes?favorites_only=true", headers=auth(bob_token)
    )
    assert len(favs.json()) == len(listing.json()["items"]), (
        f"/me/favorites returned {len(favs.json())} but "
        f"/mecipes?favorites_only returned {len(listing.json()['items'])}"
    )
    assert len(favs.json()) == 0


@pytest.mark.asyncio
async def test_pagination(client: AsyncClient, alice_token: str):
    for i in range(5):
        await client.post(
            "/mecipes", json=sample(title=f"r{i}"), headers=auth(alice_token)
        )
    res = await client.get("/mecipes?limit=2&offset=0")
    page1 = res.json()
    assert len(page1["items"]) == 2
    assert page1["total"] == 5

    res = await client.get("/mecipes?limit=2&offset=2")
    page2 = res.json()
    assert len(page2["items"]) == 2

    titles1 = {r["title"] for r in page1["items"]}
    titles2 = {r["title"] for r in page2["items"]}
    assert titles1.isdisjoint(titles2)
