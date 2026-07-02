"""Seed the database with the 93 curated `is_premium=True` recipes.

Idempotent: re-running won't duplicate existing curated recipes (matched by
exact title). Safe to run after every deploy.

Usage:
    uv run python -m scripts.seed_curated_recipes            # full run
    uv run python -m scripts.seed_curated_recipes --quick    # deploy hook

The `--quick` flag skips the (slow, network-bound) image-resolution step
for recipes that already exist with a non-empty `image_path`. New rows
still resolve images, but re-runs against a populated DB return in a
couple of seconds instead of 30+. Use this from `release.sh` so every
Render deploy isn't blocked on HEAD requests to Flickr.
"""
import argparse
import asyncio
import re
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.cuisine import Cuisine
from app.models.difficulty import Difficulty, compute_difficulty
from app.models.spice_route import Ingredient, SpiceRoute, Step
from app.models.tag import Tag
from scripts.curated_data import CURATED
from scripts.recipe_images import is_broken_image_url, stable_food_image_url
from scripts.translation_utils import strip_stub_bundles

# Matches LoremFlickr's resolved cache URL, which has two shapes:
#   1. With explicit Flickr size letter:
#      .../cache/resized/{server}_{photo}_{secret}_z_400_300_nofilter.jpg
#   2. With just LoremFlickr's resize dimensions (no size letter):
#      .../cache/resized/{server}_{photo}_{secret}_1200_800_nofilter.jpg
# Both contain server / photo / secret which is everything we need to
# rebuild the permanent Flickr CDN URL.
_LOREMFLICKR_RESOLVED_PATTERN = re.compile(
    r"loremflickr\.com/cache/resized/"
    r"(?P<server>\d+)_(?P<photo>\d+)_(?P<secret>[a-z0-9]+)_"
)


def _is_url_alive(url: str, timeout: float = 10.0) -> bool:
    """HEAD-check a URL. Returns True only on 2xx with non-trivial body.

    Flickr's CDN returns HTTP 410 Gone for photos that have been deleted
    or made private by their owner. We have to filter these out because
    LoremFlickr happily serves search results that point at long-dead
    photos (their cache layer used to mask this, but the cache eviction
    has caught up).
    """
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _candidate_lock_values(base_seed: int) -> list[int]:
    """Generate up to 12 deterministic lock values to try in order.

    Starting from the base hash, we expand outwards so the same seed
    always produces the same sequence (-> same image picked on every
    re-seed run, no flakiness).
    """
    return [base_seed % 99999] + [
        (base_seed + offset * 7919) % 99999 for offset in range(1, 12)
    ]


