import io

import pytest
from httpx import AsyncClient

from tests.conftest import auth


# Smallest valid 1x1 PNG
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_spice_route_payload(title: str = "T"):
    return {
        "title": title,
        "ingredients": [{"name": "x"}],
        "steps": [{"body": "y"}],
        "tags": [],
    }


@pytest.mark.asyncio
async def test_upload_image_success(client: AsyncClient, alice_token: str):
    create = await client.post(
        "/spice_routes", json=make_spice_route_payload(), headers=auth(alice_token)
    )
    rid = create.json()["id"]
    res = await client.post(
        f"/spice_routes/{rid}/image",
        files={"file": ("hero.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=auth(alice_token),
    )
    assert res.status_code == 200, res.text
    assert res.json()["image_url"].startswith("http")
    assert res.json()["image_url"].endswith(".png")

    detail = await client.get(f"/spice_routes/{rid}", headers=auth(alice_token))
    assert detail.json()["image_url"]


@pytest.mark.asyncio
async def test_upload_rejects_non_image(client: AsyncClient, alice_token: str):
    create = await client.post(
        "/spice_routes", json=make_spice_route_payload(), headers=auth(alice_token)
    )
    rid = create.json()["id"]
    res = await client.post(
        f"/spice_routes/{rid}/image",
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        headers=auth(alice_token),
    )
    assert res.status_code == 415


@pytest.mark.asyncio
async def test_upload_requires_owner(
    client: AsyncClient, alice_token: str, bob_token: str
):
    create = await client.post(
        "/spice_routes", json=make_spice_route_payload(), headers=auth(alice_token)
    )
    rid = create.json()["id"]
    res = await client.post(
        f"/spice_routes/{rid}/image",
        files={"file": ("hero.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=auth(bob_token),
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient, alice_token: str):
    create = await client.post(
        "/spice_routes", json=make_spice_route_payload(), headers=auth(alice_token)
    )
    rid = create.json()["id"]
    res = await client.post(
        f"/spice_routes/{rid}/image",
        files={"file": ("hero.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_upload_uses_mime_derived_extension_not_filename(
    client: AsyncClient, alice_token: str
):
    """Regression: evil.png.exe uploaded with image/png must be saved as .png,
    not .exe, otherwise the file would be served with the wrong content-type
    and the browser would treat it as a download.
    """
    create = await client.post(
        "/spice_routes", json=make_spice_route_payload(), headers=auth(alice_token)
    )
    rid = create.json()["id"]
    res = await client.post(
        f"/spice_routes/{rid}/image",
        files={"file": ("evil.png.exe", io.BytesIO(PNG_BYTES), "image/png")},
        headers=auth(alice_token),
    )
    assert res.status_code == 200, res.text
    url = res.json()["image_url"]
    assert url.endswith(".png"), f"expected .png, got {url}"
    assert ".exe" not in url


@pytest.mark.asyncio
async def test_upload_replaces_existing_image(
    client: AsyncClient, alice_token: str
):
    create = await client.post(
        "/spice_routes", json=make_spice_route_payload(), headers=auth(alice_token)
    )
    rid = create.json()["id"]
    first = await client.post(
        f"/spice_routes/{rid}/image",
        files={"file": ("a.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=auth(alice_token),
    )
    second = await client.post(
        f"/spice_routes/{rid}/image",
        files={"file": ("b.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=auth(alice_token),
    )
    assert first.json()["image_url"] != second.json()["image_url"]
    # New URL should be the canonical one in the spice_route detail
    detail = await client.get(f"/spice_routes/{rid}", headers=auth(alice_token))
    assert detail.json()["image_url"] == second.json()["image_url"]


@pytest.mark.asyncio
async def test_upload_rejects_empty(client: AsyncClient, alice_token: str):
    create = await client.post(
        "/spice_routes", json=make_spice_route_payload(), headers=auth(alice_token)
    )
    rid = create.json()["id"]
    res = await client.post(
        f"/spice_routes/{rid}/image",
        files={"file": ("blank.png", io.BytesIO(b""), "image/png")},
        headers=auth(alice_token),
    )
    assert res.status_code == 400
