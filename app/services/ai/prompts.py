"""System prompts and JSON schemas for the AI Creator and AI Companion."""

# Languages we support across the UI. Used in prompts to nudge the model into
# producing recipe content in the user's selected language.
LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Mandarin Chinese (Simplified)",
    "th": "Thai",
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
        "matching the provided schema."
    )


# JSON schema we ask Gemini to conform its recipe response to. Mirrors the
# `SpiceRouteCreate` Pydantic schema closely enough that we can hand the parsed
# dict almost directly to the persistence layer.
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
            "enum": [
                "korean",
                "japanese",
                "chinese",
                "burmese",
                "thai",
                "indian",
                "italian",
                "american_western",
                "mexican",
            ],
        },
        "language": {
            "type": "string",
            "enum": ["en", "zh", "th", "ja", "ko", "vi"],
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


def chat_system_prompt(language: str) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    return (
        "You are the AI Kitchen Companion for the Savor Global Recipes app. "
        "You help home cooks across nine cuisines: Korean, Japanese, Chinese, "
        "Burmese, Thai, Indian, Italian, American/Western, and Mexican. "
        "Give practical, friendly answers about ingredient substitutes, "
        "cooking techniques, dietary adaptations (vegan, keto, gluten-free), "
        "and quick recipes. Keep responses tight (3-6 sentences unless the "
        "user explicitly asks for a full recipe). "
        f"Respond in {lang_name} unless the user writes in another language, "
        "in which case match the language they're using."
    )
