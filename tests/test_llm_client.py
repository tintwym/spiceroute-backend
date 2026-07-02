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
import json
from collections.abc import Callable

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


# ---------------------------------------------------------------------------
# translate_title_description
#
# This helper runs at recipe-save time and is intentionally NON-fatal —
# every failure path must return None so a flaky LLM provider can't
# block the user from saving their own content. The tests below pin
# that contract: each failure mode that would normally bubble up an
# AIError on `generate_recipe` instead silently returns None here.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_translate_returns_none_in_stub_mode() -> None:
    """Stub mode → no LLM call, no translations stored.

    Stub mode is what CI and offline-dev run in. Returning anything
    other than None would write deterministic fake strings (e.g.
    "Sample Recipe" in every locale) into production-shaped JSONB
    and is a worse default than just leaving the column null and
    falling back to the source title.
    """
    out = await llm.translate_title_description(
        title="Pho Bo", description="Beef noodle soup", source_language="en"
    )
    assert out is None


# Per-locale dispatch helper: the rewritten translator issues ONE call
# per target locale, not a single combined call. The handler maps the
# target language name (extracted from the system prompt) to the
# bundle the test wants to return for that locale.
_LANG_NAME_TO_CODE = {
    "English": "en",
    "Mandarin Chinese (Simplified)": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Vietnamese": "vi",
}


def _bundle_handler(bundles: dict[str, dict]) -> Callable[..., httpx.Response]:
    """Build an httpx handler that returns `bundles[code]` for each
    per-locale request, where `code` is the two-letter language code
    derived from the target language name in the system prompt.
    Locales absent from `bundles` get an empty bundle so the call
    completes (the per-call result is still validated by the
    extractor)."""

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/v1/chat/completions"
        body = json.loads(req.content)
        assert body["response_format"] == {"type": "json_object"}
        assert body["temperature"] == 0.2
        system = body["messages"][0]["content"]
        target_code: str | None = None
        for name, code in _LANG_NAME_TO_CODE.items():
            if f"to {name}" in system:
                target_code = code
                break
        assert target_code is not None, system
        bundle = bundles.get(target_code, {})
        return httpx.Response(
            200, json=_chat_completion_envelope(json.dumps(bundle))
        )

    return handler


