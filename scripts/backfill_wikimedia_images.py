"""Backfill `_WIKIMEDIA_IMAGE_BY_SLUG` for recipes still on generic Unsplash.

Looks up each missing slug via Wikipedia / Commons, prints Python entries
ready to paste into `scripts/curated_data.py`.

Usage:
    uv run python -m scripts.backfill_wikimedia_images
    uv run python -m scripts.backfill_wikimedia_images --apply
"""
from __future__ import annotations

import argparse
import logging
import sys

from scripts.curated_data import _WIKIMEDIA_IMAGE_BY_SLUG, CURATED
from scripts.fix_recipe_images import _slug_from_title
from scripts.recipe_images import stable_food_image_url
from scripts.wikimedia_lookup import lookup_wikimedia_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("wikimedia_backfill")


def _missing_slugs() -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for spec in CURATED:
        slug = _slug_from_title(spec["title"])
        if slug in seen:
            continue
        image = spec["image"]
        if "wikimedia.org" in image.lower():
            seen.add(slug)
            continue
        if image == stable_food_image_url(slug) or (
            "unsplash.com" in image and slug not in _WIKIMEDIA_IMAGE_BY_SLUG
        ):
            seen.add(slug)
            out.append((slug, spec["title"], spec["cuisine"]))
    return out


def _apply_to_curated_data(entries: dict[str, str]) -> None:
    from pathlib import Path

    path = Path(__file__).resolve().parent / "curated_data.py"
    src = path.read_text(encoding="utf-8")
    marker = "}\n\n\ndef _img(slug: str)"
    if marker not in src:
        raise RuntimeError("Could not find insertion point in curated_data.py")
    block = "\n".join(
        f'    "{slug}": "{url}",' for slug, url in sorted(entries.items())
    )
    src = src.replace(
        marker,
        "\n".join(
            [
                "    # ---- auto backfill (audit_culinary_images) ----",
                block,
                marker,
            ]
        ),
        1,
    )
    path.write_text(src, encoding="utf-8")
    log.info("appended %d entries to curated_data.py", len(entries))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--apply",
        action="store_true",
        help="Append found URLs into curated_data.py",
    )
    args = p.parse_args(argv)

    missing = _missing_slugs()
    log.info("slugs to resolve: %d", len(missing))

    found: dict[str, str] = {}
    failed: list[str] = []
    for slug, title, cuisine in missing:
        url, source = lookup_wikimedia_image(title, slug)
        if url:
            found[slug] = url
            log.info("OK %-28s %s", slug, source)
        else:
            failed.append(f"{slug}\t{title}\t{cuisine}")
            log.warning("MISS %-28s %s", slug, title)

    print("\n# Paste into _WIKIMEDIA_IMAGE_BY_SLUG:")
    for slug, url in sorted(found.items()):
        print(f'    "{slug}": "{url}",')

    if failed:
        print("\n# Still unresolved:", file=sys.stderr)
        for line in failed:
            print(line, file=sys.stderr)

    if args.apply and found:
        _apply_to_curated_data(found)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
