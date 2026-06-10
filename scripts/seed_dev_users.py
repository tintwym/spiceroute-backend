"""Seed a handful of dev users + a few user-authored (non-premium) recipes.

This is a *local-only* helper that gives you something to look at when
you sign in with one of the dev-auth stub tokens (`dev:alice`,
`dev:bob`, `dev:carol`). Without it, a fresh local DB has 27 curated
recipes (all `user_id=NULL`) and the "My Recipes" / authored-recipe
flows have nothing to render.

Gated on `DEBUG=true`. The script refuses to run otherwise so it can't
accidentally pollute a production database.

Idempotent: matched on `firebase_uid` for users and on
`(user_id, title)` for recipes, so re-runs are safe.

Usage:
    DEBUG=true uv run python -m scripts.seed_dev_users
"""
import asyncio
import sys
from decimal import Decimal

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.cuisine import Cuisine
from app.models.spice_route import Ingredient, SpiceRoute, Step
from app.models.user import User

# Mirrors the `dev:<uid>[:<email>][:<name>]` parser in
# `app/services/firebase.py::_parse_dev_token`. Sign in from the client
# by sending `Authorization: Bearer dev:alice` (etc.) once DEBUG=true
# on the backend.
_DEV_USERS = [
    {
        "firebase_uid": "alice",
        "email": "alice@dev.local",
        "display_name": "Alice",
    },
    {
        "firebase_uid": "bob",
        "email": "bob@dev.local",
        "display_name": "Bob",
    },
    {
        "firebase_uid": "carol",
        "email": "carol@dev.local",
        "display_name": "Carol",
    },
]

