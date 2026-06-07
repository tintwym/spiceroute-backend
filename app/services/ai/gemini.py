"""Thin Gemini client wrapper.

Exposes two operations:
    generate_recipe()   structured-JSON one-shot call (AI Creator)
    chat_stream()       streamed chat completion (AI Companion)

When `settings.gemini_api_key` is empty we run in STUB MODE: the same call
shape is honored but responses are deterministic mock content. This lets the
whole UI be developed without a paid API key.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.services.ai.prompts import (
    LANGUAGE_NAMES,
    RECIPE_RESPONSE_SCHEMA,
    chat_system_prompt,
    recipe_system_prompt,
)

log = logging.getLogger(__name__)


class AIError(RuntimeError):
    pass


_settings = get_settings()
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if _settings.gemini_stub_mode:
            raise AIError("Gemini client requested in stub mode")
        _client = genai.Client(api_key=_settings.gemini_api_key)
    return _client


# ---------------------------------------------------------------------------
# Recipe generation
# ---------------------------------------------------------------------------


async def generate_recipe(
    *,
    idea: str,
    cuisine: str | None,
    language: str,
) -> dict[str, Any]:
    if _settings.gemini_stub_mode:
        return _stub_recipe(idea=idea, cuisine=cuisine, language=language)

    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=recipe_system_prompt(language, cuisine),
        response_mime_type="application/json",
        response_schema=RECIPE_RESPONSE_SCHEMA,
        temperature=0.85,
    )

    def _call() -> str:
        response = client.models.generate_content(
            model=_settings.gemini_model,
            contents=idea,
            config=config,
        )
        return response.text or ""

    text = await asyncio.to_thread(_call)
    if not text:
        raise AIError("empty response from gemini")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIError(f"gemini returned non-JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# Chat streaming
# ---------------------------------------------------------------------------


async def chat_stream(
    *,
    history: list[dict[str, str]],
    language: str,
) -> AsyncIterator[str]:
    """Yields partial-text deltas for the AI Companion.

    `history` is a list of `{"role": "user"|"model", "content": str}`
    messages, ending with the user's latest turn.
    """
    if _settings.gemini_stub_mode:
        async for chunk in _stub_chat_stream(history=history, language=language):
            yield chunk
        return

    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=chat_system_prompt(language),
        temperature=0.7,
    )

    contents: list[types.Content] = []
    for msg in history:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg.get("content", ""))],
            )
        )

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _produce() -> None:
        try:
            stream = client.models.generate_content_stream(
                model=_settings.gemini_model,
                contents=contents,
                config=config,
            )
            for chunk in stream:
                text = chunk.text or ""
                if text:
                    asyncio.run_coroutine_threadsafe(queue.put(text), loop)
        except Exception as exc:
            log.exception("gemini stream error")
            asyncio.run_coroutine_threadsafe(
                queue.put(f"\n[error: {exc}]"), loop
            )
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    task = asyncio.get_running_loop().run_in_executor(None, _produce)
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        await task


# ---------------------------------------------------------------------------
# Stub mode (no API key) — deterministic mock content for development
# ---------------------------------------------------------------------------


_STUB_TITLE_BY_CUISINE = {
    "korean": "Sample Kimchi Fried Rice",
    "japanese": "Sample Tamago Donburi",
    "chinese": "Sample Mapo Tofu",
    "burmese": "Sample Mohinga Bowl",
    "thai": "Sample Pad Krapow",
    "indian": "Sample Dal Tadka",
    "italian": "Sample Aglio e Olio",
    "american_western": "Sample Sheet-Pan Chicken",
    "mexican": "Sample Chicken Tinga Tacos",
}


def _stub_recipe(
    *, idea: str, cuisine: str | None, language: str
) -> dict[str, Any]:
    chosen = (cuisine or "italian").lower()
    title = _STUB_TITLE_BY_CUISINE.get(chosen, "Sample Recipe")
    return {
        "title": f"{title} (stub)",
        "description": (
            f"Mock recipe inspired by '{idea}'. Set GEMINI_API_KEY in your .env "
            "to enable real AI generation."
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
        f"(stub reply, set GEMINI_API_KEY for real responses) "
        f"You asked: \"{last_user[:120]}\". For best results, taste as you "
        "go, balance acid + fat + salt, and let proteins rest before slicing. "
        f"[language={language}]"
    )
    for word in reply.split(" "):
        await asyncio.sleep(0.04)
        yield word + " "
