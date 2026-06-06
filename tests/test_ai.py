"""Tests for the AI Creator and AI Companion endpoints (stub mode)."""
import json

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_recipe_generate_stub(client: AsyncClient) -> None:
    r = await client.post(
        "/ai/recipe/generate",
        json={
            "idea": "Something cozy with mushrooms",
            "cuisine": "italian",
            "language": "en",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "recipe" in body
    recipe = body["recipe"]
    assert recipe["cuisine"] == "italian"
    assert recipe["language"] == "en"
    assert len(recipe["ingredients"]) >= 1
    assert len(recipe["steps"]) >= 1
    assert body["saved"] is None


@pytest.mark.asyncio
async def test_recipe_generate_save_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        "/ai/recipe/generate",
        json={
            "idea": "Quick weeknight stir-fry",
            "cuisine": "korean",
            "save": True,
        },
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_recipe_generate_save_authed(client: AsyncClient) -> None:
    headers = auth_header(uid="alice", name="Alice")
    r = await client.post(
        "/ai/recipe/generate",
        json={
            "idea": "Quick weeknight stir-fry",
            "cuisine": "korean",
            "language": "en",
            "save": True,
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["saved"] is not None
    saved = body["saved"]
    assert saved["cuisine"] == "korean"
    assert saved["is_premium"] is False
    assert saved["owner"]["display_name"] == "Alice"

    listing = await client.get("/spice_routes", params={"cuisine": "korean"})
    titles = [i["title"] for i in listing.json()["items"]]
    assert saved["title"] in titles


@pytest.mark.asyncio
async def test_recipe_generate_validates_language(
    client: AsyncClient,
) -> None:
    r = await client.post(
        "/ai/recipe/generate",
        json={"idea": "anything", "language": "xx"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_stub(client: AsyncClient) -> None:
    async with client.stream(
        "POST",
        "/ai/chat/stream",
        json={
            "messages": [
                {"role": "user", "content": "Suggest a dinner with leftover rice"}
            ],
            "language": "en",
        },
    ) as r:
        assert r.status_code == 200
        events: list[dict] = []
        async for line in r.aiter_lines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            events.append(json.loads(line[len("data:") :].strip()))

    assert events, "expected SSE events"
    assert events[-1]["type"] == "done"
    deltas = [e for e in events if e["type"] == "delta"]
    assert deltas, "expected at least one delta event"
    joined = "".join(e["text"] for e in deltas)
    assert "stub" in joined.lower()


@pytest.mark.asyncio
async def test_chat_stream_requires_user_last(client: AsyncClient) -> None:
    r = await client.post(
        "/ai/chat/stream",
        json={
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "model", "content": "hello"},
            ],
            "language": "en",
        },
    )
    assert r.status_code == 422