# Each entry creates one user-authored SpiceRoute (is_premium=False,
# is_public=False) so the "My Recipes" tab has content to render WHEN
# you're signed in as the owner. Private so that even if this somehow
# runs against a shared/prod database, real users browsing Explore
# anonymously never see "Alice's Weeknight Pasta" mixed in with the
# curated content. Tags are deliberately omitted — these are personal
# recipes, not curated explore content.
_DEV_RECIPES = [
    {
        "owner_uid": "alice",
        "title": "Alice's Weeknight Pasta",
        "description": (
            "A 20-minute one-pan pasta that doesn't pretend to be Italian — "
            "spaghetti, garlic-confit oil, frozen peas, a generous shower "
            "of pecorino, and a hit of lemon zest."
        ),
        "cuisine": Cuisine.ITALIAN,
        "language": "en",
        "spice_level": 0,
        "prep": 5,
        "cook": 15,
        "servings": 2,
        "calories": 580,
        "ingredients": [
            {"quantity": 200, "unit": "g", "name": "spaghetti"},
            {"quantity": 3, "unit": "tbsp", "name": "garlic-confit oil"},
            {"quantity": 1, "unit": "cup", "name": "frozen peas"},
            {"quantity": 50, "unit": "g", "name": "pecorino, grated"},
            {"quantity": 1, "unit": None, "name": "lemon (zested)"},
        ],
        "steps": [
            "Boil spaghetti in well-salted water, 1 minute under the box time.",
            "While it cooks, warm the garlic oil in a wide pan over low heat.",
            "Add frozen peas to the pan; they'll thaw in about 2 minutes.",
            "Drag the pasta into the pan with tongs (don't drain — you want the starch water). Add a splash of pasta water if dry.",
            "Off heat: stir in pecorino and lemon zest. Taste, adjust salt, serve immediately.",
        ],
    },
    {
        "owner_uid": "alice",
        "title": "Brown Butter Banana Bread",
        "description": (
            "Forgiving, one-bowl banana bread that's better the next day. "
            "Browned butter is the only flex."
        ),
        "cuisine": Cuisine.AMERICAN_WESTERN,
        "language": "en",
        "spice_level": 0,
        "prep": 15,
        "cook": 55,
        "servings": 8,
        "calories": 320,
        "ingredients": [
            {"quantity": 115, "unit": "g", "name": "unsalted butter"},
            {"quantity": 3, "unit": None, "name": "very ripe bananas"},
            {"quantity": 150, "unit": "g", "name": "brown sugar"},
            {"quantity": 2, "unit": None, "name": "eggs"},
            {"quantity": 220, "unit": "g", "name": "plain flour"},
            {"quantity": 1, "unit": "tsp", "name": "baking soda"},
            {"quantity": 0.5, "unit": "tsp", "name": "salt"},
        ],
        "steps": [
            "Brown the butter in a small pan until it smells nutty and the milk solids are deep amber. Cool 5 minutes.",
            "Mash bananas in a large bowl. Whisk in the brown butter, sugar, and eggs.",
            "Fold in flour, baking soda, and salt — stop the moment there are no dry streaks.",
            "Pour into a buttered loaf tin and bake at 175 °C / 350 °F for 50-55 minutes, until a skewer comes out clean.",
            "Cool in the tin 10 minutes, then turn out. Wait until properly cool before slicing.",
        ],
    },
    {
        "owner_uid": "bob",
        "title": "Bob's Smoky Black Bean Tacos",
        "description": (
            "Pantry-friendly weeknight tacos — canned black beans, "
            "chipotle, lots of lime. Vegan if you skip the crumbled "
            "queso fresco on top."
        ),
        "cuisine": Cuisine.MEXICAN,
        "language": "en",
        "spice_level": 2,
        "prep": 5,
        "cook": 15,
        "servings": 3,
        "calories": 410,
        "ingredients": [
            {"quantity": 2, "unit": None, "name": "cans black beans"},
            {"quantity": 2, "unit": None, "name": "chipotles in adobo"},
            {"quantity": 1, "unit": "tsp", "name": "ground cumin"},
            {"quantity": 1, "unit": None, "name": "white onion, diced"},
            {"quantity": 8, "unit": None, "name": "corn tortillas"},
            {"quantity": 1, "unit": None, "name": "lime, cut in wedges"},
        ],
        "steps": [
            "Sauté the onion in a glug of oil until translucent, 4 minutes.",
            "Add cumin and chipotles (mince them first); cook 30 seconds.",
            "Tip in the beans with their liquid. Simmer 8 minutes, mashing about half with the back of a spoon for body.",
            "Warm tortillas in a dry pan, 20 seconds per side.",
            "Fill, squeeze with lime, top with whatever's in the fridge (cilantro, queso fresco, pickled red onion).",
        ],
    },
    {
        "owner_uid": "bob",
        "title": "Crispy Smashed Potatoes",
        "description": (
            "Side dish that punches above its weight. Two-stage: boil "
            "until knife-tender, smash, roast hot."
        ),
        "cuisine": Cuisine.AMERICAN_WESTERN,
        "language": "en",
        "spice_level": 0,
        "prep": 10,
        "cook": 40,
        "servings": 4,
        "calories": 240,
        "ingredients": [
            {"quantity": 750, "unit": "g", "name": "baby potatoes"},
            {"quantity": 3, "unit": "tbsp", "name": "olive oil"},
            {"quantity": 1, "unit": "tsp", "name": "flaky salt"},
            {"quantity": 4, "unit": None, "name": "sprigs rosemary"},
        ],
        "steps": [
            "Boil potatoes in salted water until a knife slides in without resistance, ~15 minutes. Drain and steam-dry 5 minutes.",
            "On an oiled sheet pan, smash each potato flat with the bottom of a glass.",
            "Drizzle with oil, tuck rosemary between them, sprinkle with salt.",
            "Roast at 220 °C / 425 °F for 25 minutes, flipping once, until lacy and dark gold at the edges.",
        ],
    },
    {
        "owner_uid": "carol",
        "title": "Carol's Cold Sesame Noodles",
        "description": (
            "Make-ahead lunch. Sauce keeps in the fridge for a week; "
            "boil noodles when you're hungry."
        ),
        "cuisine": Cuisine.CHINESE,
        "language": "en",
        "spice_level": 1,
        "prep": 10,
        "cook": 8,
        "servings": 2,
        "calories": 520,
        "ingredients": [
            {"quantity": 200, "unit": "g", "name": "wheat noodles"},
            {"quantity": 3, "unit": "tbsp", "name": "tahini or sesame paste"},
            {"quantity": 2, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "rice vinegar"},
            {"quantity": 1, "unit": "tsp", "name": "chili crisp"},
            {"quantity": 2, "unit": None, "name": "spring onions, sliced"},
            {"quantity": 0.5, "unit": None, "name": "cucumber, julienned"},
        ],
        "steps": [
            "Whisk tahini, soy, vinegar, chili crisp, and a splash of warm water until smooth and pourable.",
            "Cook noodles to the box time. Drain and rinse under cold water.",
            "Toss noodles with the sauce until evenly coated.",
            "Top with spring onions and cucumber. Eats cold or at room temperature.",
        ],
    },
    {
        "owner_uid": "carol",
        "title": "Yogurt Marinated Chicken Thighs",
        "description": (
            "Yogurt tenderises and the spices stick to it on the grill. "
            "Marinate overnight if you can, 1 hour at minimum."
        ),
        "cuisine": Cuisine.INDIAN,
        "language": "en",
        "spice_level": 2,
        "prep": 15,
        "cook": 18,
        "servings": 4,
        "calories": 480,
        "ingredients": [
            {"quantity": 8, "unit": None, "name": "boneless chicken thighs"},
            {"quantity": 200, "unit": "g", "name": "full-fat yogurt"},
            {"quantity": 2, "unit": "tbsp", "name": "garam masala"},
            {"quantity": 4, "unit": None, "name": "garlic cloves, grated"},
            {"quantity": 1, "unit": "tbsp", "name": "grated ginger"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 1, "unit": None, "name": "lemon, juiced"},
        ],
        "steps": [
            "Whisk everything except the chicken into a marinade.",
            "Coat the thighs thoroughly. Cover and refrigerate at least 1 hour, ideally overnight.",
            "Heat a grill pan or grill to medium-high. Wipe excess marinade off the chicken so it doesn't catch.",
            "Cook 7-9 minutes per side until well charred and the juices run clear.",
            "Rest 5 minutes; serve with rice or warm flatbread and extra yogurt on the side.",
        ],
    },
]