def _resolve_image_url(url: str, timeout: float = 15.0) -> str:
    """Resolve a LoremFlickr search URL to a *verified-alive* Flickr CDN URL.

    Why this is necessary: LoremFlickr is a redirect-and-search service.
    Its resolved `cache/resized/...` URL contains a real Flickr photo
    ID, but a large fraction of Flickr's CC pool has been deleted /
    privated over the years, so a naive resolve frequently lands on a
    URL that returns HTTP 410 Gone.

    Strategy:
      1. Generate ~12 candidate `lock=N` values from the slug's hash.
      2. For each, resolve via LoremFlickr to the underlying Flickr URL.
      3. HEAD-check that the Flickr URL is alive.
      4. Return the first alive one. Same input slug always produces
         the same sequence, so re-runs are deterministic.
      5. If nothing is alive (rare), return the original search URL so
         the recipe at least keeps showing *some* image at runtime.
    """
    if "loremflickr.com" not in url:
        return url
    # Parse the URL once so we can swap the lock value in/out cleanly.
    base = url.split("?")[0]  # https://loremflickr.com/1200/800/kw[/all]
    # Pull the original lock for deterministic seed expansion.
    lock_match = re.search(r"lock=(\d+)", url)
    base_seed = int(lock_match.group(1)) if lock_match else 0
    locks = _candidate_lock_values(base_seed)
    # Try with /all first (strict match), then loosen to OR-match if the
    # whole batch is unmatchable. _candidate_lock_values is identical
    # across both passes, so we always exhaust strict matches first.
    base_strict = base if "/all" in base else f"{base}/all"
    base_loose = base.replace("/all", "")
    for base_url in (base_strict, base_loose):
        for lock in locks:
            attempt = f"{base_url}?lock={lock}"
            try:
                req = urllib.request.Request(attempt, method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    final = r.url
                if "defaultImage" in final:
                    continue
                m = _LOREMFLICKR_RESOLVED_PATTERN.search(final)
                if not m:
                    continue
                flickr_url = (
                    f"https://live.staticflickr.com/{m['server']}/"
                    f"{m['photo']}_{m['secret']}_b.jpg"
                )
                if _is_url_alive(flickr_url, timeout=timeout):
                    return flickr_url
            except (urllib.error.URLError, TimeoutError, OSError):
                continue
    # LoremFlickr is frequently down (HTTP 500). Fall back to a stable
    # Unsplash CDN photo keyed on the lock seed so cards still show food.
    lock_match = re.search(r"lock=(\d+)", url)
    seed = lock_match.group(1) if lock_match else url
    return stable_food_image_url(f"lf-{seed}")

# Per-cuisine fallback used when a curated recipe doesn't pin its own
# `calories`. These are deliberately rounded mid-range values per serving —
# good enough to populate the chip on Explore until each dish gets an
# explicit estimate.
_CUISINE_KCAL_FALLBACK = {
    "korean": 540,
    "japanese": 480,
    "chinese": 560,
    "burmese": 520,
    "thai": 510,
    "vietnamese": 470,
    "indian": 560,
    "italian": 620,
    "american_western": 700,
    "mexican": 580,
    "french": 620,
    # v4 catalog expansion. Values picked to sit near the middle of each
    # cuisine's typical home-cooked main course — fall back when a
    # curated recipe doesn't pin its own `calories`.
    "lebanese": 510,
    "turkish": 580,
    "moroccan": 540,
    "ethiopian": 500,
    "filipino": 580,
    "pakistani": 620,
    "sri_lankan": 520,
    "cambodian": 490,
    # v4 Phase 2: catalog gaps + remaining Phase 2 cuisines.
    "greek": 560,
    "spanish": 590,
    "malaysian": 600,
    "german": 680,
    "indonesian": 600,
    "brazilian": 640,
    "peruvian": 580,
    "caribbean": 620,
    "taiwanese": 560,
    "portuguese": 580,
    "british": 680,
}

_DEFAULT_KCAL = 520


def _kcal_for_spec(spec: Mapping[str, Any]) -> int:
    """Per-serving calories for a curated spec — explicit value, cuisine
    fallback table, then a sane default so expansion cuisines never seed
    as NULL."""
    calories = spec.get("calories")
    if calories is not None:
        return int(calories)
    return _CUISINE_KCAL_FALLBACK.get(spec["cuisine"], _DEFAULT_KCAL)

# Per-recipe extra tags layered on top of `spec["tags"]` to power the
# Explore filter dropdowns. Frontend `Course` and `Dietary` enums look these
# up by name (case-insensitive) so the strings here must match the
# `tagName` field on those Dart enums exactly.
#
# Tag taxonomy mirrors the v2 filter design (see filter_bar.dart):
#   Courses     : breakfast | lunch | appetizer | side dish | dessert
#                 | snack | drinks
#   Dietary     : vegan | vegetarian
#   Allergen    : gluten-free | dairy-free | nut-free | egg-free
#   Wellness    : blood sugar balanced | swicy | anti-inflammatory
#   Cooking fmt : meal prep | quick | pasta soup
#
# IMPORTANT — tag string format matches the `Dietary.tagName` field on
# the Dart enum LITERALLY (case-insensitive but otherwise exact). The
# allergen tags use hyphens (`gluten-free`, not `gluten free`) to match
# the historical convention here AND the `anti-inflammatory` precedent
# on the dietary side. A subtle space-vs-hyphen drift would silently
# filter Explore to zero matches.
#
# Legacy tags still in use for visible tag display (not filter
# surfacing): main course, dinner, soup, salad, high-protein, low-carb.
_EXTRA_TAGS_BY_TITLE: dict[str, list[str]] = {
    # ---- Korean ----
    "Kimchi Jjigae": [
        "soup", "dinner", "main course",
        "pasta soup", "meal prep",
    ],
    "Bibimbap": [
        "main course", "lunch", "dinner",
        "meal prep", "blood sugar balanced",
    ],
    "Korean Fried Chicken": [
        "main course", "dinner", "high-protein",
        "swicy", "meal prep",
    ],
    # ---- Japanese ----
    "Tamago Donburi": [
        "main course", "lunch", "quick",
    ],
    "Miso Glazed Salmon": [
        "main course", "dinner", "high-protein", "gluten-free",
        "blood sugar balanced", "anti-inflammatory", "meal prep",
    ],
    "Cold Soba with Dipping Sauce": [
        "main course", "lunch", "vegetarian", "quick",
        "pasta soup", "anti-inflammatory",
    ],
    # ---- Chinese ----
    "Mapo Tofu": [
        "main course", "dinner", "vegetarian",
        "swicy", "meal prep",
    ],
    "Egg Drop Soup": [
        "soup", "appetizer", "vegetarian", "gluten-free", "quick",
        "pasta soup",
    ],
    "Beef and Broccoli": [
        "main course", "dinner", "high-protein", "low-carb",
        "blood sugar balanced", "meal prep",
    ],
    # ---- Burmese ----
    "Mohinga": [
        "soup", "breakfast", "main course",
        "pasta soup", "meal prep",
    ],
    "Burmese Tea Leaf Salad": [
        "salad", "snack", "vegetarian", "appetizer",
        "anti-inflammatory",
    ],
    "Shan Noodles": [
        "main course", "lunch", "dinner",
        "pasta soup", "meal prep",
    ],
    # ---- Thai ----
    "Pad Krapow Gai": [
        "main course", "dinner", "quick", "high-protein",
        "swicy", "blood sugar balanced",
    ],
    "Tom Yum Goong": [
        "soup", "appetizer", "gluten-free", "low-carb",
        "pasta soup", "anti-inflammatory",
    ],
    "Green Papaya Salad": [
        "salad", "appetizer", "vegetarian", "gluten-free", "vegan",
        "blood sugar balanced", "anti-inflammatory", "swicy",
    ],
    # ---- Vietnamese ----
    "Pho Bo": [
        "soup", "main course", "lunch", "dinner", "high-protein",
        "pasta soup", "anti-inflammatory",
    ],
    "Banh Mi Thit Nuong": [
        "main course", "lunch", "dinner",
        "meal prep",
    ],
    "Goi Cuon": [
        "appetizer", "snack", "lunch", "gluten-free",
        "blood sugar balanced", "anti-inflammatory",
    ],
    # ---- Indian ----
    "Chicken Tikka Masala": [
        "main course", "dinner", "high-protein",
        "meal prep",
    ],
    "Dal Tadka": [
        "main course", "dinner", "vegetarian", "vegan", "gluten-free",
        "anti-inflammatory", "meal prep",
    ],
    "Aloo Gobi": [
        "side dish", "main course", "vegetarian", "vegan", "gluten-free",
        "anti-inflammatory", "blood sugar balanced", "meal prep",
    ],
    # ---- Italian ----
    "Spaghetti Carbonara": [
        "main course", "dinner", "quick",
        "pasta soup",
    ],
    "Aglio e Olio": [
        "main course", "dinner", "vegetarian", "quick",
        "pasta soup",
    ],
    "Margherita Pizza": [
        "main course", "dinner", "vegetarian",
    ],
    # ---- American / Western ----
    "Sheet-Pan Chicken with Vegetables": [
        "main course", "dinner", "gluten-free", "high-protein",
        "meal prep", "blood sugar balanced",
    ],
    "Classic Cheeseburger": [
        "main course", "lunch", "dinner", "high-protein",
    ],
    "Classic Chocolate Chip Cookies": [
        "dessert", "snack", "vegetarian",
    ],
    # ---- Mexican ----
    "Chicken Tinga Tacos": [
        "main course", "dinner", "high-protein",
        "swicy", "meal prep",
    ],
    "Guacamole": [
        "appetizer", "snack", "vegetarian", "vegan", "gluten-free",
        "dairy-free", "quick",
        "blood sugar balanced", "anti-inflammatory",
    ],
    "Carne Asada": [
        "main course", "dinner", "high-protein", "low-carb", "gluten-free",
        "meal prep", "blood sugar balanced",
    ],
    # ---- French ----
    "Coq au Vin": [
        "main course", "dinner",
        "meal prep",
    ],
    "Ratatouille": [
        "main course", "side dish", "dinner", "vegetarian", "vegan",
        "gluten-free", "dairy-free",
        "anti-inflammatory", "blood sugar balanced", "meal prep",
    ],
    "Quiche Lorraine": [
        "breakfast", "lunch", "main course",
    ],
    # ---- Lebanese ----
    "Hummus": [
        "appetizer", "snack", "vegetarian", "vegan", "gluten-free",
        "dairy-free", "blood sugar balanced", "anti-inflammatory",
        "meal prep",
    ],
    "Tabbouleh": [
        "salad", "side dish", "appetizer", "vegetarian", "vegan",
        "dairy-free", "anti-inflammatory", "meal prep",
    ],
    "Kibbeh bil Sanieh": [
        "main course", "dinner", "high-protein",
        "meal prep",
    ],
    # ---- Turkish ----
    "Adana Kebab": [
        "main course", "dinner", "high-protein", "gluten-free",
        "blood sugar balanced", "swicy",
    ],
    "Lahmacun": [
        "main course", "lunch", "dinner",
    ],
    "Baklava": [
        "dessert", "snack", "vegetarian", "meal prep",
    ],
    # ---- Moroccan ----
    "Chicken Tagine with Preserved Lemon and Olives": [
        "main course", "dinner", "high-protein", "gluten-free",
        "dairy-free", "meal prep",
    ],
    "Moroccan Lamb Couscous": [
        "main course", "dinner", "high-protein", "meal prep",
    ],
    "Harira": [
        "soup", "main course", "dairy-free",
        "pasta soup", "anti-inflammatory", "meal prep",
    ],
    # ---- Ethiopian ----
    "Doro Wat": [
        "main course", "dinner", "high-protein", "gluten-free",
        "swicy", "meal prep",
    ],
    "Misir Wat": [
        "main course", "dinner", "vegetarian", "vegan", "gluten-free",
        "dairy-free", "anti-inflammatory", "swicy", "meal prep",
    ],
    "Injera": [
        "side dish", "vegetarian", "vegan", "gluten-free", "dairy-free",
    ],
    # ---- Filipino ----
    "Chicken Adobo": [
        "main course", "dinner", "high-protein", "dairy-free",
        "meal prep",
    ],
    "Sinigang na Hipon": [
        "soup", "main course", "lunch", "dinner", "gluten-free",
        "dairy-free", "pasta soup", "anti-inflammatory",
    ],
    "Lumpiang Shanghai": [
        "appetizer", "snack", "dinner",
    ],
    # ---- Pakistani ----
    "Chicken Karahi": [
        "main course", "dinner", "high-protein", "gluten-free",
        "swicy", "quick",
    ],
    "Chicken Biryani": [
        "main course", "dinner", "high-protein", "meal prep",
    ],
    "Nihari": [
        "main course", "dinner", "high-protein", "gluten-free",
        "swicy", "meal prep",
    ],
    # ---- Sri Lankan ----
    "Sri Lankan Chicken Curry": [
        "main course", "dinner", "high-protein", "gluten-free",
        "dairy-free", "swicy", "meal prep",
    ],
    "Egg Hoppers": [
        "breakfast", "vegetarian", "gluten-free", "dairy-free",
    ],
    "Sri Lankan Dhal Curry": [
        "main course", "side dish", "vegetarian", "vegan", "gluten-free",
        "dairy-free", "anti-inflammatory", "meal prep",
    ],
    # ---- Cambodian ----
    "Fish Amok": [
        "main course", "dinner", "high-protein", "gluten-free",
        "dairy-free",
    ],
    "Lok Lak": [
        "main course", "dinner", "high-protein", "gluten-free",
        "dairy-free", "quick",
    ],
    "Kuy Teav": [
        "soup", "breakfast", "main course", "lunch", "dairy-free",
        "pasta soup",
    ],
    # ---- Greek ----
    "Pork Souvlaki": [
        "main course", "dinner", "high-protein", "blood sugar balanced",
    ],
    "Moussaka": [
        "main course", "dinner", "high-protein", "meal prep",
    ],
    "Greek Salad": [
        "salad", "side dish", "appetizer", "vegetarian", "gluten-free",
        "anti-inflammatory", "blood sugar balanced", "quick",
    ],
    # ---- Spanish ----
    "Paella Valenciana": [
        "main course", "dinner", "gluten-free", "high-protein",
        "meal prep",
    ],
    "Tortilla Española": [
        "main course", "lunch", "vegetarian", "gluten-free",
        "meal prep",
    ],
    "Patatas Bravas": [
        "appetizer", "snack", "side dish", "vegetarian", "vegan",
        "gluten-free", "dairy-free", "swicy",
    ],
    # ---- Malaysian ----
    "Nasi Lemak": [
        "breakfast", "main course", "dairy-free", "swicy",
    ],
    "Char Kway Teow": [
        "main course", "dinner", "lunch", "dairy-free",
        "quick",
    ],
    "Curry Laksa": [
        "soup", "main course", "dinner", "dairy-free",
        "pasta soup", "swicy",
    ],
    # ---- German ----
    "Wiener Schnitzel": [
        "main course", "dinner", "high-protein",
    ],
    "Sauerbraten": [
        "main course", "dinner", "high-protein", "meal prep",
    ],
    "Kartoffelsalat": [
        "salad", "side dish", "make-ahead",
    ],
    # ---- Indonesian ----
    "Nasi Goreng": [
        "main course", "dinner", "lunch", "high-protein",
        "dairy-free", "swicy", "quick",
    ],
    "Beef Rendang": [
        "main course", "dinner", "high-protein", "gluten-free",
        "dairy-free", "swicy", "meal prep",
    ],
    "Gado-Gado": [
        "salad", "main course", "lunch", "vegetarian", "gluten-free",
        "dairy-free", "anti-inflammatory", "blood sugar balanced",
    ],
    # ---- Brazilian ----
    "Feijoada": [
        "main course", "dinner", "high-protein", "gluten-free",
        "dairy-free", "meal prep",
    ],
    "Moqueca de Peixe": [
        "main course", "dinner", "high-protein", "gluten-free",
        "dairy-free", "anti-inflammatory",
    ],
    "Pão de Queijo": [
        "snack", "breakfast", "vegetarian", "gluten-free",
    ],
    # ---- Peruvian ----
    "Lomo Saltado": [
        "main course", "dinner", "high-protein", "dairy-free",
        "quick",
    ],
    "Ceviche": [
        "appetizer", "main course", "lunch", "high-protein",
        "gluten-free", "dairy-free", "anti-inflammatory",
        "blood sugar balanced", "swicy",
    ],
    "Ají de Gallina": [
        "main course", "dinner", "high-protein", "meal prep",
    ],
    # ---- Caribbean ----
    "Jamaican Jerk Chicken": [
        "main course", "dinner", "high-protein", "gluten-free",
        "dairy-free", "swicy", "meal prep",
    ],
    "Rice and Peas": [
        "side dish", "vegetarian", "vegan", "gluten-free",
        "dairy-free", "meal prep",
    ],
    "Ackee and Saltfish": [
        "breakfast", "main course", "high-protein", "gluten-free",
        "dairy-free",
    ],
    # ---- Taiwanese ----
    "Taiwanese Beef Noodle Soup": [
        "soup", "main course", "dinner", "lunch", "high-protein",
        "dairy-free", "pasta soup", "swicy",
    ],
    "Three-Cup Chicken": [
        "main course", "dinner", "high-protein", "dairy-free",
        "quick",
    ],
    "Lu Rou Fan": [
        "main course", "dinner", "lunch", "dairy-free",
        "meal prep",
    ],
    # ---- Portuguese ----
    "Bacalhau à Brás": [
        "main course", "dinner", "high-protein",
    ],
    "Caldo Verde": [
        "soup", "main course", "lunch",
        "pasta soup", "anti-inflammatory",
    ],
    "Pastel de Nata": [
        "dessert", "snack", "vegetarian", "make-ahead",
    ],
    # ---- British ----
    "Fish and Chips": [
        "main course", "dinner", "high-protein",
    ],
    "Shepherd's Pie": [
        "main course", "dinner", "high-protein", "meal prep",
    ],
    "Full English Breakfast": [
        "breakfast", "high-protein",
    ],
}


# Per-title difficulty overrides for recipes where the auto-rule in
# `app.models.difficulty.compute_difficulty()` gives a counterintuitive
# answer. The rule covers ~90% of the curated catalog correctly; this
# dict patches the remainder so the chip matches what an experienced
# home cook would expect.
#
# Override criteria (one of):
#   * The user-facing rules list the dish as an exemplar for a bucket
#     the auto-rule doesn't reach (e.g. Baklava — "highly technical
#     pastry" is HARD, but Baklava's clock at 80 min sits in MEDIUM).
#   * The auto-rule misses a clear EASY due to a tiny step-count
#     overage (e.g. Patatas Bravas at 50 min — most of the time is
#     unattended oven, not active work).
#
# Keep this list tight. Every entry here is a SILENT departure from
# the documented rules, so the burden of proof is high. If the rules
# need to be relaxed in general, update `compute_difficulty()` instead
# of adding rows here.
_DIFFICULTY_OVERRIDES_BY_TITLE: dict[str, Difficulty] = {
    # Pastry-technique exception. The auto-rule's time + step axis
    # doesn't see "filo layering + butter precision", which is what
    # makes Baklava HARD in practice.
    "Baklava": Difficulty.HARD,
    # 50-minute clock is mostly unattended oven roasting time; the
    # active hands-on portion is < 20 min and the technique is
    # forgiving. Listed as EASY in the product rules.
    "Patatas Bravas": Difficulty.EASY,
}


def _resolve_difficulty(spec: Mapping[str, Any]) -> Difficulty:
    """Pick the difficulty for a curated spec.

    Priority order (highest first):
      1. Explicit `spec["difficulty"]` set in `curated_data.py`. Hand
         authored, trusted as-is — used for the rare recipe where
         even the override table isn't right.
      2. `_DIFFICULTY_OVERRIDES_BY_TITLE` lookup. Per-title patches
         for the auto-rule's edge cases (see dict comment above).
      3. `compute_difficulty()` — the rule-based fallback, applied
         to the spec's prep + cook + step count.

    Always returns a `Difficulty` member; never None. The seed and
    backfill paths can write the result directly to the column.
    """
    pinned = spec.get("difficulty")
    if pinned is not None:
        # Coerce string -> enum, accepting any case (a future seed
        # author writing `"difficulty": "Hard"` is doing something
        # reasonable; raising "value 'Hard' is not a valid Difficulty"
        # from inside StrEnum is unhelpful in context). The Difficulty
        # ctor accepts lowercase wire values; we lowercase first and
        # then re-raise with the offending recipe title so a typo
        # surfaces with enough context to fix.
        normalized = pinned.lower() if isinstance(pinned, str) else pinned
        try:
            return Difficulty(normalized)
        except ValueError as exc:
            raise ValueError(
                f"unknown difficulty {pinned!r} on recipe "
                f"{spec.get('title')!r}; valid values are "
                f"{[d.value for d in Difficulty]}"
            ) from exc
    override = _DIFFICULTY_OVERRIDES_BY_TITLE.get(spec["title"])
    if override is not None:
        return override
    return compute_difficulty(
        prep_minutes=spec["prep"],
        cook_minutes=spec["cook"],
        step_count=len(spec["steps"]),
    )


def _merge_translations(
    existing: dict | None, fresh: dict
) -> dict:
    """Per-locale shallow merge: for each locale, fresh keys win where
    they're set, otherwise the existing value is preserved. Used by
    the seed-time sync so spec-supplied title/description updates
    land while LLM-backfilled ingredients/steps arrays (written by
    `backfill_recipe_translations.py`) survive a re-seed.

    The merge is per-FIELD, not per-locale: writing only `title` for
    a locale doesn't blank that locale's `description` or
    `ingredients` array. This matches the contract of
    `backfill_recipe_translations._merge_translation_bundle` so the
    two writers compose cleanly.
    """
    if not isinstance(existing, dict):
        return dict(fresh)
    out: dict[str, dict[str, Any]] = {}
    for code in set(existing.keys()) | set(fresh.keys()):
        cur_raw = existing.get(code)
        new_raw = fresh.get(code)
        cur: dict[str, Any] = cur_raw if isinstance(cur_raw, dict) else {}
        new: dict[str, Any] = new_raw if isinstance(new_raw, dict) else {}
        merged: dict[str, Any] = {**cur, **new}
        if merged:
            out[code] = merged
    return out


def _augmented_tags(spec_title: str, base_tags: list[str]) -> list[str]:
    """Return the union of `base_tags` (from the curated spec) and the
    course/dietary tags from `_EXTRA_TAGS_BY_TITLE`, deduplicated, with
    original ordering preserved as much as possible. Returns a fresh list
    so callers can mutate it freely.
    """
    extra = _EXTRA_TAGS_BY_TITLE.get(spec_title, [])
    seen: set[str] = set()
    out: list[str] = []
    for t in [*base_tags, *extra]:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


async def main(*, quick: bool = False) -> None:
    # ------------------------------------------------------------------
    # Phase 1 (no DB): figure out which titles need resolution and which
    # don't, without holding a DB connection. We open a short read
    # session, snapshot the relevant fields into plain Python, then close
    # it. The actual `_resolve_image_url()` work can take minutes per
    # batch (network round-trips to LoremFlickr + HEAD-checks to Flickr)
    # and was previously timing the DB connection out with
    # `ConnectionDoesNotExistError`.
    # ------------------------------------------------------------------
    async with AsyncSessionLocal() as db:
        existing_rows = (
            await db.scalars(
                select(SpiceRoute).where(SpiceRoute.is_premium.is_(True))
            )
        ).all()
        existing_snapshot = {
            r.title: (r.id, r.image_path, r.calories_per_serving)
            for r in existing_rows
        }
    # Note: this snapshot is used ONLY by Phase 1 image-resolution
    # decisions (skip the slow Flickr HEAD when we already have an
    # image cached). The Phase 2 dedup check uses a fresh DB read
    # so it stays correct in the face of parallel writes during
    # the Phase 1 network loop. See the comment at the dedup
    # branch below for the full rationale.

    # Resolve every URL we'll need (new rows + existing rows that need
    # re-freezing) without touching the DB.
    #
    # Policy:
    #   - Hand-curated Wikimedia URLs in `spec["image"]` are the source
    #     of truth - they ALWAYS win over whatever's currently in DB
    #     (which might be a low-quality auto-resolved Flickr photo from
    #     a previous run, a dead live.staticflickr.com URL, an old
    #     picsum.photos URL, or a rotating loremflickr.com search URL).
    #   - Other URL types (LoremFlickr search URLs in spec) still go
    #     through `_resolve_image_url` to be frozen.
    resolved_by_title: dict[str, str] = {}
    for spec in CURATED:
        title = spec["title"]
        spec_image = spec["image"]
        if "upload.wikimedia.org" in spec_image:
            # Hand-curated, permanent. Use as-is, always.
            resolved_by_title[title] = spec_image
            continue
        if title in existing_snapshot:
            _, current_image, _ = existing_snapshot[title]
            if quick and current_image and not is_broken_image_url(current_image):
                # Deploy-hook path: trust whatever's already in the DB
                # so we don't burn 10+ seconds per recipe HEAD-checking
                # Flickr on every release. Use the periodic full run
                # (without --quick) to freshen dead image URLs.
                resolved_by_title[title] = current_image
                continue
            needs_freeze = (
                not current_image
                or "picsum.photos" in current_image
                or "loremflickr.com" in current_image
                or (
                    "live.staticflickr.com" in current_image
                    and not _is_url_alive(current_image)
                )
            )
            if needs_freeze:
                resolved_by_title[title] = _resolve_image_url(spec_image)
            elif current_image:
                resolved_by_title[title] = current_image
        else:
            # New rows still go through the full resolver — we'd rather
            # take the hit once and ship a verified image than gamble on
            # the spec URL being alive.
            resolved_by_title[title] = (
                spec_image if quick else _resolve_image_url(spec_image)
            )

    # ------------------------------------------------------------------
    # Phase 2 (DB): open a fresh, short-lived session and write all
    # changes in one go. This holds the connection for seconds, not
    # minutes, so it never trips the idle timeout.
    # ------------------------------------------------------------------
    async with AsyncSessionLocal() as db:
        # Compute the full universe of tag names we'll need (curated tags
        # PLUS the augmented course/dietary tags) so every Tag row exists
        # before we attach them to recipes.
        all_tag_names = sorted({
            n
            for r in CURATED
            for n in _augmented_tags(r["title"], list(r["tags"]))
        })
        if all_tag_names:
            tag_rows = (
                await db.scalars(select(Tag).where(Tag.name.in_(all_tag_names)))
            ).all()
            tag_by_name = {t.name: t for t in tag_rows}
            for n in all_tag_names:
                if n not in tag_by_name:
                    new_tag = Tag(name=n)
                    db.add(new_tag)
                    tag_by_name[n] = new_tag
            await db.flush()
        else:
            tag_by_name = {}

        # Re-load the rows we'll be mutating into THIS session so they're
        # attached and changes flush on commit.
        existing_rows = (
            await db.scalars(
                select(SpiceRoute).where(SpiceRoute.is_premium.is_(True))
            )
        ).all()
        existing_by_title = {r.title: r for r in existing_rows}

        added = 0
        skipped = 0
        backfilled = 0
        relinked = 0
        retagged = 0
        translations_synced = 0
        difficulty_synced = 0
        for spec in CURATED:
            target_tag_names = _augmented_tags(spec["title"], list(spec["tags"]))
            target_difficulty = _resolve_difficulty(spec)
            # IMPORTANT: dedup against the Phase 2 fresh read
            # (`existing_by_title`), NOT the Phase 1 snapshot
            # (`existing`). The Phase 1 set is captured BEFORE the
            # slow LoremFlickr resolution loop, so anything written
            # by a parallel process (or a previous deploy that
            # raced this one on a restart) lands in Phase 2's read
            # but not in Phase 1's snapshot — and using the stale
            # set would let us INSERT a duplicate row (titles are
            # only `index=True`, not `unique=True`, so the DB
            # wouldn't catch it for us). On Render free-tier this
            # is unlikely in practice (single worker), but it costs
            # nothing to be correct here.
            if spec["title"] in existing_by_title:
                skipped += 1
                row = existing_by_title[spec["title"]]
                if row.calories_per_serving is None:
                    row.calories_per_serving = _kcal_for_spec(spec)
                    backfilled += 1
                target_image = resolved_by_title[spec["title"]]
                if target_image and row.image_path != target_image:
                    row.image_path = target_image
                    relinked += 1
                # Reconcile tag set: add any course/dietary tags that
                # weren't present yet (e.g. on rows seeded before we
                # introduced `_EXTRA_TAGS_BY_TITLE`). Existing curated
                # tags are preserved so we never silently drop data.
                existing_tag_names = {t.name for t in row.tags}
                missing = [n for n in target_tag_names if n not in existing_tag_names]
                if missing:
                    for n in missing:
                        row.tags.append(tag_by_name[n])
                    retagged += 1
                # Backfill translations onto already-seeded rows whenever
                # the curated spec gains (or updates) a `translations`
                # entry. MERGE rather than replace per-locale: the spec
                # carries hand-polished title + description copy, while
                # the DB may carry LLM-backfilled ingredients + steps
                # arrays (written by `scripts/backfill_recipe_translations`).
                # A naive `row.translations = spec_translations` would
                # wipe those arrays on the next re-seed and the live
                # site would silently drop back to source-language
                # steps for every curated recipe.
                spec_translations = strip_stub_bundles(
                    spec.get("translations"),
                    source_title=spec["title"],
                    source_description=spec.get("description"),
                )
                if spec_translations:
                    merged = _merge_translations(
                        row.translations, spec_translations
                    )
                    if merged != row.translations:
                        row.translations = merged
                        translations_synced += 1
                # Reconcile difficulty. The first deploy after migration
                # 0012 lands every existing curated row at the server
                # default (`medium`); this branch over-writes that
                # placeholder with the spec-derived value. Re-runs are
                # no-ops once the row matches.
                if row.difficulty != target_difficulty:
                    row.difficulty = target_difficulty
                    difficulty_synced += 1
                continue
            resolved_image = resolved_by_title[spec["title"]]
            sr = SpiceRoute(
                user_id=None,
                title=spec["title"],
                description=spec["description"],
                prep_minutes=spec["prep"],
                cook_minutes=spec["cook"],
                servings=spec["servings"],
                is_public=True,
                is_premium=True,
                cuisine=Cuisine(spec["cuisine"]),
                language=spec["language"],
                spice_level=spec["spice_level"],
                translations=strip_stub_bundles(
                    spec.get("translations"),
                    source_title=spec["title"],
                    source_description=spec.get("description"),
                ),
                calories_per_serving=_kcal_for_spec(spec),
                difficulty=target_difficulty,
                image_path=resolved_image,
                ingredients=[
                    Ingredient(
                        quantity=(
                            Decimal(str(ing["quantity"]))
                            if "quantity" in ing
                            else None
                        ),
                        unit=ing.get("unit"),
                        name=ing.get("name", ""),
                        sort_order=i,
                    )
                    for i, ing in enumerate(spec["ingredients"])
                ],
                steps=[
                    Step(sort_order=i, body=body)
                    for i, body in enumerate(spec["steps"])
                ],
                tags=[tag_by_name[name] for name in target_tag_names],
            )
            db.add(sr)
            added += 1

        await db.commit()
        print(
            f"Seeded {added} curated recipes "
            f"(skipped {skipped} duplicates, backfilled calories on "
            f"{backfilled}, re-linked images on {relinked}, "
            f"added course/dietary tags to {retagged}, synced "
            f"translations on {translations_synced}, synced "
            f"difficulty on {difficulty_synced})."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quick",
        action="store_true",
        help=(
            "Skip the network-bound image-resolution step for recipes "
            "that already exist in the DB. Use this from release.sh on "
            "every deploy; use a periodic non-quick run to refresh dead "
            "Flickr URLs."
        ),
    )
    args = parser.parse_args()
    asyncio.run(main(quick=args.quick))
