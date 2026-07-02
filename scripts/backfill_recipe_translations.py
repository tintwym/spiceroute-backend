"""Backfill `spice_routes.translations` JSONB so every row carries
per-locale ingredients + steps in addition to title + description.

WHY THIS EXISTS
---------------
The save-time translation hook (`app/services/ai/llm.py::
translate_recipe_content`) was extended to translate ingredients and
steps alongside title + description. Recipes saved AFTER that change
get the full bundle automatically. Recipes that already existed in
the DB (every curated row + any user/AI recipes from before the
extension) still have the OLD shape — title + description per locale
but no ingredients / steps arrays — so a non-English visitor sees:

    HƯỚNG DẪN NẤU                             ← UI (translated)
      1. Blanch beef bones and brisket for…   ← step body in source lang
      2. Char onion and ginger…               ← step body in source lang
      …

This script LLM-translates every missing row's ingredients + steps
in batch and merges the result into the existing `translations`
JSONB (preserving any human-polished title / description fields).

USAGE
-----
    # Hit every row in the DB that's missing ingredient OR step
    # translations for any of the 4 non-source locales.
    uv run python -m scripts.backfill_recipe_translations

    # Smoke-test against 3 rows first.
    uv run python -m scripts.backfill_recipe_translations --limit 3

    # Dry-run: print what would change, don't write.
    uv run python -m scripts.backfill_recipe_translations --dry-run

    # Translate ONE specific recipe by ID (useful after a manual edit).
    uv run python -m scripts.backfill_recipe_translations \
        --id 0123abcd-…

DESIGN NOTES
------------
1. **Merge, don't replace.** When we re-write `translations`, we merge
   the new ingredient/step arrays into the existing per-locale bundle
   instead of overwriting the whole locale. This preserves any
   hand-polished title / description that already lives in the row
   (e.g. the 9 curated recipes the i18n audit corrected by hand).

2. **Idempotent.** A row is skipped if EVERY non-source locale already
   carries non-empty `ingredients` AND `steps` arrays of the correct
   length. Re-running after a partial network failure picks up only
   the rows that didn't finish.

3. **Per-row rate pacing.** The configured LLM provider (Groq by
   default) caps free-tier accounts at ~30 RPM. We pace at the same
   ceiling so a single backfill run doesn't burn the quota that the
   live save-time hook also depends on.

4. **Failure isolation.** A single row's LLM error is logged and
   skipped — the next row continues. We'd rather ship 92/93 translated
   rows and have one to re-try than abort the whole run on a
   transient timeout.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.cuisine import Cuisine
from app.models.cuisine_catalog import MYANMAR_REGIONAL_WIRES
from app.models.spice_route import SpiceRoute
from app.services.ai.llm import translate_recipe_content
from app.services.recipe_translations import row_needs_backfill
from app.services.spice_routes import format_ingredient_line
from scripts.translation_utils import merge_translation_bundle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backfill")
# Quiet the noisy httpx INFO lines (`HTTP Request: POST … 200 OK`) — one
# per LLM call, drowns out the actual progress output.
logging.getLogger("httpx").setLevel(logging.WARNING)

# Per row we now issue 4 parallel LLM calls (one per target locale).
# Free-tier Groq's `llama-3.1-8b-instant` is capped at 30 RPM AND 6000
# TPM. Each per-locale call is ~1500-2000 output tokens for a typical
# 10-ingredient / 7-step recipe, so 4 parallel calls per row ≈ 6-8k
# tokens — exactly the per-minute budget. Pacing at 3 RPM means at
# most 12 requests / minute and ~24k tokens / minute INTENT, but
# Groq throttles to 6 k/min so the per-locale retry kicks in to
# spread it out. Lowering further (e.g. 1 RPM) only stretches the
# wall clock — it doesn't reduce the per-minute token volume.
# One row ≈ four sequential per-locale LLM calls; 1 RPM keeps us under
# Groq free-tier TPM while still making steady progress.
DEFAULT_RPM = 1.0


def _row_needs_backfill(row: SpiceRoute) -> bool:
    return row_needs_backfill(row)


@dataclass(frozen=True)
class _RowSnapshot:
    """Plain-data view of a row for the outer loop.

    ORM instances go stale after `session.commit()` / `session.rollback()`
  — accessing `row.title` on the next iteration after a rollback raises
    `MissingGreenlet` because SQLAlchemy tries a sync lazy-load inside
    an async session. Snapshotting upfront (or re-fetching by id each
    iteration) keeps the loop resilient to per-row failures."""
    id: UUID
    title: str
    language: str
    ingredient_count: int
    step_count: int


def _snapshot_row(row: SpiceRoute) -> _RowSnapshot:
    return _RowSnapshot(
        id=row.id,
        title=row.title,
        language=row.language,
        ingredient_count=len(row.ingredients),
        step_count=len(row.steps),
    )


async def _fetch_row_by_id(session, row_id: UUID) -> SpiceRoute | None:
    stmt = (
        select(SpiceRoute)
        .options(
            selectinload(SpiceRoute.ingredients),
            selectinload(SpiceRoute.steps),
        )
        .where(SpiceRoute.id == row_id)
    )
    return (await session.scalars(stmt)).first()


async def _fetch_rows(
    session, *, only_id: UUID | None, cuisine_wires: tuple[str, ...] | None
) -> list[SpiceRoute]:
    """Load every row + its ingredients + steps with a single query."""
    stmt = select(SpiceRoute).options(
        selectinload(SpiceRoute.ingredients),
        selectinload(SpiceRoute.steps),
    )
    if only_id is not None:
        stmt = stmt.where(SpiceRoute.id == only_id)
    elif cuisine_wires:
        stmt = stmt.where(
            SpiceRoute.cuisine.in_([Cuisine(w) for w in cuisine_wires])
        )
    # Newest rows first — expansion drops (e.g. Myanmar v7) land at the
    # tail of ASC order and would otherwise wait hours behind legacy rows.
    stmt = stmt.order_by(SpiceRoute.created_at.desc(), SpiceRoute.id)
    return list((await session.scalars(stmt)).all())


async def _backfill_one(
    session, row: SpiceRoute
) -> tuple[bool, str]:
    """Translate one row, merge the result, commit. Returns
    (changed, message) for caller logging."""
    ingredients = [
        format_ingredient_line(quantity=i.quantity, unit=i.unit, name=i.name)
        for i in row.ingredients
    ]
    steps = [s.body for s in row.steps]
    fresh = await translate_recipe_content(
        title=row.title,
        description=row.description,
        source_language=row.language,
        ingredients=ingredients,
        steps=steps,
    )
    if not fresh:
        return False, "LLM returned nothing (stub mode or transient error)"

    merged = merge_translation_bundle(
        row.translations,
        fresh,
        source_title=row.title,
        source_description=row.description,
    )
    if merged == row.translations:
        return False, "no-op (fresh result identical to stored bundle)"

    row.translations = merged
    await session.commit()
    locales = ",".join(sorted(fresh.keys()))
    return True, f"wrote {len(fresh)} locale bundle(s) [{locales}]"


async def _run(
    *,
    dry_run: bool,
    limit: int | None,
    only_id: UUID | None,
    cuisine_wires: tuple[str, ...] | None,
    rpm: float,
) -> int:
    """Main loop. Returns process exit code."""
    min_interval = 60.0 / rpm if rpm > 0 else 0.0
    last_call_at: float | None = None

    async with AsyncSessionLocal() as session:
        rows = await _fetch_rows(
            session, only_id=only_id, cuisine_wires=cuisine_wires
        )
        log.info("Loaded %d row(s) from DB", len(rows))

        pending_rows = [r for r in rows if _row_needs_backfill(r)]
        pending = [_snapshot_row(r) for r in pending_rows]
        log.info("%d row(s) need translation backfill", len(pending))

        if limit is not None:
            pending = pending[:limit]
            log.info("Limit applied: %d row(s) will be processed", len(pending))

        if not pending:
            log.info("Nothing to do — every row already carries a full bundle.")
            return 0

        if dry_run:
            for snap in pending:
                log.info(
                    "[dry-run] would translate %s (%s) — %s ings / %s steps",
                    snap.id,
                    snap.title[:40],
                    snap.ingredient_count,
                    snap.step_count,
                )
            return 0

        changed = 0
        skipped = 0
        for i, snap in enumerate(pending, start=1):
            # Per-minute pacing — honour BEFORE the call so the first
            # two calls don't fire back-to-back and immediately 429.
            if last_call_at is not None and min_interval > 0:
                elapsed = time.monotonic() - last_call_at
                if elapsed < min_interval:
                    wait = min_interval - elapsed
                    if wait > 1.0:
                        log.info("  · pacing — sleeping %.1fs", wait)
                    await asyncio.sleep(wait)

            log.info(
                "[%d/%d] %s (%s, %s ings / %s steps) …",
                i,
                len(pending),
                snap.title[:50],
                snap.language,
                snap.ingredient_count,
                snap.step_count,
            )
            last_call_at = time.monotonic()
            try:
                row = await _fetch_row_by_id(session, snap.id)
                if row is None:
                    log.warning("  ! Skipped: row %s no longer exists", snap.id)
                    skipped += 1
                    continue
                ok, msg = await _backfill_one(session, row)
            except Exception as exc:  # noqa: BLE001 — see comment
                # Don't abort the whole batch on a single transient
                # error (rate limit, malformed JSON, network blip).
                # Rollback the broken transaction so subsequent rows
                # operate on a clean session, then continue. The outer
                # loop uses `_RowSnapshot` (not the stale ORM instance)
                # so we never touch expired attributes here.
                await session.rollback()
                log.warning("  ! Skipped: %r", exc)
                skipped += 1
                continue
            if ok:
                changed += 1
                log.info("  ✓ %s", msg)
            else:
                skipped += 1
                log.info("  · %s", msg)

        log.info(
            "Done. wrote=%d skipped=%d total=%d",
            changed,
            skipped,
            len(pending),
        )
    return 0


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument(
        "--id", dest="only_id", type=UUID, default=None,
        help="Backfill ONE row by primary key.",
    )
    p.add_argument(
        "--rpm", type=float, default=DEFAULT_RPM,
        help=f"Max LLM calls per minute (default {DEFAULT_RPM}).",
    )
    p.add_argument(
        "--cuisine-wires",
        nargs="+",
        default=None,
        help="Only backfill rows whose cuisine wire is in this list "
        "(e.g. burmese yangon shan).",
    )
    p.add_argument(
        "--myanmar",
        action="store_true",
        help="Shorthand for all Myanmar regional wires plus burmese.",
    )
    return p.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    wires: tuple[str, ...] | None = None
    if args.myanmar:
        wires = ("burmese", *MYANMAR_REGIONAL_WIRES)
    elif args.cuisine_wires:
        wires = tuple(args.cuisine_wires)
    return asyncio.run(
        _run(
            dry_run=args.dry_run,
            limit=args.limit,
            only_id=args.only_id,
            cuisine_wires=wires,
            rpm=args.rpm,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
