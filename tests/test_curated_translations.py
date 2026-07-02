"""Regression test for curated-recipe translation hygiene.

A previous version of `scripts/curated_data.py` had eight curated
recipes whose `translations` dicts were entirely about a different
dish (Korean Fried Chicken pointed at Oyakodon, Shan Noodles at
Dal Tadka, Mohinga at Pho Bo, …). The English source title /
description column was right but every per-locale override pointed
the resolver at the wrong dish, so users on every non-English UI
locale saw a completely different recipe under the English title.

These tests are the data-quality gate that catches that class of
bug at CI time, before it ships:

  1) No two curated recipes may share an identical translated title
     in the same locale (e.g. Beef and Broccoli and Green Papaya
     Salad both showing "青木瓜沙拉" for zh.title).
  2) No translated title may exactly equal another recipe's English
     source title (the most common copy-paste fingerprint).
  3) Every supported UI locale (zh/ja/ko/vi) MUST have a translation
     bundle on every curated recipe — missing translations would
     leave the user stuck on English for that one row.

These run in the normal `pytest` invocation, so a future deploy that
adds a curated recipe with a swapped translation will fail CI
instead of silently shipping.
"""
from __future__ import annotations

from collections import defaultdict

from scripts.curated_data import CURATED
from scripts.translation_utils import is_stub_locale_bundle

SUPPORTED_UI_LOCALES = ("zh", "ja", "ko", "vi")


def test_no_two_recipes_share_translated_title_in_any_locale() -> None:
    """Per-locale uniqueness: each translated title must be unique.

    Two recipes sharing the same translated title is the smoking
    fingerprint of a copy-paste swap — either someone duplicated a
    block, or two recipes got translated to the same generic name
    (e.g. both "Vietnamese Spring Roll"). Either way it's a bug we
    want to know about at CI, not in production.
    """
    for locale in SUPPORTED_UI_LOCALES:
        title_to_recipes: dict[str, list[str]] = defaultdict(list)
        for r in CURATED:
            bundle = (r.get("translations") or {}).get(locale)
            if not isinstance(bundle, dict):
                continue
            t = (bundle.get("title") or "").strip()
            if not t:
                continue
            title_to_recipes[t].append(r["title"])
        duplicates = {
            title: names
            for title, names in title_to_recipes.items()
            if len(names) > 1
        }
        assert not duplicates, (
            f"Multiple curated recipes share an identical translated "
            f"title in locale {locale!r}: {duplicates}. Each translated "
            f"title must be unique — when two share, it's almost always a "
            f"copy-paste swap that puts the wrong dish under the right "
            f"English name on every {locale!r} UI."
        )


def test_translated_title_never_equals_another_recipes_en_source() -> None:
    """If a recipe's `translations[loc].title` equals the EN source
    title of a DIFFERENT curated recipe, the bundle was almost
    certainly pasted in from that other recipe by mistake.

    E.g. `Egg Drop Soup.translations.vi.title = "Pad Krapow Gai"`
    is the exact tell-tale of a swap — Vietnamese-locale users
    would see Pad Krapow Gai's name on the Egg Drop Soup card."""
    en_titles = {r["title"] for r in CURATED}
    bad: list[str] = []
    for r in CURATED:
        tr = r.get("translations") or {}
        for locale in SUPPORTED_UI_LOCALES:
            bundle = tr.get(locale) or {}
            t = (bundle.get("title") or "").strip()
            if t in en_titles and t != r["title"]:
                bad.append(
                    f"  - {r['title']} ({r['cuisine']}) "
                    f"{locale}.title = {t!r} (which is another recipe's "
                    f"EN source title — looks like a paste swap)"
                )
    assert not bad, (
        "Some curated recipes have a translated title that exactly "
        "matches a DIFFERENT recipe's English source title — this is "
        "the fingerprint of a copy-paste swap. Fix the translations "
        "block on each flagged row:\n" + "\n".join(bad)
    )


def test_every_curated_recipe_has_all_ui_locales() -> None:
    """Curated recipes with translation blocks must carry real per-locale copy."""
    missing: list[str] = []
    stubs: list[str] = []
    for r in CURATED:
        tr = r.get("translations") or {}
        if not tr:
            continue
        for locale in SUPPORTED_UI_LOCALES:
            bundle = tr.get(locale)
            if not isinstance(bundle, dict):
                missing.append(
                    f"  - {r['title']} ({r['cuisine']}): missing {locale!r}"
                )
                continue
            if is_stub_locale_bundle(
                bundle,
                source_title=r["title"],
                source_description=r.get("description"),
            ):
                stubs.append(
                    f"  - {r['title']} ({r['cuisine']}): {locale} is an "
                    f"English stub (title/description match source)"
                )
                continue
            t = (bundle.get("title") or "").strip()
            d = (bundle.get("description") or "").strip()
            if locale != r.get("language") and not t:
                missing.append(
                    f"  - {r['title']} ({r['cuisine']}): {locale}.title is empty"
                )
            if not d:
                missing.append(
                    f"  - {r['title']} ({r['cuisine']}): {locale}.description is empty"
                )
    assert not missing, (
        "Some curated recipes are missing translations for one or more "
        "supported UI locales. Every recipe must have a non-empty title "
        "and description for zh / ja / ko / vi so users in those locales "
        "never fall back to the source language:\n" + "\n".join(missing)
    )
    assert not stubs, (
        "Some curated recipes ship English copy-paste stubs in zh/ja/ko/vi "
        "instead of real translations. Remove the stub block (backfill at "
        "deploy) or replace with hand-polished copy:\n" + "\n".join(stubs)
    )
