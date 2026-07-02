from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spice_route import Ingredient, Step
from app.models.tag import Tag
from app.schemas.spice_route import IngredientIn, StepIn


async def upsert_tags(db: AsyncSession, names: list[str]) -> list[Tag]:
    """Return Tag rows for each name, creating ones that don't exist yet.

    Concurrency note: `Tag.name` has a UNIQUE constraint, so the naive
    "SELECT then INSERT missing rows" pattern races — two simultaneous
    requests can both miss the SELECT, both INSERT, and the second
    INSERT hits a UniqueViolation that bubbles out as a 500.
    We retry once on `IntegrityError` and re-SELECT, on the assumption
    that a competing transaction won the race and now the row exists.
    """
    if not names:
        return []

    existing = (
        await db.scalars(select(Tag).where(Tag.name.in_(names)))
    ).all()
    by_name = {t.name: t for t in existing}

    missing = [n for n in names if n not in by_name]
    if not missing:
        return [by_name[n] for n in names]

    for n in missing:
        db.add(Tag(name=n))

    try:
        await db.flush()
    except IntegrityError:
        # A competing request committed at least one of the names we
        # were trying to insert. Roll back THIS transaction's failed
        # flush, re-fetch every row by name (winner's INSERTs are now
        # committed and visible), and rebuild the result.
        await db.rollback()
        existing = (
            await db.scalars(select(Tag).where(Tag.name.in_(names)))
        ).all()
        by_name = {t.name: t for t in existing}
        # In the rare case our retry SELECT still misses something
        # (e.g. winning transaction was an update, not an insert) we
        # try once more to insert — if that ALSO races, surface the
        # error rather than loop forever.
        missing = [n for n in names if n not in by_name]
        for n in missing:
            db.add(Tag(name=n))
        if missing:
            await db.flush()
            for t in (
                await db.scalars(
                    select(Tag).where(Tag.name.in_(missing))
                )
            ).all():
                by_name[t.name] = t
    else:
        # Happy path: pick up the IDs the flush just assigned.
        for t in (
            await db.scalars(
                select(Tag).where(Tag.name.in_(missing))
            )
        ).all():
            by_name[t.name] = t

    return [by_name[n] for n in names]


def build_ingredients(items: list[IngredientIn]) -> list[Ingredient]:
    return [
        Ingredient(
            quantity=i.quantity,
            unit=i.unit,
            name=i.name,
            sort_order=idx,
        )
        for idx, i in enumerate(items)
    ]


def build_steps(items: list[StepIn]) -> list[Step]:
    return [Step(body=s.body, sort_order=idx) for idx, s in enumerate(items)]


def _fmt_quantity(q) -> str:
    """Format a Decimal/float quantity the same way the Flutter render
    does — strip trailing `.0` (so `1.00` reads as `1`, not `1.00`).
    Kept loosely typed so this works for both Decimal (Pydantic) and
    SQLAlchemy `Numeric` row values without an explicit conversion."""
    if q is None:
        return ""
    s = str(q).rstrip("0").rstrip(".")
    return s or "0"


def format_ingredient_line(
    *, quantity, unit: str | None, name: str
) -> str:
    """Compose an ingredient row into the same idiomatic display string
    the Flutter UI shows: "<qty> <unit> <name>" with empty parts
    skipped (e.g. "1 thumb fresh ginger", "60 ml lime juice",
    "1 tsp salt", "8 bone-in chicken thighs and drumsticks").

    Used as the unit of work for LLM translation. Splitting the line
    back into separate qty/unit/name fields cross-language is
    impossible — Vietnamese collapses "1 tbsp" to "1 muỗng canh",
    Japanese to "1 大さじ" — so the translator receives and returns
    the whole composed phrase, which the resolver then renders verbatim
    when the active locale has a translation."""
    parts = [s for s in (_fmt_quantity(quantity), unit, name) if s]
    return " ".join(parts).strip()
