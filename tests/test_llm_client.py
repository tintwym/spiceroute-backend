"""Unit tests for the OpenAI-compatible LLM client wrapper.

These exercise the wrapper directly (not through the API) so we can
inject failures without standing up a full FastAPI client. Httpx's
`MockTransport` lets us pretend to be Groq / OpenAI / Ollama and return
the exact envelope shapes the real `/chat/completions` endpoint
produces.

The fixtures in `conftest.py` pin the process to stub mode by setting
`AI_FORCE_STUB=1`. For these tests we deliberately bypass that gate by
patching `_settings.ai_force_stub`, `llm_base_url`, and `llm_api_key`
to point at a mock-transport-backed AsyncClient.
"""
from __future__ import annotations

import json

import httpx
import pytest

from app.services.ai import llm

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def disable_stub_mode(monkeypatch: pytest.MonkeyPatch):
    """Take the test out of stub mode so the real HTTP path runs."""
    monkeypatch.setattr(llm._settings, "ai_force_stub", False)
    monkeypatch.setattr(llm._settings, "llm_base_url", "http://fake/v1")
    monkeypatch.setattr(llm._settings, "llm_api_key", "test-key")
    monkeypatch.setattr(llm._settings, "llm_model", "test-model")


def _patch_transport(
    monkeypatch: pytest.MonkeyPatch, handler
) -> None:
    """Wire `httpx.AsyncClient` to use `MockTransport(handler)` for this test.

    The client wrapper builds its own `AsyncClient` internally; the
    cleanest way to inject a transport is to monkey-patch the
    `httpx.AsyncClient` constructor used by `llm.py`.
    """
    real_cls = httpx.AsyncClient

    def fake_factory(*args, **kwargs):
        kwargs.setdefault("transport", httpx.MockTransport(handler))
        return real_cls(*args, **kwargs)

    monkeypatch.setattr(llm.httpx, "AsyncClient", fake_factory)


def _chat_completion_envelope(content: str) -> dict:
    """Standard OpenAI / Groq response shape for a non-streaming completion."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def _sse_frame(delta_content: str = "", finish_reason: str | None = None) -> str:
    """One `data: {...}` SSE line for streaming chat completions."""
    delta: dict = {}
    if delta_content:
        delta["content"] = delta_content
    frame = {
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "choices": [
            {"index": 0, "delta": delta, "finish_reason": finish_reason}
        ],
    }
    return f"data: {json.dumps(frame)}\n\n"


# ---------------------------------------------------------------------------
# generate_recipe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_recipe_happy_path(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """Well-formed chat-completion envelope → parsed recipe dict."""
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
        assert req.url.path == "/v1/chat/completions"
        # Bearer auth header must be present and match the configured key.
        assert req.headers.get("authorization") == "Bearer test-key"
        body = json.loads(req.content)
        assert body["model"] == "test-model"
        assert body["response_format"] == {"type": "json_object"}
        assert body["stream"] is False
        # System + user messages get assembled by the client.
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][-1]["role"] == "user"
        return httpx.Response(
            200, json=_chat_completion_envelope(json.dumps(recipe))
        )

    _patch_transport(monkeypatch, handler)

    out = await llm.generate_recipe(
        idea="vietnamese soup", cuisine="vietnamese", language="en"
    )
    assert out["title"] == "Test Pho"
    assert out["cuisine"] == "vietnamese"


@pytest.mark.asyncio
async def test_generate_recipe_unreachable_falls_back_to_stub(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """ConnectError → silent stub fallback (NOT an AIError).

    This is the production-friendly behavior: if the LLM provider is
    unreachable, we'd rather serve a stub recipe than 502 the request.
    The API caller sees a 200 with a `(stub)` title.
    """

    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    _patch_transport(monkeypatch, handler)

    out = await llm.generate_recipe(
        idea="anything", cuisine="italian", language="en"
    )
    assert "(stub)" in out["title"]
    assert out["cuisine"] == "italian"


@pytest.mark.asyncio
async def test_generate_recipe_http_error_raises_aierror(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """HTTP 500 from the provider → AIError so the API layer can retry once."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    _patch_transport(monkeypatch, handler)

    with pytest.raises(llm.AIError):
        await llm.generate_recipe(idea="x", cuisine=None, language="en")


