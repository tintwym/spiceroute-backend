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

Three operations:
    generate_recipe()             structured-JSON one-shot call (AI Creator)
    chat_stream()                 streamed chat completion  (AI Companion)
    translate_title_description() best-effort save-time translation of a
                                  recipe's title + description into every
                                  supported locale other than the source,
                                  so listings can render in the user's UI
                                  language without a per-view LLM call

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
import re
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
# Save-time title/description translation
# ---------------------------------------------------------------------------


async def translate_recipe_content(
    *,
    title: str,
    description: str | None,
    source_language: str,
    ingredients: list[str] | None = None,
    steps: list[str] | None = None,
) -> dict[str, dict[str, Any]] | None:
    """Best-effort recipe translation into every supported locale other
    than `source_language`.

    Translates four fields:
      * `title` (string)
      * `description` (string, optional)
      * `ingredients` (ordered list of strings, optional)
      * `steps` (ordered list of strings, optional)

    Returns a dict ready to write into the `SpiceRoute.translations`
    JSONB column, or `None` if translation could not be performed (stub
    mode, LLM unreachable, HTTP error, malformed response, unknown
    source language). **Callers MUST treat `None` as "store nothing and
    continue with the save"** — a flaky LLM provider must never block
    a user from saving their own recipe. Missing translations can
    always be backfilled later by a one-shot script; a failed recipe
    save is irrecoverable from the user's point of view.

    Return shape (the source language is intentionally omitted because
    the row's `title` / `description` columns and the related
    `ingredients` / `steps` rows already cover that locale via the
    resolver's fallback):

        {
          "zh": {
            "title": "...",
            "description": "...",
            "ingredients": ["...", "..."],
            "steps": ["...", "..."]
          },
          "ja": { ... }, ...
        }

    Entries are dropped individually if the model returns a missing or
    empty value for a field, so a partial translation (e.g. the model
    gave us titles but bailed on the steps array) still ships what it
    got right. An empty dict collapses to `None` to keep the JSONB
    column null rather than `{}` (which would confuse the resolver's
    `if not isinstance(...)` guard at read time).

    Step / ingredient lists are returned in the SAME ORDER and SAME
    LENGTH as the input lists. If the model returns a wrong-length
    array we drop that specific list (rather than silently misaligning
    rows) because misaligned steps would render the wrong action
    against each numbered card — worse than no translation at all."""

    if _stub_mode_active():
        return None

    targets = [code for code in LANGUAGE_NAMES if code != source_language]
    if not targets or len(targets) == len(LANGUAGE_NAMES):
        # `len(targets) == len(LANGUAGE_NAMES)` means the source
        # language wasn't recognised — translating into ALL supported
        # locales would store a "translation" for the language the
        # recipe is already written in, which is both wasteful and
        # would break the resolver's fallback (it would prefer the
        # LLM's re-rendering over the user's original title). Safer
        # to skip entirely.
        return None

    ingredients_clean = [
        s for s in (ingredients or []) if s and s.strip()
    ]
    steps_clean = [s for s in (steps or []) if s and s.strip()]

    # Issue ONE call per target locale rather than asking for all four
    # at once. Three reasons:
    #
    # 1. Free-tier Groq caps at 6000 tokens/min. A combined call for
    #    a recipe with 10 ingredients + 7 steps × 4 locales is ~5k
    #    output tokens by itself — single recipes were tripping the
    #    TPM ceiling AND the per-response `max_tokens` budget,
    #    surfacing as `json_validate_failed` errors mid-document.
    # 2. Smaller outputs are also more reliable: small Llama models
    #    are more likely to produce a complete, valid JSON document
    #    for one locale than for four nested ones.
    # 3. Per-locale isolation: a network blip or rate-limit on the
    #    French call doesn't lose the already-completed Vietnamese
    #    one, which matters during the curated backfill where we
    #    want partial progress to persist.
    #
    # Concurrency: SEQUENTIAL not parallel. Free-tier Groq's TPM cap
    # (6000 tokens/min on llama-3.1-8b-instant) is small enough that
    # 4 parallel ~3500-token calls immediately overshoot the budget
    # and 3 of 4 fail with 429. Sequential calls let the in-call
    # `_retry_after_seconds` honour Groq's advisory and recover
    # cleanly — the wall-clock cost is ~3× higher than parallel but
    # the success rate is ~4× better, so net throughput improves.
    async with httpx.AsyncClient(
        base_url=_settings.llm_base_url,
        timeout=_settings.llm_request_timeout_s,
        headers=_auth_headers(),
    ) as http:
        result: dict[str, dict[str, Any]] = {}
        for code in targets:
            try:
                outcome = await _translate_single_locale(
                    http,
                    title=title,
                    description=description,
                    source_language=source_language,
                    target_code=code,
                    ingredients=ingredients_clean,
                    steps=steps_clean,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "translate(%s): %r — skipping locale", code, exc
                )
                continue
            if outcome:
                result[code] = outcome
            # Spread TPM across locales — backfill issues four sequential
            # calls per row; without a gap Groq's 6k/min cap still trips.
            if code != targets[-1]:
                await asyncio.sleep(8.0)
    return result or None


