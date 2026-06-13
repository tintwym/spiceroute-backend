"""System prompts and JSON schemas for the AI Creator and AI Companion."""

from __future__ import annotations

import json
from typing import Any

# Languages we support across the UI. Used in prompts to nudge the model into
# producing recipe content in the user's selected language. MUST stay in sync
# with `SUPPORTED_LANGUAGES` in `app/schemas/spice_route.py` and with the
# Flutter app's ARB files (spiceroute-flutter/lib/l10n/*.arb).
LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Mandarin Chinese (Simplified)",
    "my": "Burmese (Myanmar)",
    "ja": "Japanese",
    "ko": "Korean",
    "vi": "Vietnamese",
}


def recipe_system_prompt(language: str, cuisine: str | None) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    cuisine_clause = (
        f"The recipe must clearly belong to {cuisine.replace('_', '/')} cuisine. "
        if cuisine
        else "Pick a cuisine that fits the user's idea best. "
    )
    return (
        "You are a Michelin-trained chef writing for a global home audience. "
        f"Generate a single, faithful, well-structured recipe in {lang_name}. "
        f"{cuisine_clause}"
        "Be precise: include realistic prep / cook minutes, sensible servings, "
        "and a spice level from 0 (no heat) to 3 (very hot). "
        "Estimate calories_per_serving as a single integer (kcal per serving) "
        "based on the ingredient quantities. Round to the nearest 10. Omit "
        "the field only if the recipe is genuinely uncountable (e.g. a sauce "
        "consumed in tiny dollops). "
        "Ingredients must have explicit quantity + unit when applicable. "
        "Steps must be numbered chronologically and concise (one action per step). "
        "Do NOT invent images. Do NOT include markdown. Output JSON ONLY, "
        "matching the JSON schema given in the user message."
    )


# JSON schema we ask the model to conform its recipe response to. Mirrors the
# `SpiceRouteCreate` Pydantic schema closely enough that we can hand the parsed
# dict almost directly to the persistence layer.
#
# IMPORTANT: this is now used in two ways. With Gemini we passed it as
# `response_schema` and the SDK enforced it on the decoder side. With Ollama
# there is no such enforcement (`format: "json"` only guarantees valid JSON),
# so we additionally inline this schema into the user prompt and lean on the
# Pydantic validator in the API layer (which silently drops unknown keys) plus
# the API's existing one-shot retry-on-AIError to recover from the occasional
# small-model hallucination of an extra wrapper or a missing field.
RECIPE_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "required": ["title", "ingredients", "steps", "cuisine", "language"],
    "properties": {
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "description": {"type": "string", "maxLength": 1000},
        "prep_minutes": {"type": "integer", "minimum": 0, "maximum": 600},
        "cook_minutes": {"type": "integer", "minimum": 0, "maximum": 600},
        "servings": {"type": "integer", "minimum": 1, "maximum": 50},
        "cuisine": {
            "type": "string",
            # MUST stay in lock-step with `Cuisine` in
            # `app/models/cuisine.py` and the Flutter `Cuisine` enum in
            # `lib/models/spice_route.dart`. Adding a cuisine means
            # updating all three places (plus an Alembic migration to
            # ALTER the Postgres `cuisine_type` enum).
            "enum": [
                "korean",
                "japanese",
                "chinese",
                "burmese",
                "thai",
                "vietnamese",
                "indian",
                "italian",
                "american_western",
                "mexican",
                "french",
                "greek",
                "spanish",
                "malaysian",
                "german",
                "indonesian",
            ],
        },
        "language": {
            "type": "string",
            # MUST stay in lock-step with `SUPPORTED_LANGUAGES` in
            # `app/schemas/spice_route.py`. Drift here was historically
            # the cause of a silent Burmese-generation bug: with `my`
            # missing from the enum the model would fall back to `en`
            # and the saved row was mis-tagged (or rejected by Pydantic)
            # even though the prose was Burmese. Adding a language to
            # the app means updating BOTH places.
            "enum": ["en", "zh", "my", "ja", "ko", "vi"],
        },
        "spice_level": {"type": "integer", "minimum": 0, "maximum": 3},
        "calories_per_serving": {
            "type": "integer",
            "minimum": 0,
            "maximum": 20000,
        },
        "ingredients": {
            "type": "array",
            "minItems": 1,
            "maxItems": 50,
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "quantity": {"type": "number", "minimum": 0},
                    "unit": {"type": "string", "maxLength": 32},
                    "name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200,
                    },
                },
            },
        },
        "steps": {
            "type": "array",
            "minItems": 1,
            "maxItems": 50,
            "items": {
                "type": "object",
                "required": ["body"],
                "properties": {
                    "body": {"type": "string", "minLength": 1, "maxLength": 800}
                },
            },
        },
        "tags": {
            "type": "array",
            "maxItems": 8,
            "items": {"type": "string", "maxLength": 32},
        },
    },
}


def recipe_user_prompt(*, idea: str, schema: dict[str, Any]) -> str:
    """User-side prompt for the recipe generator.

    On Gemini this was just `idea` (the SDK injected the schema separately).
    On Ollama there's no `response_schema`, so we ship the schema inline as
    part of the prompt. Models follow inline JSON schemas reasonably well
    when the request also has `format: "json"` set on the wire.

    We pretty-print the schema (indent=2) on purpose: it's easier for the
    model to follow when it's not a single 1.5 KB blob, and the extra
    tokens are negligible against the recipe response itself.
    """
    return (
        f"User idea: {idea}\n\n"
        "Return a JSON object that conforms EXACTLY to this JSON schema. "
        "Only the keys defined in the schema may appear. Use the literal "
        "string values from each `enum` (do not translate enum keys). Do "
        "NOT wrap the object in any envelope (no `recipe`, `data`, etc.) "
        "and do NOT include any prose, markdown fences, or commentary — "
        "just the JSON object.\n\n"
        f"JSON schema:\n{json.dumps(schema, indent=2)}"
    )


def chat_system_prompt(language: str) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    return (
        "You are the AI Kitchen Companion for the SpiceRoute app. "
        "You help home cooks across sixteen cuisines: Korean, Japanese, "
        "Chinese, Burmese, Thai, Vietnamese, Indian, Italian, "
        "American/Western, Mexican, French, Greek, Spanish, Malaysian, "
        "German, and Indonesian. "
        "Give practical, friendly answers about ingredient substitutes, "
        "cooking techniques, dietary adaptations (vegan, keto, gluten-free), "
        "and quick recipes. Keep responses tight (3-6 sentences unless the "
        "user explicitly asks for a full recipe). "
        f"Respond in {lang_name} unless the user writes in another language, "
        "in which case match the language they're using."
    )