@pytest.mark.asyncio
async def test_generate_recipe_unauthorized_raises_aierror(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """HTTP 401 (bad / missing key) → AIError. We don't silently
    stub-fallback on auth failures because the operator needs to see
    the retry-eligible 502 in their logs and fix their config."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid api key")

    _patch_transport(monkeypatch, handler)

    with pytest.raises(llm.AIError):
        await llm.generate_recipe(idea="x", cuisine=None, language="en")


@pytest.mark.asyncio
async def test_generate_recipe_non_json_content_raises_aierror(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """`message.content` that isn't valid JSON → AIError (retry-eligible).

    `response_format=json_object` should make this near-impossible on
    Groq / OpenAI, but smaller open-source models occasionally produce
    `{...}{...}` concatenations or unterminated strings. We don't try
    to repair — the API layer retries once, which is cheap.
    """

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=_chat_completion_envelope("{not valid json")
        )

    _patch_transport(monkeypatch, handler)

    with pytest.raises(llm.AIError):
        await llm.generate_recipe(idea="x", cuisine=None, language="en")


@pytest.mark.asyncio
async def test_generate_recipe_empty_content_raises_aierror(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """Empty `message.content` → AIError (retry-eligible)."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_completion_envelope(""))

    _patch_transport(monkeypatch, handler)

    with pytest.raises(llm.AIError):
        await llm.generate_recipe(idea="x", cuisine=None, language="en")


@pytest.mark.asyncio
async def test_generate_recipe_missing_choices_raises_aierror(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """Malformed envelope (no `choices` array) → AIError, not KeyError 500."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "weird"})

    _patch_transport(monkeypatch, handler)

    with pytest.raises(llm.AIError):
        await llm.generate_recipe(idea="x", cuisine=None, language="en")


# ---------------------------------------------------------------------------
# chat_stream
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_stream_yields_deltas(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """OpenAI-style SSE frames → text deltas; `data: [DONE]` ends the stream."""
    body = (
        _sse_frame(delta_content="Hello")
        + _sse_frame(delta_content=" there")
        + _sse_frame(finish_reason="stop")  # final frame, empty delta
        + "data: [DONE]\n\n"
    ).encode()

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/v1/chat/completions"
        assert req.headers.get("authorization") == "Bearer test-key"
        sent = json.loads(req.content)
        assert sent["stream"] is True
        # System prompt is prepended automatically.
        assert sent["messages"][0]["role"] == "system"
        # Our internal `model` role is normalized to OpenAI's `assistant`.
        assert all(m["role"] != "model" for m in sent["messages"])
        return httpx.Response(200, content=body)

    _patch_transport(monkeypatch, handler)

    out: list[str] = []
    async for chunk in llm.chat_stream(
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
    async for chunk in llm.chat_stream(
        history=[{"role": "user", "content": "hi"}], language="en"
    ):
        out.append(chunk)

    joined = "".join(out)
    assert "stub" in joined.lower()


@pytest.mark.asyncio
async def test_chat_stream_skips_malformed_frames(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """One bad SSE frame doesn't tear down the whole stream.

    Also verifies that non-`data:` lines (keepalive comments starting
    with `:`, blank lines) are silently ignored.
    """
    body = (
        _sse_frame(delta_content="ok")
        + ": keepalive comment\n\n"  # ignored
        + "data: this is not json\n\n"  # malformed JSON, skipped
        + _sse_frame(delta_content="!")
        + "data: [DONE]\n\n"
    ).encode()

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    _patch_transport(monkeypatch, handler)

    out: list[str] = []
    async for chunk in llm.chat_stream(
        history=[{"role": "user", "content": "hi"}], language="en"
    ):
        out.append(chunk)

    assert "".join(out) == "ok!"


@pytest.mark.asyncio
async def test_chat_stream_http_error_raises_aierror(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """4xx/5xx → AIError so the SSE handler emits an error frame."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="model not found")

    _patch_transport(monkeypatch, handler)

    with pytest.raises(llm.AIError):
        async for _ in llm.chat_stream(
            history=[{"role": "user", "content": "hi"}], language="en"
        ):
            pass


@pytest.mark.asyncio
async def test_chat_stream_done_sentinel_ends_cleanly(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """An OpenAI stream that ends with `data: [DONE]` (no explicit
    `finish_reason` frame) terminates without raising."""
    body = (
        _sse_frame(delta_content="hi")
        + "data: [DONE]\n\n"
    ).encode()

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    _patch_transport(monkeypatch, handler)

    out = []
    async for chunk in llm.chat_stream(
        history=[{"role": "user", "content": "x"}], language="en"
    ):
        out.append(chunk)
    assert "".join(out) == "hi"
