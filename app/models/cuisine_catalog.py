"""Presentation helpers for the cuisine catalog.

Sub-national enum values (provinces, cities, ethnic regions) stay in Postgres
for backwards compatibility, but the product surfaces one picker row per
country and migrates rows to the parent country wire.
"""
from __future__ import annotations

from app.models.cuisine import Cuisine

# Keep in sync with `spiceroute-flutter/lib/models/cuisine_catalog.dart`

CHINESE_PROVINCIAL_WIRES: tuple[str, ...] = (
    "sichuan",
    "cantonese",
    "shanghainese",
    "fujian",
    "hunan",
    "yunnan",
    "beijing",
    "dongbei",
    "hakka",
    "shandong",
    "guangxi",
    "teochew",
    "hainanese",
    "jiangsu",
    "zhejiang",
    "anhui",
    "jiangxi",
    "guizhou",
    "manchurian",
    "shaanxi",
)

CHINESE_SUBNATIONAL_WIRES: tuple[str, ...] = CHINESE_PROVINCIAL_WIRES + (
    "hong_kong",
    "macanese",
    "tibetan",
    "uyghur",
)

MYANMAR_REGIONAL_WIRES: tuple[str, ...] = (
    "shan",
    "rakhine",
    "mon",
    "kachin",
    "kayin",
    "chin",
    "kayah",
    "mandalay",
    "yangon",
    "ayeyarwady",
    "tanintharyi",
    "intha",
    "naga",
    "pa_o",
    "danu",
    "wa",
    "magway",
    "bago",
    "sagaing",
    "taunggyi",
)

JAPANESE_SUBNATIONAL_WIRES: tuple[str, ...] = ("okinawan",)

CHINESE_PROVINCIAL: frozenset[Cuisine] = frozenset(
    Cuisine(w) for w in CHINESE_PROVINCIAL_WIRES
)
CHINESE_SUBNATIONAL: frozenset[Cuisine] = frozenset(
    Cuisine(w) for w in CHINESE_SUBNATIONAL_WIRES
)
MYANMAR_REGIONAL: frozenset[Cuisine] = frozenset(
    Cuisine(w) for w in MYANMAR_REGIONAL_WIRES
)
JAPANESE_SUBNATIONAL: frozenset[Cuisine] = frozenset(
    Cuisine(w) for w in JAPANESE_SUBNATIONAL_WIRES
)

SUBNATIONAL_WIRES: frozenset[str] = frozenset(
    CHINESE_SUBNATIONAL_WIRES + MYANMAR_REGIONAL_WIRES + JAPANESE_SUBNATIONAL_WIRES
)

_PARENT_BY_SUBNATIONAL: dict[Cuisine, Cuisine] = {
    **{c: Cuisine.CHINESE for c in CHINESE_SUBNATIONAL},
    **{c: Cuisine.BURMESE for c in MYANMAR_REGIONAL},
    **{c: Cuisine.JAPANESE for c in JAPANESE_SUBNATIONAL},
}

_EXPANDED_FILTER: dict[Cuisine, tuple[Cuisine, ...]] = {
    Cuisine.CHINESE: (Cuisine.CHINESE, *CHINESE_SUBNATIONAL),
    Cuisine.BURMESE: (Cuisine.BURMESE, *MYANMAR_REGIONAL),
    Cuisine.JAPANESE: (Cuisine.JAPANESE, *JAPANESE_SUBNATIONAL),
}


def cuisine_for_display(cuisine: Cuisine) -> Cuisine:
    return _PARENT_BY_SUBNATIONAL.get(cuisine, cuisine)


def cuisine_filter_values(cuisine: Cuisine | None) -> list[Cuisine] | None:
    """Expand country filters to include legacy sub-national rows."""
    if cuisine is None:
        return None
    expanded = _EXPANDED_FILTER.get(cuisine)
    if expanded is not None:
        return list(expanded)
    return [cuisine]


def ai_cuisine_enum_values() -> list[str]:
    """Cuisines the AI Creator may emit — country level only."""
    return [c.value for c in Cuisine if c.value not in SUBNATIONAL_WIRES]
