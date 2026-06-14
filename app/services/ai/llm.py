"""OpenAI-compatible Chat Completions client.

This module replaces the earlier Ollama-native client. The wire format is
the OpenAI `/v1/chat/completions` API, which is the de-facto standard
spoken by:

    - Groq           (free tier, our default — fast Llama 3.1)
    - OpenAI         (paid)
    - OpenRouter     (mix of free + paid models behind one endpoint)
    - Cerebras       (free tier, Llama 3.1)
    - Together AI    (mix)
    - Ollama         (via its `/v1/chat/completions` compatibility shim)

So the same three env vars (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`)
let an operator pick any provider without touching code.

Two operations:
    generate_recipe()   structured-JSON one-shot call (AI Creator)
    chat_stream()       streamed chat completion  (AI Companion)

Two ways to land in STUB MODE — deterministic mock content for development:

    1. `AI_FORCE_STUB=1`, or `LLM_BASE_URL` blank, or `LLM_API_KEY` blank.
       Any of those flips the entire process to stub mode at config time.
       Used by CI, offline dev, and half-configured deploys.

    2. **Per-request reachability fallback**: if both env vars are set
       but the host is unreachable (connection refused, DNS fails,
       timeout on the initial connect), we silently serve stub content
       for that one request and log a warning. This is what keeps the
       production surface from 502'ing the whole AI feature when the
       upstream provider has a hiccup.

Why per-request and not "memoize unreachable for N seconds"? The
provider coming back up should be visible immediately — stale negative
caching is exactly the kind of thing that makes "it works on my box"
bug reports.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.ai.prompts import (
    LANGUAGE_NAMES,
    RECIPE_RESPONSE_SCHEMA,
    chat_system_prompt,
    recipe_system_prompt,
    recipe_user_prompt,
)

log = logging.getLogger(__name__)


class AIError(RuntimeError):
    """Surface for upstream failures the API layer can catch and retry once."""


_settings = get_settings()


# Network errors that mean "provider isn't reachable right now" → fall
# back to stub. Anything else (4xx/5xx with a body, malformed JSON,
# etc.) is a real error and propagates as `AIError`.
_REACHABILITY_ERRORS: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


def _stub_mode_active() -> bool:
    return _settings.ai_stub_mode


def _auth_headers() -> dict[str, str]:
    """Bearer-token header. The API key is required even for local
    Ollama (Ollama ignores the value but the OpenAI-compat layer still
    demands the header)."""
    return {
        "Authorization": f"Bearer {_settings.llm_api_key}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Recipe generation — POST /chat/completions with response_format=json_object
# ---------------------------------------------------------------------------


async def generate_recipe(
    *,
    idea: str,
    cuisine: str | None,
    language: str,
) -> dict[str, Any]:
    if _stub_mode_active():
        return _stub_recipe(idea=idea, cuisine=cuisine, language=language)

    system = recipe_system_prompt(language, cuisine)
    user = recipe_user_prompt(idea=idea, schema=RECIPE_RESPONSE_SCHEMA)
    payload = {
        "model": _settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        # `{"type": "json_object"}` is the OpenAI-standard way to ask
        # for guaranteed-valid JSON. It does NOT enforce a specific
        # schema (unlike the older Gemini `response_schema`); the
        # Pydantic validation in the caller is the real shape gate.
        # Groq, OpenAI, Cerebras, and Ollama (>= 0.1.32) all support
        # this. OpenRouter passes it through to the underlying model.
        "response_format": {"type": "json_object"},
        "temperature": 0.85,
        # Bound the response so a runaway model doesn't fill the body
        # with megabytes of JSON. The schema caps at ~50 ingredients +
        # 50 steps, well under 4 K tokens.
        "max_tokens": 4096,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(
            base_url=_settings.llm_base_url,
            timeout=_settings.llm_request_timeout_s,
            headers=_auth_headers(),
        ) as http:
            resp = await http.post("/chat/completions", json=payload)
    except _REACHABILITY_ERRORS as exc:
        log.warning(
            "LLM provider unreachable (%s) — falling back to stub recipe", exc
        )
        return _stub_recipe(idea=idea, cuisine=cuisine, language=language)

    if resp.status_code >= 400:
        # Providers return 401 (bad/missing key), 404 (unknown model),
        # 429 (rate-limited), 5xx (provider issues). We surface a
        # generic AIError so the API layer can retry once. Body is
        # logged for ops but not echoed to the client.
        log.warning(
            "LLM %s on /chat/completions: %s",
            resp.status_code,
            resp.text[:500],
        )
        raise AIError(f"LLM returned HTTP {resp.status_code}")

    try:
        envelope = resp.json()
    except json.JSONDecodeError as exc:
        raise AIError(f"LLM envelope not JSON: {exc}") from exc

    text = _extract_message_content(envelope)
    if not text:
        raise AIError("empty response from LLM")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        # `response_format=json_object` should make this near-impossible
        # on Groq / OpenAI, but smaller open-source models occasionally
        # produce a `{...}{...}` concatenation or an unterminated
        # string. The API layer already retries once on AIError, so we
        # just surface and let it have another go.
        raise AIError(f"LLM returned non-JSON: {exc}") from exc


def _extract_message_content(envelope: dict[str, Any]) -> str:
    """Pull `choices[0].message.content` from an OpenAI-compat response.

    Defensive against the (rare) provider that returns malformed
    envelopes — we'd rather raise AIError and trigger the API's
    one-shot retry than drop into a `KeyError` 500."""
    choices = envelope.get("choices") or []
    if not choices:
        return ""
    msg = (choices[0] or {}).get("message") or {}
    content = msg.get("content")
    return content if isinstance(content, str) else ""


# ---------------------------------------------------------------------------
# Chat streaming — POST /chat/completions with stream=true (SSE)
# ---------------------------------------------------------------------------


async def chat_stream(
    *,
    history: list[dict[str, str]],
    language: str,
) -> AsyncIterator[str]:
    """Yields partial-text deltas for the AI Companion.

    `history` is a list of `{"role": "user"|"model", "content": str}`
    messages, ending with the user's latest turn. We translate Gemini's
    `model` role to OpenAI's `assistant` role on the wire (kept the
    Gemini terminology in our internal contract because the Flutter
    schema and DB rows already use `model`).
    """
    if _stub_mode_active():
        async for chunk in _stub_chat_stream(history=history, language=language):
            yield chunk
        return

    messages: list[dict[str, str]] = [
        {"role": "system", "content": chat_system_prompt(language)}
    ]
    for msg in history:
        role = "user" if msg.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": msg.get("content", "")})

    payload = {
        "model": _settings.llm_model,
        "messages": messages,
        "temperature": 0.7,
        "stream": True,
    }

    # `httpx.AsyncClient.stream()` defers the actual HTTP request until
    # we enter the `async with`, so all reachability errors flow through
    # the inner block. We track `yielded_any` to distinguish a
    # pre-stream failure (safe to swap to stub) from a mid-stream one
    # (must surface — swapping mid-flight would corrupt the partial
    # message the client has already rendered).
    client = httpx.AsyncClient(
        base_url=_settings.llm_base_url,
        timeout=_settings.llm_request_timeout_s,
        headers=_auth_headers(),
    )

    yielded_any = False
    try:
        try:
            async with client.stream(
                "POST", "/chat/completions", json=payload
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    log.warning(
                        "LLM %s on /chat/completions: %s",
                        resp.status_code,
                        body[:500].decode("utf-8", errors="replace"),
                    )
                    raise AIError(
                        f"LLM returned HTTP {resp.status_code}"
                    )

                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    # OpenAI SSE format: each non-empty line starts
                    # with `data: ` and the body is either a JSON
                    # frame or the literal string `[DONE]` to mark
                    # end of stream. Anything else (keepalive
                    # comments starting with `:`, etc.) is ignored.
                    if not line.startswith("data:"):
                        continue
                    payload_str = line[5:].strip()
                    if not payload_str:
                        continue
                    if payload_str == "[DONE]":
                        break
                    try:
                        frame = json.loads(payload_str)
                    except json.JSONDecodeError:
                        log.debug("LLM: skipping non-JSON SSE frame %r", line)
                        continue

                    text = _extract_delta_content(frame)
                    if text:
                        yielded_any = True
                        yield text
        except _REACHABILITY_ERRORS as exc:
            if not yielded_any:
                log.warning(
                    "LLM unreachable (%s) — falling back to stub chat", exc
                )
                async for chunk in _stub_chat_stream(
                    history=history, language=language
                ):
                    yield chunk
                return
            log.warning("LLM mid-stream failure: %s", exc)
            raise AIError(f"LLM stream disconnected: {exc}") from exc
    finally:
        await client.aclose()


def _extract_delta_content(frame: dict[str, Any]) -> str:
    """Pull `choices[0].delta.content` from a single SSE frame.

    Each streamed frame's shape is:
        {"choices": [{"delta": {"content": "..."}, "index": 0,
                      "finish_reason": null}], ...}
    The final frame before `[DONE]` typically has an empty `delta` and
    a non-null `finish_reason` — our content extraction returns "" for
    that one and we just skip it."""
    choices = frame.get("choices") or []
    if not choices:
        return ""
    delta = (choices[0] or {}).get("delta") or {}
    content = delta.get("content")
    return content if isinstance(content, str) else ""


# ---------------------------------------------------------------------------
# Stub mode — deterministic mock content for development
# ---------------------------------------------------------------------------


_STUB_TITLE_BY_CUISINE = {
    "korean": "Sample Kimchi Fried Rice",
    "japanese": "Sample Tamago Donburi",
    "chinese": "Sample Mapo Tofu",
    "burmese": "Sample Mohinga Bowl",
    "thai": "Sample Pad Krapow",
    "vietnamese": "Sample Pho Bo",
    "indian": "Sample Dal Tadka",
    "italian": "Sample Aglio e Olio",
    "american_western": "Sample Sheet-Pan Chicken",
    "mexican": "Sample Chicken Tinga Tacos",
    "french": "Sample Coq au Vin",
}


def _stub_recipe(
    *, idea: str, cuisine: str | None, language: str
) -> dict[str, Any]:
    chosen = (cuisine or "italian").lower()
    title = _STUB_TITLE_BY_CUISINE.get(chosen, "Sample Recipe")
    return {
        "title": f"{title} (stub)",
        "description": (
            f"Mock recipe inspired by '{idea}'. Configure LLM_BASE_URL "
            "and LLM_API_KEY in your environment to enable real AI "
            "generation (Groq's free tier works out of the box — see "
            ".env.example)."
        ),
        "prep_minutes": 10,
        "cook_minutes": 20,
        "servings": 2,
        "cuisine": chosen if chosen in _STUB_TITLE_BY_CUISINE else "italian",
        "language": language if language in LANGUAGE_NAMES else "en",
        "spice_level": 1,
        "ingredients": [
            {"quantity": 200, "unit": "g", "name": "Main protein or starch"},
            {"quantity": 2, "unit": "tbsp", "name": "Cooking oil"},
            {"quantity": 1, "unit": "tsp", "name": "Salt"},
            {"name": "Aromatics to taste"},
        ],
        "steps": [
            {"body": "Mise en place: chop, measure, and arrange everything."},
            {"body": "Heat the oil in a wide pan over medium-high heat."},
            {"body": "Cook the main ingredient until just done, then season."},
            {"body": "Plate immediately and finish with garnish."},
        ],
        "tags": ["stub", "demo"],
        "calories_per_serving": 480,
    }


async def _stub_chat_stream(
    *, history: list[dict[str, str]], language: str
) -> AsyncIterator[str]:
    last_user = next(
        (m["content"] for m in reversed(history) if m.get("role") == "user"),
        "",
    )
    reply = (
        "(stub reply — set LLM_BASE_URL + LLM_API_KEY for real responses) "
        f'You asked: "{last_user[:120]}". For best results, taste as you '
        "go, balance acid + fat + salt, and let proteins rest before slicing. "
        f"[language={language}]"
    )
    for word in reply.split(" "):
        await asyncio.sleep(0.04)
        yield word + " "
