"""Helpers for detecting and merging per-locale recipe translations.

Expansion generators used to copy the English `title` / `description`
into every locale bundle. Those stubs look "complete" to naive merge
logic but render as English on zh/ja/ko/vi Explore cards. Use these
helpers anywhere we read or write `spice_routes.translations`.
"""
from __future__ import annotations

import re
from typing import Any


def _norm(s: str | None) -> str:
    return (s or "").strip()


def _is_mostly_cjk(text: str) -> bool:
    non_space = [ch for ch in text if not ch.isspace()]
    if not non_space:
        return False
    cjk = sum(
        1
        for ch in non_space
        if "\u4e00" <= ch <= "\u9fff"
        or "\u3040" <= ch <= "\u30ff"
        or "\uac00" <= ch <= "\ud7af"
    )
    return cjk / len(non_space) >= 0.5


def _is_ascii_letters_only(text: str) -> bool:
    stripped = text.replace(" ", "")
    return bool(stripped) and all(c.isascii() and c.isalpha() for c in stripped)


def _is_degraded_romanization(text: str) -> bool:
    """Space-separated Latin tokens with diacritics stripped — e.g. 'Ch tr m t'."""
    text = _norm(text)
    if not text or not _is_ascii_letters_only(text):
        return False
    tokens = text.split()
    if len(tokens) < 3:
        return False
    short = sum(1 for t in tokens if len(t) <= 2)
    return short / len(tokens) >= 0.6


def _has_repeated_phrase(text: str) -> bool:
    """Same 4+ char substring appears twice — LLM loop / copy glitch."""
    text = _norm(text)
    n = len(text)
    if n < 12:
        return False
    for size in range(4, min(16, n // 2 + 1)):
        counts: dict[str, int] = {}
        for i in range(n - size + 1):
            phrase = text[i : i + size]
            if len(phrase.strip()) < 4:
                continue
            counts[phrase] = counts.get(phrase, 0) + 1
            if counts[phrase] >= 2:
                return True
    return False


def is_garbage_translation_text(
    text: str | None,
    *,
    field: str = "text",
) -> bool:
    """Heuristic for LLM garbage (repeated chars, absurdly low diversity)."""
    text = _norm(text)
    if not text:
        return True
    if field == "title" and len(text) <= 3 and _is_ascii_letters_only(text):
        # Stripped Vietnamese debris like "Ch" — real dish names are longer
        # or use native script / diacritics.
        return True
    if _is_degraded_romanization(text):
        return True
    if _has_repeated_phrase(text):
        return True
    if re.search(r"(.)\1{4,}", text):
        return True
    n = len(text)
    diversity = len(set(text))
    if n > 6 and diversity < max(3, n // 3):
        return True
    # Long mostly-CJK strings where fewer than half the glyphs are unique —
    # catches looping nonsense like "红尺索尺零和索尺索尺".
    if n >= 8 and diversity <= n // 2 and _is_mostly_cjk(text):
        return True
    # Looping bigrams — "年应米尼…尼米尼…" / "…湖湖强…"
    if n >= 8 and _is_mostly_cjk(text):
        for i in range(n - 1):
            bigram = text[i : i + 2].strip()
            if len(bigram) == 2 and text.count(bigram) >= 3:
                return True
    return False


def _is_stub_title(cur: object, source_title: str) -> bool:
    if not isinstance(cur, str) or not _norm(cur):
        return True
    return _norm(cur) == _norm(source_title)


def _is_stub_description(cur: object, source_description: str | None) -> bool:
    if not source_description:
        return False
    if not isinstance(cur, str) or not _norm(cur):
        return True
    return _norm(cur) == _norm(source_description)


def is_stub_title_value(cur: object, source_title: str) -> bool:
    return _is_stub_title(cur, source_title)


def is_stub_description_value(
    cur: object, source_description: str | None
) -> bool:
    return _is_stub_description(cur, source_description)


def is_stub_locale_bundle(
    bundle: dict | None,
    *,
    source_title: str,
    source_description: str | None,
) -> bool:
    """True when a locale bundle's title/description are missing or still
    the untranslated English source strings."""
    if not isinstance(bundle, dict):
        return True
    title = bundle.get("title")
    if not isinstance(title, str) or not _norm(title):
        return True
    if _norm(title) == _norm(source_title):
        return True
    if source_description:
        desc = bundle.get("description")
        if not isinstance(desc, str) or not _norm(desc):
            return True
        if _norm(desc) == _norm(source_description):
            return True
    return False


def strip_stub_bundles(
    translations: dict | None,
    *,
    source_title: str,
    source_description: str | None,
) -> dict | None:
    """Drop per-locale title/description keys that are English stubs.

    Leaves ingredients/steps intact. Returns `None` when nothing remains.
    """
    if not isinstance(translations, dict):
        return None
    out: dict = {}
    for code, bundle in translations.items():
        if not isinstance(bundle, dict):
            continue
        cleaned = dict(bundle)
        if is_stub_locale_bundle(
            cleaned, source_title=source_title, source_description=source_description
        ):
            cleaned.pop("title", None)
            cleaned.pop("description", None)
        else:
            t = cleaned.get("title")
            if isinstance(t, str) and is_garbage_translation_text(t, field="title"):
                cleaned.pop("title", None)
            d = cleaned.get("description")
            if isinstance(d, str) and is_garbage_translation_text(d, field="description"):
                cleaned.pop("description", None)
        if cleaned:
            out[code] = cleaned
    return out or None


def merge_translation_bundle(
    existing: dict | None,
    fresh: dict[str, dict],
    *,
    source_title: str,
    source_description: str | None,
) -> dict:
    """Merge LLM output into stored translations.

    Fresh wins for ingredients/steps. Title/description are replaced when
    missing OR when the stored value is still an English stub identical
    to the source row — so hand-polished overrides (e.g. curated_data.py)
    survive re-runs.
    """
    if not isinstance(existing, dict):
        existing = {}
    out: dict[str, dict[str, Any]] = {}
    for code in set(existing.keys()) | set(fresh.keys()):
        cur_raw = existing.get(code)
        new_raw = fresh.get(code)
        cur: dict[str, Any] = cur_raw if isinstance(cur_raw, dict) else {}
        new: dict[str, Any] = new_raw if isinstance(new_raw, dict) else {}
        merged: dict[str, Any] = dict(cur)
        if "ingredients" in new:
            merged["ingredients"] = new["ingredients"]
        if "steps" in new:
            merged["steps"] = new["steps"]
        for field in ("title", "description"):
            if field not in new:
                continue
            if field == "title":
                if _is_stub_title(merged.get("title"), source_title):
                    merged["title"] = new["title"]
            elif _is_stub_description(merged.get("description"), source_description):
                merged["description"] = new["description"]
        if merged:
            out[code] = merged
    return out


def invalid_locale_codes(
    translations: dict[str, dict[str, str]] | None,
    *,
    source_title: str,
    source_description: str | None,
    required_locales: tuple[str, ...] = ("zh", "ja", "ko", "vi"),
) -> list[str]:
    """Locales missing or carrying stub/garbage title+description."""
    bad: list[str] = []
    for code in required_locales:
        bundle = (translations or {}).get(code)
        if not isinstance(bundle, dict):
            bad.append(code)
            continue
        title = bundle.get("title")
        desc = bundle.get("description")
        if is_stub_locale_bundle(
            bundle, source_title=source_title, source_description=source_description
        ):
            bad.append(code)
            continue
        if is_garbage_translation_text(str(title), field="title") or is_garbage_translation_text(
            str(desc), field="description"
        ):
            bad.append(code)
    return bad
