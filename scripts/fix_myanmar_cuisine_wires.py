"""Point Myanmar expansion recipes at their regional cuisine wires in Postgres.

The v7 generator briefly stored every regional dish under `burmese`.
Re-run after regenerating `cuisine_expansion_v7_myanmar.py`:

    uv run python -m scripts.fix_myanmar_cuisine_wires
    uv run python -m scripts.fix_myanmar_cuisine_wires --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.cuisine import Cuisine
from app.models.spice_route import SpiceRoute
from scripts.generate_myanmar_expansion import _DISHES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fix_myanmar_cuisines")

_TITLE_TO_WIRE = {title: wire for wire, _slug, title, *_rest in _DISHES}


async def _run(*, dry_run: bool) -> int:
    async with AsyncSessionLocal() as db:
        rows = (await db.scalars(select(SpiceRoute))).all()
        changed = 0
        for row in rows:
            wire = _TITLE_TO_WIRE.get(row.title)
            if wire is None:
                continue
            target = Cuisine(wire)
            if row.cuisine == target:
                continue
            log.info("%s: %s -> %s", row.title, row.cuisine, wire)
            if not dry_run:
                row.cuisine = target
                changed += 1
        if dry_run:
            log.info("dry-run complete")
            return 0
        await db.commit()
        log.info("updated %d row(s)", changed)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