@pytest.mark.asyncio
async def test_translate_happy_path(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """Well-formed per-locale responses → dict keyed by target locale.

    Verifies:
      - the wire request hits /chat/completions with json_object mode
      - one request fires PER target locale (we no longer ask for all
        four in one combined call — see `_translate_single_locale`
        for the rationale)
      - the source language (en) is NOT in the returned dict (its
        title/description already live in the source columns)
      - every other supported locale IS present
    """
    bundles = {
        "zh": {"title": "越南牛肉河粉", "description": "经典北越牛肉河粉。"},
        "ja": {"title": "フォー・ボー", "description": "ベトナム北部風の牛肉米麺。"},
        "ko": {"title": "퍼 보", "description": "북부식 베트남 쇠고기 쌀국수."},
        "vi": {"title": "Phở Bò", "description": "Phở bò kiểu miền Bắc."},
    }
    _patch_transport(monkeypatch, _bundle_handler(bundles))

    out = await llm.translate_title_description(
        title="Pho Bo",
        description="Beef noodle soup",
        source_language="en",
    )
    assert out is not None
    assert set(out.keys()) == {"zh", "ja", "ko", "vi"}
    assert out["vi"]["title"] == "Phở Bò"
    assert out["ja"]["description"] == "ベトナム北部風の牛肉米麺。"


@pytest.mark.asyncio
async def test_translate_excludes_source_language(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """`source_language='vi'` → vi is NOT in the per-locale call set,
    so the result dict can never carry a `vi` entry even if a buggy
    handler tries to return one.

    The resolver treats the source columns as the canonical vi value;
    a parallel `translations.vi` would compete with that and could
    cause the user's own title to be silently replaced by an LLM
    re-rendering on the next page view."""
    bundles = {
        "en": {"title": "Pho Bo", "description": "Beef noodle soup."},
        "zh": {"title": "越南牛肉河粉", "description": "经典北越牛肉河粉。"},
        "ja": {"title": "フォー・ボー", "description": "牛肉米麺。"},
        "ko": {"title": "퍼 보", "description": "쌀국수."},
    }
    fired: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        system = body["messages"][0]["content"]
        for name, code in _LANG_NAME_TO_CODE.items():
            if f"to {name}" in system:
                fired.append(code)
                return httpx.Response(
                    200,
                    json=_chat_completion_envelope(
                        json.dumps(bundles.get(code, {}))
                    ),
                )
        raise AssertionError(f"no target found in system prompt: {system!r}")

    _patch_transport(monkeypatch, handler)

    out = await llm.translate_title_description(
        title="Phở Bò",
        description="Phở bò kiểu miền Bắc.",
        source_language="vi",
    )
    assert out is not None
    # No vi request was fired (source-language guard).
    assert "vi" not in fired
    assert set(fired) == {"en", "zh", "ja", "ko"}
    # And the merged result mirrors that — no vi entry.
    assert "vi" not in out
    assert set(out.keys()) == {"en", "zh", "ja", "ko"}


@pytest.mark.asyncio
async def test_translate_partial_response_keeps_good_entries(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """Per-locale calls return different shapes → keep the good ones,
    don't return None on any single bad bundle.

    Half a translation is strictly better than zero: a user who reads
    Vietnamese still gets the Vietnamese row even if the Korean
    translation came back malformed."""
    # Different bundles for different locales: zh good, ja garbage,
    # ko empty-title (description only), vi good. Each per-locale
    # call returns its own bundle.
    bundles: dict[str, object] = {
        "zh": {"title": "越南牛肉河粉", "description": "经典北越牛肉河粉。"},
        # ja entry returns garbage — not a JSON object
        "ja": "not json at all",
        # ko has whitespace-only title — that field is dropped,
        # description is kept
        "ko": {"title": "  ", "description": "북부식 베트남 쇠고기 쌀국수."},
        "vi": {"title": "Phở Bò", "description": "Phở bò kiểu miền Bắc."},
    }

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        system = body["messages"][0]["content"]
        for name, code in _LANG_NAME_TO_CODE.items():
            if f"to {name}" in system:
                payload = bundles.get(code)
                if isinstance(payload, str):
                    # Return non-JSON content — extractor should return
                    # None for this locale.
                    return httpx.Response(
                        200, json=_chat_completion_envelope(payload)
                    )
                return httpx.Response(
                    200,
                    json=_chat_completion_envelope(json.dumps(payload or {})),
                )
        raise AssertionError(f"no target in system prompt: {system!r}")

    _patch_transport(monkeypatch, handler)

    out = await llm.translate_title_description(
        title="Pho Bo", description="Beef soup", source_language="en"
    )
    assert out is not None
    assert "zh" in out and out["zh"]["title"] == "越南牛肉河粉"
    # ja was unparseable JSON — dropped
    assert "ja" not in out
    # ko only kept description (title was whitespace-only)
    assert out["ko"] == {"description": "북부식 베트남 쇠고기 쌀국수."}
    assert out["vi"]["title"] == "Phở Bò"


@pytest.mark.asyncio
async def test_translate_unreachable_returns_none(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """ConnectError → None (NOT AIError).

    Unlike `generate_recipe` (where unreachable falls back to a stub
    recipe) or `chat_stream` (stub stream), translation has no
    user-facing "stub" fallback shape — the right behavior is to
    return None so the recipe gets saved with `translations=NULL`
    and the resolver falls back to the source language.
    """

    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    _patch_transport(monkeypatch, handler)

    out = await llm.translate_title_description(
        title="Anything", description="At all", source_language="en"
    )
    assert out is None


@pytest.mark.asyncio
async def test_translate_http_error_returns_none(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """5xx from provider → None, NOT a raised AIError.

    A provider blip must not prevent the user from saving their
    recipe — we'd rather store the row without translations than
    fail the save."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream down")

    _patch_transport(monkeypatch, handler)

    out = await llm.translate_title_description(
        title="x", description="y", source_language="en"
    )
    assert out is None


@pytest.mark.asyncio
async def test_translate_unauthorized_returns_none(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """401 → None. Even if the API key is wrong, the user save still
    succeeds (without translations). The bad key is logged for the
    operator to fix."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid api key")

    _patch_transport(monkeypatch, handler)

    out = await llm.translate_title_description(
        title="x", description="y", source_language="en"
    )
    assert out is None


@pytest.mark.asyncio
async def test_translate_non_json_returns_none(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """`message.content` isn't valid JSON → None.

    `json_object` mode normally prevents this on Groq / OpenAI, but
    small local models occasionally produce garbage. The recipe save
    must still succeed."""

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=_chat_completion_envelope("not json at all")
        )

    _patch_transport(monkeypatch, handler)

    out = await llm.translate_title_description(
        title="x", description="y", source_language="en"
    )
    assert out is None


@pytest.mark.asyncio
async def test_translate_empty_object_collapses_to_none(
    monkeypatch: pytest.MonkeyPatch, disable_stub_mode
) -> None:
    """Model returns `{}` with no usable entries → None, NOT `{}`.

    `{}` in the JSONB column would be a footgun: the resolver's
    `isinstance(translations, dict)` guard would pass, and any code
    that does `if row.translations:` would treat the row as "has
    translations" when it doesn't. NULL is the unambiguous signal
    for "nothing to look up here, use the source columns."
    """

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_completion_envelope("{}"))

    _patch_transport(monkeypatch, handler)

    out = await llm.translate_title_description(
        title="x", description="y", source_language="en"
    )
    assert out is None


@pytest.mark.asyncio
async def test_translate_unknown_source_language_returns_none() -> None:
    """Unrecognised source language → None.

    Translating into ALL supported locales (including what the row
    actually IS) would store an LLM re-rendering of the user's title
    over their own words. Skipping entirely is safer."""
    out = await llm.translate_title_description(
        title="x", description="y", source_language="xx-XX"
    )
    assert out is None
