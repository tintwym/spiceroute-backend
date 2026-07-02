"""Resolve the UI locale a recipe read should translate into."""

from __future__ import annotations

from app.services.ai.prompts import LANGUAGE_NAMES

_SUPPORTED = frozenset(LANGUAGE_NAMES.keys())


def locale_from_accept_language(header: str | None) -> str | None:
    """Pick the first supported locale from an HTTP Accept-Language header."""
    if not header:
        return None
    for part in header.split(","):
        token = part.split(";")[0].strip().lower()
        if not token:
            continue
        code = token.split("-")[0]
        if code in _SUPPORTED:
            return code
    return None


def requested_translation_locale(
    *,
    translate_to: str | None,
    accept_language: str | None,
) -> str | None:
    """Locale for `_resolve_translation`.

  `translate_to` wins when present. Otherwise fall back to
  Accept-Language so older web bundles that forgot the query param
  still receive localized card copy.
    """
    explicit = (translate_to or "").strip().lower() or None
    if explicit and explicit in _SUPPORTED:
        return explicit
    return locale_from_accept_language(accept_language)
