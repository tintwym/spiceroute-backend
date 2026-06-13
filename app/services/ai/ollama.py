"""Thin Ollama client wrapper.

Exposes two operations:
    generate_recipe()   structured-JSON one-shot call (AI Creator)
    chat_stream()       streamed chat completion (AI Companion)

Talks to Ollama over plain HTTP (`/api/generate` and `/api/chat`). The model
must already be pulled on the Ollama host (e.g. `ollama pull llama3.1:8b`).

Two ways to land in STUB MODE — deterministic mock content for development:

    1. `AI_FORCE_STUB=1` (or `OLLAMA_BASE_URL=""`) flips the entire process
       to stub mode at config time. Used by CI and for offline dev.

    2. **Per-request reachability fallback**: if `OLLAMA_BASE_URL` is set
       but the host is down (connection refused, DNS fails, timeout on the
       initial connect), we silently serve stub content for that one
       request and log a warning. This is what keeps the production
       surface (Render free tier, where running an 8B model is impractical)
       from 502'ing the whole AI feature when Ollama isn't deployed yet.

Why per-request and not "memoize unreachable for N seconds"? Ollama coming
back up should be visible immediately — stale negative caching is exactly
the kind of thing that makes "it works on my box" bug reports.
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
    """Surface for upstream failures the API layer can catch and retry once.

    Kept name-compatible with the previous Gemini client so `app/api/ai.py`
    didn't need to learn a new exception type.
    """


_settings = get_settings()

# Network errors that mean "Ollama isn't reachable right now" → fall back to
# stub. Anything else (4xx/5xx with a body, malformed JSON, etc.) is a real
# error and propagates as `AIError`.
_REACHABILITY_ERRORS: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


def _stub_mode_active() -> bool:
    return _settings.ai_stub_mode


# ---------------------------------------------------------------------------
# Recipe generation — POST /api/generate
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
        "model": _settings.ollama_model,
        "prompt": user,
        "system": system,
        # `format: "json"` constrains the decoder to valid JSON. It does NOT
        # enforce a specific schema (unlike Gemini's `response_schema`),
        # so the Pydantic validation in the caller is the real shape gate.
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.85,
            # Keep the response bounded so a runaway model doesn't fill
            # the response with megabytes of JSON. The schema caps at ~50
            # ingredients + 50 steps, which fits in well under 4k tokens.
            "num_predict": 4096,
        },
    }

    try:
        async with httpx.AsyncClient(
            base_url=_settings.ollama_base_url,
            timeout=_settings.ollama_request_timeout_s,
        ) as http:
            resp = await http.post("/api/generate", json=payload)
    except _REACHABILITY_ERRORS as exc:
        log.warning(
            "ollama unreachable (%s) — falling back to stub recipe", exc
        )
        return _stub_recipe(idea=idea, cuisine=cuisine, language=language)

    if resp.status_code >= 400:
        # Ollama replies 404 on unknown model, 500 on internal failures.
        # We surface a generic AIError so the API layer can retry once.
        # Body is logged for ops but not echoed to the client.
        log.warning(
            "ollama %s on /api/generate: %s",
            resp.status_code,
            resp.text[:500],
        )
        raise AIError(f"ollama returned HTTP {resp.status_code}")

    try:
        envelope = resp.json()
    except json.JSONDecodeError as exc:
        raise AIError(f"ollama envelope not JSON: {exc}") from exc

    text = envelope.get("response") or ""
    if not text:
        raise AIError("empty response from ollama")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        # `format: "json"` should make this near-impossible, but small
        # models occasionally produce a `{...}{...}` concatenation or an
        # unterminated string. The API layer already retries once on
        # AIError, so we just surface and let it have another go.
        raise AIError(f"ollama returned non-JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# Chat streaming — POST /api/chat with stream=true
# ---------------------------------------------------------------------------


async def chat_stream(
    *,
    history: list[dict[str, str]],
    language: str,
) -> AsyncIterator[str]:
    """Yields partial-text deltas for the AI Companion.

    `history` is a list of `{"role": "user"|"model", "content": str}`
    messages, ending with the user's latest turn. We translate Gemini's
    `model` role to Ollama's `assistant` role on the wire.
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
        "model": _settings.ollama_model,
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.7},
    }

    # `httpx.AsyncClient.stream()` returns an async-context-managed Response.
    # The actual HTTP request (and any connection error it raises) is
    # deferred until we enter the `async with` — `client.stream()` itself
    # is synchronous setup. So all reachability errors flow through the
    # `async with` block, and we distinguish pre-stream vs mid-stream by
    # tracking whether we've yielded anything yet.
    client = httpx.AsyncClient(
        base_url=_settings.ollama_base_url,
        timeout=_settings.ollama_request_timeout_s,
    )

    yielded_any = False
    try:
        try:
            async with client.stream(
                "POST", "/api/chat", json=payload
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    log.warning(
                        "ollama %s on /api/chat: %s",
                        resp.status_code,
                        body[:500].decode("utf-8", errors="replace"),
                    )
                    raise AIError(
                        f"ollama returned HTTP {resp.status_code}"
                    )

                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        frame = json.loads(line)
                    except json.JSONDecodeError:
                        # Skip the rare malformed line rather than
                        # tearing down the whole stream over it.
                        log.debug("ollama: skipping non-JSON frame %r", line)
                        continue

                    # Ollama emits `{"message": {"role": "...",
                    # "content": "..."}, "done": false, ...}` per chunk
                    # and a final frame with `"done": true`.
                    if frame.get("done"):
                        break
                    msg = frame.get("message") or {}
                    text = msg.get("content") or ""
                    if text:
                        yielded_any = True
                        yield text
        except _REACHABILITY_ERRORS as exc:
            # Pre-stream connection failure → fall back to stub, same as
            # the recipe path. We only know this is "pre-stream" if we
            # haven't yielded anything yet; once partial text has reached
            # the client, swapping to a stub mid-flight would corrupt the
            # message, so we surface AIError instead and let the API
            # layer emit an `error` SSE frame.
            if not yielded_any:
                log.warning(
                    "ollama unreachable (%s) — falling back to stub chat",
                    exc,
                )
                async for chunk in _stub_chat_stream(
                    history=history, language=language
                ):
                    yield chunk
                return
            log.warning("ollama mid-stream failure: %s", exc)
            raise AIError(f"ollama stream disconnected: {exc}") from exc
    finally:
        await client.aclose()


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
            f"Mock recipe inspired by '{idea}'. Set OLLAMA_BASE_URL in "
            "your .env (and `ollama serve` locally) to enable real AI "
            "generation."
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
        f"(stub reply, set OLLAMA_BASE_URL for real responses) "
        f"You asked: \"{last_user[:120]}\". For best results, taste as you "
        "go, balance acid + fat + salt, and let proteins rest before slicing. "
        f"[language={language}]"
    )
    for word in reply.split(" "):
        await asyncio.sleep(0.04)
        yield word + " "
