"""Seed the database with a demo user and a starter set of spice_routes.

Idempotent: re-running won't duplicate the demo user or their spice_routes.

Usage (inside the api container):
    docker compose exec api python -m scripts.seed
"""

import asyncio
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.spice_route import Ingredient, SpiceRoute, Step
from app.models.tag import Tag
from app.models.user import User

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demopass1"
DEMO_NAME = "Demo Cook"

# Each spice_route: title, desc, prep, cook, servings, tags, ingredients (qty, unit, name), steps
SPICE_ROUTES: list[dict[str, Any]] = [
    {
        "title": "Spaghetti Carbonara",
        "description": "The real Roman version: eggs, pecorino, guanciale, pepper. No cream.",
        "prep": 10, "cook": 15, "servings": 2,
        "tags": ["italian", "pasta", "weeknight"],
        "ingredients": [
            (200, "g", "spaghetti"),
            (100, "g", "guanciale"),
            (2, None, "egg yolks"),
            (1, None, "whole egg"),
            (50, "g", "pecorino romano"),
            (None, None, "freshly cracked black pepper"),
        ],
        "steps": [
            "Boil a large pot of salted water and cook spaghetti to al dente.",
            "Meanwhile, dice the guanciale and render slowly in a cold pan until crisp.",
            "Whisk yolks, whole egg, and grated pecorino with lots of pepper.",
            "Reserve a cup of pasta water, drain the spaghetti.",
            "Off heat, toss pasta with guanciale, then with the egg mixture and a splash of pasta water until creamy.",
            "Serve immediately with more pecorino and pepper.",
        ],
    },
    {
        "title": "Pad See Ew",
        "description": "Thai stir-fried wide rice noodles with Chinese broccoli and dark soy.",
        "prep": 15, "cook": 8, "servings": 2,
        "tags": ["thai", "noodles", "weeknight"],
        "ingredients": [
            (200, "g", "wide rice noodles"),
            (200, "g", "chicken thigh, sliced"),
            (1, "bunch", "Chinese broccoli"),
            (2, "tbsp", "dark soy sauce"),
            (1, "tbsp", "oyster sauce"),
            (1, "tsp", "sugar"),
            (2, None, "eggs"),
            (3, "tbsp", "neutral oil"),
            (3, "cloves", "garlic, minced"),
        ],
        "steps": [
            "Soak rice noodles in warm water until pliable, then drain.",
            "Heat oil in a wok over high heat. Stir-fry garlic and chicken until cooked.",
            "Push to the side, crack in eggs and scramble.",
            "Add noodles, sauces, and sugar. Toss to coat.",
            "Add Chinese broccoli stems first, then leaves. Stir-fry until just wilted.",
            "Serve hot with chili vinegar on the side.",
        ],
    },
    {
        "title": "Classic Chocolate Chip Cookies",
        "description": "Crispy edges, chewy center. The kind everyone fights over.",
        "prep": 15, "cook": 12, "servings": 24,
        "tags": ["dessert", "baking", "kid-friendly"],
        "ingredients": [
            (225, "g", "unsalted butter, softened"),
            (200, "g", "brown sugar"),
            (100, "g", "granulated sugar"),
            (2, None, "eggs"),
            (1, "tsp", "vanilla extract"),
            (300, "g", "all-purpose flour"),
            (1, "tsp", "baking soda"),
            (1, "tsp", "salt"),
            (300, "g", "dark chocolate chips"),
        ],
        "steps": [
            "Preheat oven to 180 C and line two baking sheets.",
            "Cream butter and both sugars until light and fluffy.",
            "Beat in eggs one at a time, then vanilla.",
            "Whisk flour, baking soda, and salt; stir into wet ingredients.",
            "Fold in chocolate chips.",
            "Scoop tablespoon-sized balls and space well on sheets.",
            "Bake 11-13 minutes until edges are golden but centers look underdone.",
            "Cool on the sheet for 5 minutes before transferring.",
        ],
    },
    {
        "title": "Avocado Toast with Egg",
        "description": "The 8-minute breakfast that actually keeps you full.",
        "prep": 3, "cook": 5, "servings": 1,
        "tags": ["breakfast", "quick", "vegetarian"],
        "ingredients": [
            (2, "slices", "sourdough bread"),
            (1, None, "ripe avocado"),
            (1, None, "egg"),
            (None, None, "lemon juice"),
            (None, None, "chili flakes"),
            (None, None, "flaky salt"),
        ],
        "steps": [
            "Toast bread until deeply golden.",
            "Fry the egg in olive oil to your liking.",
            "Mash avocado with a squeeze of lemon and a pinch of salt.",
            "Pile avocado on toast, top with egg, finish with chili flakes and flaky salt.",
        ],
    },
    {
        "title": "Lentil Soup",
        "description": "One pot, pantry friendly, freezes beautifully.",
        "prep": 10, "cook": 35, "servings": 6,
        "tags": ["vegetarian", "soup", "meal-prep", "gluten-free"],
        "ingredients": [
            (250, "g", "brown or green lentils"),
            (1, None, "onion, diced"),
            (2, None, "carrots, diced"),
            (2, "stalks", "celery, diced"),
            (3, "cloves", "garlic, minced"),
            (1, "can", "diced tomatoes"),
            (1.5, "L", "vegetable stock"),
            (1, "tsp", "cumin"),
            (1, "tsp", "smoked paprika"),
            (2, "tbsp", "olive oil"),
            (None, None, "salt and pepper"),
        ],
        "steps": [
            "Heat oil and sweat onion, carrot, and celery until soft.",
            "Add garlic, cumin, and paprika; stir 30 seconds.",
            "Add lentils, tomatoes, and stock. Bring to a boil.",
            "Simmer covered ~30 min until lentils are tender.",
            "Season generously. Finish with a squeeze of lemon.",
        ],
    },
    {
        "title": "Chicken Tikka Masala",
        "description": "Marinated chicken in a creamy spiced tomato sauce. Restaurant style.",
        "prep": 20, "cook": 40, "servings": 4,
        "tags": ["indian", "curry", "weekend"],
        "ingredients": [
            (700, "g", "boneless chicken thighs"),
            (200, "g", "Greek yogurt"),
            (3, "tbsp", "garam masala"),
            (2, "tbsp", "ginger-garlic paste"),
            (1, None, "large onion, finely chopped"),
            (1, "can", "tomato puree"),
            (200, "ml", "double cream"),
            (2, "tbsp", "ghee"),
            (1, "tsp", "kashmiri chili powder"),
            (None, None, "fresh coriander to finish"),
        ],
        "steps": [
            "Marinate chicken in yogurt, half the garam masala, and ginger-garlic paste for at least 1 hour.",
            "Grill or sear chicken until charred on the edges.",
            "Saute onion in ghee until deep golden.",
            "Stir in remaining garam masala and chili. Add tomato puree and simmer 10 min.",
            "Add cream and the seared chicken. Simmer 15 min more.",
            "Finish with coriander. Serve with basmati rice or naan.",
        ],
    },
    {
        "title": "Caesar Salad",
        "description": "Anchovy in the dressing is not optional.",
        "prep": 15, "cook": 8, "servings": 2,
        "tags": ["salad", "quick", "lunch"],
        "ingredients": [
            (1, "head", "romaine lettuce"),
            (4, "slices", "stale sourdough, torn"),
            (50, "g", "parmesan, shaved"),
            (2, None, "anchovy fillets"),
            (1, "clove", "garlic"),
            (1, None, "egg yolk"),
            (1, "tbsp", "lemon juice"),
            (1, "tsp", "Dijon mustard"),
            (60, "ml", "olive oil"),
        ],
        "steps": [
            "Toss bread with olive oil and salt; bake at 200 C until crisp.",
            "Mash anchovy and garlic to a paste. Whisk with yolk, lemon, Dijon.",
            "Slowly whisk in olive oil until emulsified.",
            "Toss romaine with dressing, croutons, and parmesan. Pepper to finish.",
        ],
    },
    {
        "title": "Shakshuka",
        "description": "Eggs poached in spiced tomato and pepper sauce. Brunch hero.",
        "prep": 10, "cook": 25, "servings": 4,
        "tags": ["breakfast", "vegetarian", "middle-eastern"],
        "ingredients": [
            (2, "tbsp", "olive oil"),
            (1, None, "large onion, sliced"),
            (2, None, "red peppers, sliced"),
            (4, "cloves", "garlic, sliced"),
            (1, "tsp", "ground cumin"),
            (1, "tsp", "smoked paprika"),
            (1, "can", "whole peeled tomatoes"),
            (4, None, "eggs"),
            (100, "g", "feta, crumbled"),
            (None, None, "fresh parsley"),
        ],
        "steps": [
            "Soften onion and peppers in olive oil over medium heat ~10 min.",
            "Add garlic and spices; cook 1 minute.",
            "Pour in tomatoes, crushing with a spoon. Simmer 10 min until thick.",
            "Make wells; crack an egg into each. Cover and cook until whites set.",
            "Scatter feta and parsley. Serve with crusty bread.",
        ],
    },
    {
        "title": "Banana Bread",
        "description": "Use the blackest bananas you can find. That's the secret.",
        "prep": 10, "cook": 55, "servings": 8,
        "tags": ["baking", "dessert", "breakfast"],
        "ingredients": [
            (3, None, "very ripe bananas"),
            (115, "g", "butter, melted"),
            (150, "g", "sugar"),
            (1, None, "egg"),
            (1, "tsp", "vanilla extract"),
            (1, "tsp", "baking soda"),
            (1, "pinch", "salt"),
            (200, "g", "all-purpose flour"),
            (100, "g", "walnuts, chopped"),
        ],
        "steps": [
            "Preheat oven to 175 C. Grease a loaf tin.",
            "Mash bananas in a bowl, then stir in melted butter.",
            "Mix in sugar, egg, and vanilla.",
            "Sprinkle baking soda and salt over the mixture. Stir.",
            "Fold in flour, then walnuts.",
            "Pour into the tin, bake ~55 min until a skewer comes out clean.",
        ],
    },
    {
        "title": "Pho Ga (Chicken Pho)",
        "description": "A simpler weeknight take on Vietnamese chicken noodle soup.",
        "prep": 15, "cook": 60, "servings": 4,
        "tags": ["vietnamese", "noodles", "soup"],
        "ingredients": [
            (1, "kg", "whole chicken"),
            (2, "L", "water"),
            (1, None, "onion, halved"),
            (1, "thumb", "ginger, halved"),
            (3, None, "star anise"),
            (1, "stick", "cinnamon"),
            (4, None, "cloves"),
            (3, "tbsp", "fish sauce"),
            (1, "tbsp", "sugar"),
            (300, "g", "rice noodles"),
            (None, None, "Thai basil, lime, chili, bean sprouts"),
        ],
        "steps": [
            "Char onion and ginger over an open flame or under a broiler until blackened.",
            "Toast spices in a dry pan until fragrant.",
            "Add chicken, water, charred aromatics, and spices to a pot. Simmer gently 45 min.",
            "Remove chicken, shred meat. Strain broth and season with fish sauce and sugar.",
            "Cook rice noodles per package.",
            "Assemble bowls with noodles, shredded chicken, hot broth, and serve with herbs/lime/chili on the side.",
        ],
    },
    {
        "title": "Greek Salad",
        "description": "Tomato, cucumber, olives, feta. Don't overthink it.",
        "prep": 10, "cook": 0, "servings": 4,
        "tags": ["salad", "greek", "vegetarian", "gluten-free", "quick"],
        "ingredients": [
            (4, None, "ripe tomatoes, chunked"),
            (1, None, "cucumber, chunked"),
            (1, None, "red onion, thinly sliced"),
            (100, "g", "Kalamata olives"),
            (200, "g", "feta, in slabs"),
            (60, "ml", "olive oil"),
            (1, "tbsp", "red wine vinegar"),
            (1, "tsp", "dried oregano"),
        ],
        "steps": [
            "Toss tomato, cucumber, onion, and olives in a bowl.",
            "Place feta slabs on top.",
            "Drizzle olive oil and vinegar, scatter oregano, season with salt and pepper.",
        ],
    },
    {
        "title": "Miso Glazed Salmon",
        "description": "Sweet-savory miso lacquer, sticky on the outside, just-cooked in the middle.",
        "prep": 10, "cook": 12, "servings": 2,
        "tags": ["japanese", "fish", "weeknight", "gluten-free"],
        "ingredients": [
            (2, "fillets", "salmon"),
            (3, "tbsp", "white miso paste"),
            (2, "tbsp", "mirin"),
            (1, "tbsp", "soy sauce"),
            (1, "tbsp", "sugar"),
            (1, "tsp", "grated ginger"),
            (None, None, "spring onion, sliced"),
            (None, None, "sesame seeds"),
        ],
        "steps": [
            "Whisk miso, mirin, soy, sugar, and ginger into a glaze.",
            "Marinate salmon in half the glaze for 20 minutes.",
            "Heat oven to 220 C. Place salmon skin-down in a lined tray.",
            "Roast 8 minutes. Brush with remaining glaze, then broil 2-3 min until lacquered.",
            "Top with spring onion and sesame. Serve with rice.",
        ],
    },
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            user = User(
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=DEMO_NAME,
            )
            db.add(user)
            await db.flush()
            print(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            print(f"Demo user already exists: {DEMO_EMAIL}")

        existing_titles = {
            r.title
            for r in (
                await db.scalars(select(SpiceRoute).where(SpiceRoute.user_id == user.id))
            ).all()
        }

        all_tag_names = {n for r in SPICE_ROUTES for n in r["tags"]}
        existing_tags = {
            t.name: t
            for t in (
                await db.scalars(select(Tag).where(Tag.name.in_(all_tag_names)))
            ).all()
        }
        for name in all_tag_names:
            if name not in existing_tags:
                t = Tag(name=name)
                db.add(t)
                existing_tags[name] = t
        await db.flush()

        added = 0
        for spec in SPICE_ROUTES:
            if spec["title"] in existing_titles:
                continue
            spice_route = SpiceRoute(
                user_id=user.id,
                title=spec["title"],
                description=spec["description"],
                prep_minutes=spec["prep"],
                cook_minutes=spec["cook"],
                servings=spec["servings"],
                is_public=True,
                ingredients=[
                    Ingredient(
                        quantity=Decimal(str(q)) if q is not None else None,
                        unit=u,
                        name=n,
                        sort_order=i,
                    )
                    for i, (q, u, n) in enumerate(spec["ingredients"])
                ],
                steps=[
                    Step(sort_order=i, body=body)
                    for i, body in enumerate(spec["steps"])
                ],
                tags=[existing_tags[name] for name in spec["tags"]],
            )
            db.add(spice_route)
            added += 1

        await db.commit()
        print(f"Added {added} new spice_routes (skipped {len(SPICE_ROUTES) - added} duplicates).")
        print(f"\nLog in at the Flutter app with:\n  email:    {DEMO_EMAIL}\n  password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
