"""Audit recipe image URLs in Postgres — dead links and duplicates.

Usage:
    uv run python -m scripts.audit_recipe_images
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.spice_route import SpiceRoute
from scripts.recipe_images import image_url_is_alive, is_broken_image_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("audit_images")


async def _run() -> int:
    async with AsyncSessionLocal() as db:
        rows = (await db.scalars(select(SpiceRoute))).all()

    missing = [r.title for r in rows if not r.image_path]
    dead: list[tuple[str, str]] = []
    by_url: dict[str, list[str]] = defaultdict(list)

    for row in rows:
        url = row.image_path
        if not url:
            continue
        by_url[url].append(row.title)
        if is_broken_image_url(url) or not image_url_is_alive(url):
            dead.append((row.title, url[:90]))
        # Wikimedia rate-limits burst checks — pace requests.
        if "wikimedia.org" in url:
            await asyncio.sleep(0.2)

    dups = {url: titles for url, titles in by_url.items() if len(titles) > 1}

    log.info("recipes=%d missing=%d dead=%d duplicate_groups=%d",
             len(rows), len(missing), len(dead), len(dups))

    for title, url in dead[:20]:
        log.warning("DEAD %s -> %s", title, url)
    if len(dead) > 20:
        log.warning("... and %d more dead URLs", len(dead) - 20)

    for url, titles in sorted(dups.items(), key=lambda x: -len(x[1]))[:15]:
        log.warning("DUP %dx %s", len(titles), url[:70])
        for title in titles[:6]:
            log.warning("    - %s", title)

    if missing or dead or dups:
        return 1
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
