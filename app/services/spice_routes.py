from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spice_route import Ingredient, Step
from app.models.tag import Tag
from app.schemas.spice_route import IngredientIn, StepIn


async def upsert_tags(db: AsyncSession, names: list[str]) -> list[Tag]:
    """Return Tag rows for each name, creating ones that don't exist yet."""
    if not names:
        return []

    existing = (
        await db.scalars(select(Tag).where(Tag.name.in_(names)))
    ).all()
    by_name = {t.name: t for t in existing}

    created: list[Tag] = []
    for n in names:
        if n not in by_name:
            tag = Tag(name=n)
            db.add(tag)
            by_name[n] = tag
            created.append(tag)
    if created:
        await db.flush()
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
