"""Seed the database with the 27 curated `is_premium=True` recipes.

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

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.cuisine import Cuisine
from app.models.spice_route import Ingredient, SpiceRoute, Step
from app.models.tag import Tag
from scripts.curated_data import CURATED

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
    return url

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
}

# Per-recipe extra tags layered on top of `spec["tags"]` to power the
# Explore filter dropdowns. Frontend `Course` and `Dietary` enums look these
# up by name (case-insensitive) so the strings here must match the
# `tagName` field on those Dart enums exactly.
#
# Tag taxonomy mirrors the v2 filter design (see filter_bar.dart):
#   Courses : breakfast | lunch | appetizer | side dish | dessert | snack
#             | drinks
#   Dietary : vegan | vegetarian | meal prep | quick | pasta soup
#             | blood sugar balanced | swicy | anti-inflammatory
#
# Legacy tags (main course, dinner, soup, salad, gluten-free, dairy-free,
# nut-free, high-protein, low-carb) are kept on the recipes for backward
# compatibility and visible tag display, but are no longer surfaced as
# filter dropdown options.
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
}


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
    existing = set(existing_snapshot.keys())

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
            if quick and current_image:
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
            else:
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
        for spec in CURATED:
            target_tag_names = _augmented_tags(spec["title"], list(spec["tags"]))
            if spec["title"] in existing:
                skipped += 1
                row = existing_by_title[spec["title"]]
                if row.calories_per_serving is None:
                    row.calories_per_serving = spec.get(
                        "calories",
                        _CUISINE_KCAL_FALLBACK.get(spec["cuisine"]),
                    )
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
                calories_per_serving=spec.get(
                    "calories", _CUISINE_KCAL_FALLBACK.get(spec["cuisine"])
                ),
                image_path=resolved_image,
                ingredients=[
                    Ingredient(
                        quantity=(
                            Decimal(str(ing["quantity"]))
                            if "quantity" in ing
                            else None
                        ),
                        unit=ing.get("unit"),
                        name=ing["name"],
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
            f"added course/dietary tags to {retagged})."
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