async def translate_recipe_summary_for_locale(
    *,
    title: str,
    description: str | None,
    source_language: str,
    target_code: str,
) -> dict[str, Any] | None:
    """Translate only title + description into one locale (~one LLM call).

    Used by the Explore listing path to progressively backfill card copy
    without paying for ingredient/step arrays on every page view."""
    if _stub_mode_active():
        return None

    target = target_code.strip().lower()
    src = source_language.strip().lower()
    if not target or target == src or target not in LANGUAGE_NAMES:
        return None

    async with httpx.AsyncClient(
        base_url=_settings.llm_base_url,
        timeout=_settings.llm_request_timeout_s,
        headers=_auth_headers(),
    ) as http:
        try:
            return await _translate_single_locale(
                http,
                title=title,
                description=description,
                source_language=src,
                target_code=target,
                ingredients=[],
                steps=[],
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "translate_summary(%s): %r — skipping locale", target, exc
            )
            return None


async def _post_translate_json(
    http: httpx.AsyncClient,
    payload: dict[str, Any],
    *,
    target_code: str,
) -> dict[str, Any] | None:
    """POST a chat completion and return parsed JSON dict, with 429/400 retries."""
    try:
        resp = await http.post("/chat/completions", json=payload)
    except _REACHABILITY_ERRORS as exc:
        log.warning(
            "LLM unreachable during translate(%s) (%s) — skipping",
            target_code,
            exc,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "translate(%s): unexpected error %r — skipping",
            target_code,
            exc,
        )
        return None

    for attempt in range(2):
        if resp.status_code == 429:
            retry_after_s = _retry_after_seconds(resp)
            if retry_after_s is not None and retry_after_s <= 90:
                log.info(
                    "LLM 429 on translate(%s) — sleeping %.1fs then retrying",
                    target_code,
                    retry_after_s,
                )
                await asyncio.sleep(retry_after_s + 1.0)
                try:
                    resp = await http.post("/chat/completions", json=payload)
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "translate(%s) retry failed: %r — skipping",
                        target_code,
                        exc,
                    )
                    return None
                continue
            log.warning(
                "LLM 429 on translate(%s) (retry-after %s, skipping)",
                target_code,
                retry_after_s,
            )
            return None

        if resp.status_code == 400 and "json_validate_failed" in resp.text:
            if attempt == 0:
                log.info(
                    "LLM 400 json_validate_failed on translate(%s) — retrying",
                    target_code,
                )
                await asyncio.sleep(8.0)
                try:
                    resp = await http.post("/chat/completions", json=payload)
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "translate(%s) json retry failed: %r — skipping",
                        target_code,
                        exc,
                    )
                    return None
                continue
            log.warning(
                "LLM 400 json_validate_failed on translate(%s) — giving up",
                target_code,
            )
            return None

        if resp.status_code >= 400:
            log.warning(
                "LLM %s on translate(%s): %s",
                resp.status_code,
                target_code,
                resp.text[:300],
            )
            return None
        break
    else:
        return None

    try:
        envelope = resp.json()
    except json.JSONDecodeError as exc:
        log.warning("translate(%s): envelope not JSON: %s", target_code, exc)
        return None

    text = _extract_message_content(envelope)
    if not text:
        return None

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        log.warning(
            "translate(%s): model output not JSON: %s", target_code, exc
        )
        return None
    if not isinstance(raw, dict):
        return None
    return raw


