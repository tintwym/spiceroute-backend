"""Replace broken or duplicate recipe image URLs in Postgres.

Usage:
    uv run python -m scripts.fix_recipe_images
    uv run python -m scripts.fix_recipe_images --dry-run
    uv run python -m scripts.audit_recipe_images
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.spice_route import SpiceRoute
from scripts.curated_data import CURATED
from scripts.generate_myanmar_expansion import _DISHES
from scripts.myanmar_food_images import (
    MYANMAR_WIKIMEDIA_BY_SLUG,
    MYANMAR_WIKIMEDIA_BY_TITLE,
)
from scripts.recipe_images import (
    image_url_is_alive,
    is_broken_image_url,
    stable_food_image_url,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fix_images")

_TITLE_TO_IMAGE = {spec["title"]: spec["image"] for spec in CURATED}
_TITLE_TO_MYANMAR_SLUG = {title: slug for _wire, slug, title, *_rest in _DISHES}


def _myanmar_image_for_title(title: str) -> str | None:
    if title in MYANMAR_WIKIMEDIA_BY_TITLE:
        return MYANMAR_WIKIMEDIA_BY_TITLE[title]
    slug = _TITLE_TO_MYANMAR_SLUG.get(title)
    if slug:
        return MYANMAR_WIKIMEDIA_BY_SLUG.get(slug)
    return None


def _slug_from_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "food"


def _is_wikimedia_url(url: str) -> bool:
    return "upload.wikimedia.org" in url.lower()


def resolve_recipe_image_url(
    title: str,
    *,
    assigned_urls: set[str] | None = None,
) -> str:
    """Pick a live image URL for a recipe title.

    1. Prefer the curated Wikimedia URL when it responds 200. Shared
       Commons photos are allowed (Myanmar regional dishes reuse images).
    2. Otherwise prefer the curated Unsplash URL when alive and not yet
       assigned in this batch.
    3. Fall back to a title-keyed Unsplash pool shot, bumping a suffix
       until the URL is unique within this batch.
    """
    assigned = assigned_urls if assigned_urls is not None else set()

    myanmar = _myanmar_image_for_title(title)
    if (
        myanmar
        and not is_broken_image_url(myanmar)
        and image_url_is_alive(myanmar)
    ):
        return myanmar

    curated = _TITLE_TO_IMAGE.get(title)
    if curated and not is_broken_image_url(curated):
        # Hand-curated Commons URLs are trusted without a live HEAD/GET —
        # Wikimedia rate-limits burst checks during deploy and would push
        # good rows onto the generic Unsplash pool.
        if _is_wikimedia_url(curated) or image_url_is_alive(curated):
            if _is_wikimedia_url(curated) or curated not in assigned:
                return curated

    suffix = 0
    while True:
        key = title if suffix == 0 else f"{title}-{suffix}"
        candidate = stable_food_image_url(key)
        if candidate not in assigned:
            return candidate
        suffix += 1


def _target_image_for_row(
    row: SpiceRoute,
    *,
    assigned_urls: set[str],
) -> str:
    return resolve_recipe_image_url(row.title, assigned_urls=assigned_urls)


async def _run(*, dry_run: bool) -> int:
    async with AsyncSessionLocal() as db:
        rows = sorted(
            (await db.scalars(select(SpiceRoute))).all(),
            key=lambda r: r.title,
        )
        assigned_urls: set[str] = set()
        changed = 0
        for row in rows:
            current = row.image_path
            target = _target_image_for_row(row, assigned_urls=assigned_urls)
            if current == target:
                assigned_urls.add(target)
                continue
            log.info("%s -> %s", row.title[:40], target[:72])
            if not dry_run:
                row.image_path = target
                changed += 1
            assigned_urls.add(target)
        if dry_run:
            log.info("dry-run complete (%d would change)", changed)
            return 0
        await db.commit()
        log.info("updated %d row(s)", changed)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    return asyncio.run(_run(dry_run=args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
