"""Unit tests for the Ollama client wrapper.

These exercise the wrapper directly (not through the API) so we can
inject failures without standing up a full FastAPI client. Httpx's
`MockTransport` lets us pretend to be Ollama and return the exact
envelope shapes the real `/api/generate` and `/api/chat` produce.

The fixtures in `conftest.py` pin the process to stub mode by setting
`AI_FORCE_STUB=1`. For these tests we deliberately bypass that gate by
patching `_settings.ai_force_stub` and pointing `ollama_base_url` at a
mock-transport-backed AsyncClient.
"""
from __future__ import annotations

import json

import httpx
import pytest

from app.services.ai import ollama

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def disable_stub_mode(monkeypatch: pytest.MonkeyPatch):
    """Take the test out of stub mode so the real HTTP path runs."""
    monkeypatch.setattr(ollama._settings, "ai_force_stub", False)
    monkeypatch.setattr(ollama._settings, "ollama_base_url", "http://fake")
    monkeypatch.setattr(ollama._settings, "ollama_model", "test-model")


def _patch_transport(
    monkeypatch: pytest.MonkeyPatch, handler
) -> None:
    """Wire `httpx.AsyncClient` to use `MockTransport(handler)` for this test.

    The client wrapper builds its own `AsyncClient` internally; the
    cleanest way to inject a transport is to monkey-patch the
    `httpx.AsyncClient` constructor used by `ollama.py`.
    """
    real_cls = httpx.AsyncClient

    def fake_factory(*args, **kwargs):
        kwargs.setdefault("transport", httpx.MockTransport(handler))
        return real_cls(*args, **kwargs)

    monkeypatch.setattr(ollama.httpx, "AsyncClient", fake_factory)


# ---------------------------------------------------------------------------
# generate_recipe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_recipe_happy_path(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """Well-formed Ollama envelope → parsed recipe dict."""
    recipe = {
        "title": "Test Pho",
        "description": "A bowl",
        "prep_minutes": 10,
        "cook_minutes": 30,
        "servings": 2,
        "cuisine": "vietnamese",
        "language": "en",
        "spice_level": 1,
        "ingredients": [{"quantity": 1, "unit": "kg", "name": "beef"}],
        "steps": [{"body": "Simmer."}],
        "tags": ["soup"],
    }

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/generate"
        body = json.loads(req.content)
        assert body["model"] == "test-model"
        assert body["format"] == "json"
        assert body["stream"] is False
        return httpx.Response(
            200,
            json={"response": json.dumps(recipe), "done": True},
        )

    _patch_transport(monkeypatch, handler)

    out = await ollama.generate_recipe(
        idea="vietnamese soup", cuisine="vietnamese", language="en"
    )
    assert out["title"] == "Test Pho"
    assert out["cuisine"] == "vietnamese"


@pytest.mark.asyncio
async def test_generate_recipe_unreachable_falls_back_to_stub(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """ConnectError → silent stub fallback (NOT an AIError).

    This is the production-friendly behavior: if the Ollama host is
    down, we'd rather serve a stub recipe than 502 the request. The
    API caller sees a 200 with a `(stub)` title.
    """

    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    _patch_transport(monkeypatch, handler)

    out = await ollama.generate_recipe(
        idea="anything", cuisine="italian", language="en"
    )
    assert "(stub)" in out["title"]
    assert out["cuisine"] == "italian"


@pytest.mark.asyncio
async def test_generate_recipe_http_error_raises_aierror(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """HTTP 500 from Ollama → AIError so the API layer can retry once."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    _patch_transport(monkeypatch, handler)

    with pytest.raises(ollama.AIError):
        await ollama.generate_recipe(
            idea="x", cuisine=None, language="en"
        )


@pytest.mark.asyncio
async def test_generate_recipe_non_json_response_raises_aierror(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """`response` field that isn't valid JSON → AIError (retry-eligible).

    Small models occasionally hallucinate `{...}{...}` concatenations
    or unterminated strings even with `format: "json"`. We don't try
    to repair — the API layer retries once, which is cheap.
    """

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"response": "{not valid json", "done": True}
        )

    _patch_transport(monkeypatch, handler)

    with pytest.raises(ollama.AIError):
        await ollama.generate_recipe(
            idea="x", cuisine=None, language="en"
        )


@pytest.mark.asyncio
async def test_generate_recipe_empty_response_raises_aierror(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """Empty `response` field → AIError (retry-eligible)."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "", "done": True})

    _patch_transport(monkeypatch, handler)

    with pytest.raises(ollama.AIError):
        await ollama.generate_recipe(
            idea="x", cuisine=None, language="en"
        )


# ---------------------------------------------------------------------------
# chat_stream
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_stream_yields_deltas(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """NDJSON frames → text deltas; `done: true` ends the stream."""
    frames = [
        {"message": {"role": "assistant", "content": "Hello"}, "done": False},
        {"message": {"role": "assistant", "content": " there"}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True},
    ]
    body = ("\n".join(json.dumps(f) for f in frames) + "\n").encode()

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/chat"
        sent = json.loads(req.content)
        # System prompt is prepended automatically.
        assert sent["messages"][0]["role"] == "system"
        # `model` role on the wire is normalized to `assistant`.
        assert all(m["role"] != "model" for m in sent["messages"])
        return httpx.Response(200, content=body)

    _patch_transport(monkeypatch, handler)

    out: list[str] = []
    async for chunk in ollama.chat_stream(
        history=[
            {"role": "user", "content": "hi"},
            {"role": "model", "content": "hello"},
            {"role": "user", "content": "again"},
        ],
        language="en",
    ):
        out.append(chunk)

    assert "".join(out) == "Hello there"


@pytest.mark.asyncio
async def test_chat_stream_unreachable_falls_back_to_stub(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """Connection refused → stub stream rather than AIError.

    Mirrors the recipe path: production reachability failures should
    serve content, not error responses.
    """

    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    _patch_transport(monkeypatch, handler)

    out: list[str] = []
    async for chunk in ollama.chat_stream(
        history=[{"role": "user", "content": "hi"}], language="en"
    ):
        out.append(chunk)

    joined = "".join(out)
    assert "stub" in joined.lower()


@pytest.mark.asyncio
async def test_chat_stream_skips_malformed_frames(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """One bad frame doesn't tear down the whole stream."""
    body = (
        json.dumps(
            {"message": {"role": "assistant", "content": "ok"}, "done": False}
        )
        + "\n"
        + "this is not json\n"
        + json.dumps(
            {"message": {"role": "assistant", "content": "!"}, "done": True}
        )
        + "\n"
    ).encode()

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    _patch_transport(monkeypatch, handler)

    out: list[str] = []
    async for chunk in ollama.chat_stream(
        history=[{"role": "user", "content": "hi"}], language="en"
    ):
        out.append(chunk)

    assert "".join(out) == "ok"


@pytest.mark.asyncio
async def test_chat_stream_http_error_raises_aierror(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """4xx/5xx → AIError so the SSE handler emits an error frame."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="model not found")

    _patch_transport(monkeypatch, handler)

    with pytest.raises(ollama.AIError):
        async for _ in ollama.chat_stream(
            history=[{"role": "user", "content": "hi"}], language="en"
        ):
            pass