async def _translate_single_locale(
    http: httpx.AsyncClient,
    *,
    title: str,
    description: str | None,
    source_language: str,
    target_code: str,
    ingredients: list[str],
    steps: list[str],
) -> dict[str, Any] | None:
    """One-locale translation — two smaller LLM calls (text, then lists).

    A single combined call often exceeds Groq free-tier output limits for
    CJK/Vietnamese recipes with many ingredients and steps.
    """
    has_ingredients = bool(ingredients)
    has_steps = bool(steps)
    ingredients_count = len(ingredients)
    steps_count = len(steps)

    target_name = LANGUAGE_NAMES.get(target_code, target_code)
    src_name = LANGUAGE_NAMES.get(source_language, source_language)

    system = (
        "You are a culinary translator. Translate recipe content from "
        f"{src_name} to {target_name}. Preserve culinary terms and proper "
        "nouns (dish names, place names) — render them in the target "
        "language's natural orthography where established (e.g. 'フォー' for "
        "Vietnamese 'Phở' in Japanese); otherwise keep them in the "
        "original script. Translate measurements naturally (e.g. "
        "'1 tbsp' → '1 muỗng canh' for Vietnamese, '1 大さじ' for "
        "Japanese) but NEVER change the numeric quantity. Keep "
        "descriptions tight (one or two sentences) and match the "
        "source's tone. Keep step bodies as imperative cooking "
        "instructions — DO NOT add greetings, commentary, or extra "
        "tips that aren't in the source. Output JSON ONLY."
    )

    def _payload(user_msg: str, max_tokens: int) -> dict[str, Any]:
        return {
            "model": _settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "stream": False,
        }

    entry: dict[str, Any] = {}

    # Phase 1 — title + description only.
    text_user = "\n".join(
        [
            f"Title: {title}",
            f"Description: {description or ''}",
            "",
            f"Translate into {target_name} and return JSON:",
            '{"title": "...", "description": "..."}',
        ]
    )
    text_raw = await _post_translate_json(
        http, _payload(text_user, 1024), target_code=target_code
    )
    if text_raw:
        t = text_raw.get("title")
        if isinstance(t, str) and t.strip():
            entry["title"] = t.strip()
        d = text_raw.get("description")
        if isinstance(d, str) and d.strip():
            entry["description"] = d.strip()

    if has_ingredients or has_steps:
        await asyncio.sleep(5.0)
        list_lines: list[str] = []
        bundle_fields: list[str] = []
        if has_ingredients:
            list_lines.append(
                f"Ingredients (translate every entry, return {ingredients_count} "
                "items in the same order, do NOT merge or split entries):"
            )
            for i, item in enumerate(ingredients, start=1):
                list_lines.append(f"  {i}. {item}")
            bundle_fields.append('"ingredients": ["...", "..."]')
        if has_steps:
            if list_lines:
                list_lines.append("")
            list_lines.append(
                f"Steps (translate every entry, return {steps_count} items in the "
                "same order, do NOT merge or split entries):"
            )
            for i, item in enumerate(steps, start=1):
                list_lines.append(f"  {i}. {item}")
            bundle_fields.append('"steps": ["...", "..."]')
        list_user = "\n".join(
            [
                *list_lines,
                "",
                f"Translate into {target_name} and return JSON:",
                "{" + ", ".join(bundle_fields) + "}",
            ]
        )
        list_raw = await _post_translate_json(
            http, _payload(list_user, 3072), target_code=target_code
        )
        if list_raw:
            if has_ingredients:
                ings = list_raw.get("ingredients")
                if (
                    isinstance(ings, list)
                    and len(ings) == ingredients_count
                    and all(isinstance(x, str) and x.strip() for x in ings)
                ):
                    entry["ingredients"] = [x.strip() for x in ings]
            if has_steps:
                steps_out = list_raw.get("steps")
                if (
                    isinstance(steps_out, list)
                    and len(steps_out) == steps_count
                    and all(isinstance(x, str) and x.strip() for x in steps_out)
                ):
                    entry["steps"] = [x.strip() for x in steps_out]

    return entry or None


def _retry_after_seconds(resp: httpx.Response) -> float | None:
    """Extract a retry-delay hint from a 429 response.

    Groq sends `Retry-After: 25` as a header AND embeds the same
    value (with sub-second precision) in the JSON error body
    (e.g. `"Please try again in 24.74s"`). We prefer the header
    when present, fall back to the body regex, and clamp to a
    sane ceiling so a misconfigured server can't make us sleep
    for hours.
    """
    header = resp.headers.get("retry-after")
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    try:
        body = resp.text
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"try again in ([\d.]+)\s*s", body)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


# Compatibility shim — the old function name is preserved so any callers
# we missed still work. New code should use `translate_recipe_content`.
translate_title_description = translate_recipe_content


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
