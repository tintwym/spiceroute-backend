"""Shared helpers for per-locale recipe `translations` JSONB."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spice_route import SpiceRoute
from app.services.ai import llm
from app.services.ai.prompts import LANGUAGE_NAMES
from app.services.spice_routes import format_ingredient_line
from scripts.translation_utils import is_stub_locale_bundle, merge_translation_bundle


def locale_needs_summary_backfill(row: SpiceRoute, locale: str) -> bool:
    """True when [locale] title/description are missing or still English stubs."""
    src = (row.language or "en").strip().lower()
    target = locale.strip().lower()
    if not target or target == src:
        return False
    translations = row.translations if isinstance(row.translations, dict) else {}
    bundle = translations.get(target)
    return is_stub_locale_bundle(
        bundle if isinstance(bundle, dict) else None,
        source_title=row.title,
        source_description=row.description,
    )


def _bundle_is_complete(
    bundle: dict | None,
    expected_ingredients: int,
    expected_steps: int,
) -> bool:
    if not isinstance(bundle, dict):
        return False
    ings = bundle.get("ingredients")
    steps = bundle.get("steps")
    if not isinstance(ings, list) or len(ings) != expected_ingredients:
        return False
    if not isinstance(steps, list) or len(steps) != expected_steps:
        return False
    if not all(isinstance(x, str) and x.strip() for x in ings):
        return False
    if not all(isinstance(x, str) and x.strip() for x in steps):
        return False
    return True


def row_needs_backfill(row: SpiceRoute) -> bool:
    """True when any non-source locale lacks real title/description or
    ingredient/step arrays."""
    src = row.language or "en"
    targets = [code for code in LANGUAGE_NAMES if code != src]
    if not targets:
        return False
    translations = row.translations if isinstance(row.translations, dict) else {}
    expected_ings = len(row.ingredients)
    expected_steps = len(row.steps)
    for code in targets:
        bundle = translations.get(code)
        if is_stub_locale_bundle(
            bundle if isinstance(bundle, dict) else None,
            source_title=row.title,
            source_description=row.description,
        ):
            return True
        if row.ingredients or row.steps:
            if not _bundle_is_complete(bundle, expected_ings, expected_steps):
                return True
    return False


def source_ingredient_lines(row: SpiceRoute) -> list[str]:
    return [
        format_ingredient_line(quantity=i.quantity, unit=i.unit, name=i.name)
        for i in row.ingredients
    ]


def source_step_lines(row: SpiceRoute) -> list[str]:
    return [s.body for s in row.steps]


async def ensure_row_translations(db: AsyncSession, row: SpiceRoute) -> bool:
    """LLM-fill missing locale bundles and persist. Returns True when the
    row was updated. No-op in stub mode or when already complete."""
    if not row_needs_backfill(row):
        return False
    fresh = await llm.translate_recipe_content(
        title=row.title,
        description=row.description,
        source_language=row.language or "en",
        ingredients=source_ingredient_lines(row),
        steps=source_step_lines(row),
    )
    if not fresh:
        return False
    merged = merge_translation_bundle(
        row.translations,
        fresh,
        source_title=row.title,
        source_description=row.description,
    )
    if merged == row.translations:
        return False
    row.translations = merged
    await db.commit()
    await db.refresh(row)
    return True


async def ensure_row_locale_summary(
    db: AsyncSession, row: SpiceRoute, locale: str
) -> bool:
    """LLM-fill title + description for one locale (Explore cards). Returns
    True when the row was updated."""
    if not locale_needs_summary_backfill(row, locale):
        return False
    fresh = await llm.translate_recipe_summary_for_locale(
        title=row.title,
        description=row.description,
        source_language=row.language or "en",
        target_code=locale.strip().lower(),
    )
    if not fresh:
        return False
    merged = merge_translation_bundle(
        row.translations,
        {locale.strip().lower(): fresh},
        source_title=row.title,
        source_description=row.description,
    )
    if merged == row.translations:
        return False
    row.translations = merged
    await db.commit()
    await db.refresh(row)
    return True