async def main() -> None:
    settings = get_settings()
    if not settings.debug:
        print(
            "Refusing to seed dev users: DEBUG is false. This script is for "
            "local development only. Set DEBUG=true if you really mean it.",
            file=sys.stderr,
        )
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        # Phase 1: upsert users by firebase_uid.
        existing_users = (
            await db.scalars(
                select(User).where(
                    User.firebase_uid.in_([u["firebase_uid"] for u in _DEV_USERS])
                )
            )
        ).all()
        users_by_uid = {u.firebase_uid: u for u in existing_users}

        users_added = 0
        for spec in _DEV_USERS:
            if spec["firebase_uid"] in users_by_uid:
                continue
            user = User(
                firebase_uid=spec["firebase_uid"],
                email=spec["email"],
                display_name=spec["display_name"],
            )
            db.add(user)
            users_by_uid[spec["firebase_uid"]] = user
            users_added += 1
        # Flush so the newly-added users get their `id` populated before
        # we reference it on the SpiceRoute rows below.
        await db.flush()

        # Phase 2: upsert authored recipes by (owner, title). We
        # deliberately don't update existing rows here — if someone
        # tweaked their seeded recipe in dev we don't want a re-run to
        # clobber their changes.
        existing_recipes = (
            await db.scalars(
                select(SpiceRoute).where(
                    SpiceRoute.is_premium.is_(False),
                    SpiceRoute.user_id.in_([u.id for u in users_by_uid.values()]),
                )
            )
        ).all()
        existing_keys = {(r.user_id, r.title) for r in existing_recipes}

        recipes_added = 0
        for spec in _DEV_RECIPES:
            owner = users_by_uid[spec["owner_uid"]]
            if (owner.id, spec["title"]) in existing_keys:
                continue
            sr = SpiceRoute(
                user_id=owner.id,
                title=spec["title"],
                description=spec["description"],
                cuisine=spec["cuisine"],
                language=spec["language"],
                spice_level=spec["spice_level"],
                prep_minutes=spec["prep"],
                cook_minutes=spec["cook"],
                servings=spec["servings"],
                calories_per_serving=spec["calories"],
                is_public=False,
                is_premium=False,
                ingredients=[
                    Ingredient(
                        # `Decimal(str(...))` so quantities like 0.5
                        # land exact in Numeric(10, 3) instead of round-
                        # tripping through Python float and emerging as
                        # 0.49999999... — same pattern the curated seed
                        # uses, kept consistent here.
                        quantity=Decimal(str(ing["quantity"])),
                        unit=ing["unit"],
                        name=ing["name"],
                        sort_order=i,
                    )
                    for i, ing in enumerate(spec["ingredients"])
                ],
                steps=[
                    Step(sort_order=i, body=body)
                    for i, body in enumerate(spec["steps"])
                ],
            )
            db.add(sr)
            recipes_added += 1

        await db.commit()
        print(
            f"Seeded {users_added} dev user(s) "
            f"(total {len(users_by_uid)}) and "
            f"{recipes_added} authored recipe(s) "
            f"(total {len(existing_keys) + recipes_added})."
        )


if __name__ == "__main__":
    asyncio.run(main())
