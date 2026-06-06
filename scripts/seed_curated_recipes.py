"""Seed the database with the 27 curated `is_premium=True` recipes.

Idempotent: re-running won't duplicate existing curated recipes (matched by
exact title). Safe to run after every deploy.

Usage:
    uv run python -m scripts.seed_curated_recipes
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.cuisine import Cuisine
from app.models.spice_route import Ingredient, SpiceRoute, Step
from app.models.tag import Tag
from scripts.curated_data import CURATED


async def main() -> None:
    async with AsyncSessionLocal() as db:
        existing = {
            r.title
            for r in (
                await db.scalars(
                    select(SpiceRoute).where(SpiceRoute.is_premium.is_(True))
                )
            ).all()
        }

        all_tag_names = sorted({n for r in CURATED for n in r["tags"]})
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

        added = 0
        skipped = 0
        for spec in CURATED:
            if spec["title"] in existing:
                skipped += 1
                continue
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
                image_path=spec["image"],
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
                tags=[tag_by_name[name] for name in spec["tags"]],
            )
            db.add(sr)
            added += 1

        await db.commit()
        print(
            f"Seeded {added} curated recipes (skipped {skipped} duplicates)."
        )


if __name__ == "__main__":
    asyncio.run(main())
