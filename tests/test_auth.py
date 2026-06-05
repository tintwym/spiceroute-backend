import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    res = await client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "supersecret",
            "display_name": "Alice",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "access_token" in body and "refresh_token" in body

    res = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "supersecret"},
    )
    assert res.status_code == 200, res.text
    tokens = res.json()
    assert tokens["access_token"] and tokens["refresh_token"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dup@example.com",
        "password": "supersecret",
        "display_name": "Dup",
    }
    res = await client.post("/auth/register", json=payload)
    assert res.status_code == 201
    res = await client.post("/auth/register", json=payload)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={
            "email": "bob@example.com",
            "password": "supersecret",
            "display_name": "Bob",
        },
    )
    res = await client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "wrong"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint_requires_token(client: AsyncClient):
    res = await client.get("/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint_returns_user(client: AsyncClient):
    reg = await client.post(
        "/auth/register",
        json={
            "email": "carol@example.com",
            "password": "supersecret",
            "display_name": "Carol",
        },
    )
    access = reg.json()["access_token"]
    res = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert res.status_code == 200, res.text
    assert res.json()["email"] == "carol@example.com"
    assert res.json()["display_name"] == "Carol"


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient):
    reg = await client.post(
        "/auth/register",
        json={
            "email": "dan@example.com",
            "password": "supersecret",
            "display_name": "Dan",
        },
    )
    refresh = reg.json()["refresh_token"]
    res = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert res.status_code == 200, res.text
    assert res.json()["access_token"]


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client: AsyncClient):
    reg = await client.post(
        "/auth/register",
        json={
            "email": "eve@example.com",
            "password": "supersecret",
            "display_name": "Eve",
        },
    )
    access = reg.json()["access_token"]
    res = await client.post("/auth/refresh", json={"refresh_token": access})
    assert res.status_code == 401
