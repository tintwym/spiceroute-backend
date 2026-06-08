"""Curated seed recipes for the Explore tab (3 per cuisine, 27 total).

Image URLs are curated Unsplash food photos referenced by photo ID. Each
ID below was hand-checked to (a) return HTTP 200 and (b) actually depict
the dish. Picsum.photos was the previous fallback but served random nature
shots (forests, museums, deer) that had nothing to do with the recipes.
"""

from typing import NotRequired, TypedDict


class IngredientSpec(TypedDict, total=False):
    quantity: float
    unit: str
    name: str


class RecipeSpec(TypedDict):
    title: str
    description: str
    cuisine: str
    language: str
    spice_level: int
    prep: int
    cook: int
    servings: int
    image: str
    tags: list[str]
    ingredients: list[IngredientSpec]
    steps: list[str]
    # Optional. Falls back to a per-cuisine default in the seed script when
    # unset, so existing entries keep working without manual annotation.
    calories: NotRequired[int]


# Slug -> Unsplash photo ID. The slug is whatever we pass to `_img(slug)`
# at the recipe definition site. If a slug is missing here we fall back
# to a generic "plated food" Unsplash photo rather than picsum.photos so
# every card still shows *food*.
_UNSPLASH_BY_SLUG: dict[str, str] = {
    # Korean
    "kimchi-jjigae": "1583224944844-5b268c057b72",
    "bibimbap": "1546069901-ba9599a7e63c",
    "kfc-yangnyeom": "1562967914-608f82629710",
    # Japanese
    "tamago-donburi": "1611143669185-af224c5e3252",
    "miso-salmon": "1467003909585-2f8a72700288",
    "cold-soba": "1607330289024-1535c6b4e1c1",
    # Chinese
    "mapo-tofu": "1582450871972-ab5ca641643d",
    "egg-drop-soup": "1612927601601-6638404737ce",
    "beef-broccoli": "1583394293214-28ded15ee548",
    # Burmese
    "mohinga": "1569058242253-92a9c755a0ec",
    "lahpet-thoke": "1605908502724-9093a79a1b39",
    "shan-noodles": "1551782450-a2132b4ba21d",
    # Thai
    "pad-krapow": "1569562211093-4ed0d0758f12",
    "tom-yum": "1503764654157-72d979d9af2f",
    "som-tum": "1559314809-0d155014e29e",
    # Indian
    "tikka-masala": "1565557623262-b51c2513a641",
    "dal-tadka": "1546833999-b9f581a1996d",
    "aloo-gobi": "1589302168068-964664d93dc0",
    # Italian
    "carbonara": "1612874742237-6526221588e3",
    "aglio-olio": "1551183053-bf91a1d81141",
    "margherita": "1604068549290-dea0e4a305ca",
    # American / Western
    "sheet-pan-chicken": "1604908176997-125f25cc6f3d",
    "cheeseburger": "1568901346375-23c9450c58cd",
    "choc-chip-cookies": "1499636136210-6f4ee915583e",
    # Mexican
    "chicken-tinga": "1565299585323-38d6b0865b47",
    "guacamole": "1600335895229-6e75511892c8",
    "carne-asada": "1544025162-d76694265947",
}

# Generic, food-themed fallback when a slug is unknown. Better than
# picsum (which served random nature shots) and at least keeps the card
# visually coherent.
_GENERIC_FOOD_PHOTO_ID = "1504674900247-0877df9cc836"  # plated food


def _img(slug: str) -> str:
    photo_id = _UNSPLASH_BY_SLUG.get(slug, _GENERIC_FOOD_PHOTO_ID)
    return (
        f"https://images.unsplash.com/photo-{photo_id}"
        "?w=1200&q=80&auto=format&fit=crop"
    )


CURATED: list[RecipeSpec] = [
    # ---- Korean ----
    {
        "title": "Kimchi Jjigae",
        "description": "Comforting fermented kimchi stew with pork belly and tofu.",
        "cuisine": "korean", "language": "en", "spice_level": 2,
        "prep": 10, "cook": 30, "servings": 3, "image": _img("kimchi-jjigae"),
        "tags": ["stew", "comfort", "weeknight"],
        "ingredients": [
            {"quantity": 300, "unit": "g", "name": "well-aged kimchi, chopped"},
            {"quantity": 200, "unit": "g", "name": "pork belly, sliced"},
            {"quantity": 1, "unit": "block", "name": "soft tofu, cubed"},
            {"quantity": 1, "unit": "tbsp", "name": "gochujang"},
            {"quantity": 1, "unit": "tbsp", "name": "gochugaru"},
            {"quantity": 1, "name": "small onion, sliced"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 600, "unit": "ml", "name": "water or anchovy stock"},
            {"name": "spring onion to garnish"},
        ],
        "steps": [
            "Render pork belly in a heavy pot until lightly crisp.",
            "Add kimchi, gochujang, gochugaru, and onion. Stir-fry 3 minutes.",
            "Pour in water/stock and garlic. Simmer 15 minutes.",
            "Slip in tofu and simmer another 5 minutes.",
            "Garnish with spring onion. Serve with rice.",
        ],
    },
    {
        "title": "Bibimbap",
        "description": "Mixed rice bowl with seasoned vegetables, beef, and a sunny egg.",
        "cuisine": "korean", "language": "en", "spice_level": 1,
        "prep": 25, "cook": 15, "servings": 2, "image": _img("bibimbap"),
        "tags": ["rice", "bowl", "balanced"],
        "ingredients": [
            {"quantity": 2, "unit": "cups", "name": "cooked short-grain rice"},
            {"quantity": 200, "unit": "g", "name": "beef sirloin, thinly sliced"},
            {"quantity": 100, "unit": "g", "name": "spinach"},
            {"quantity": 100, "unit": "g", "name": "bean sprouts"},
            {"quantity": 1, "name": "carrot, julienned"},
            {"quantity": 1, "name": "zucchini, julienned"},
            {"quantity": 2, "name": "eggs"},
            {"quantity": 2, "unit": "tbsp", "name": "gochujang"},
            {"quantity": 2, "unit": "tsp", "name": "sesame oil"},
        ],
        "steps": [
            "Marinate beef in soy, sugar, garlic, and sesame oil for 10 min.",
            "Blanch spinach and bean sprouts; season each with salt and sesame oil.",
            "Stir-fry carrot and zucchini separately, just until tender.",
            "Sear beef quickly over high heat.",
            "Fry eggs sunny-side up.",
            "Pile rice in bowls, fan vegetables and beef on top, crown with egg and gochujang.",
        ],
    },
    {
        "title": "Korean Fried Chicken",
        "description": "Twice-fried for shatter-glass crisp, tossed in sweet-spicy yangnyeom sauce.",
        "cuisine": "korean", "language": "en", "spice_level": 2,
        "prep": 20, "cook": 25, "servings": 4, "image": _img("kfc-yangnyeom"),
        "tags": ["fried", "weekend", "party"],
        "ingredients": [
            {"quantity": 1, "unit": "kg", "name": "chicken wings"},
            {"quantity": 100, "unit": "g", "name": "potato starch"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 3, "unit": "tbsp", "name": "gochujang"},
            {"quantity": 2, "unit": "tbsp", "name": "honey"},
            {"quantity": 2, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "rice vinegar"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, minced"},
            {"name": "neutral oil for frying"},
            {"name": "toasted sesame seeds"},
        ],
        "steps": [
            "Pat wings dry and toss with salt and potato starch.",
            "Heat oil to 160 C. Fry wings 8 minutes; drain.",
            "Raise oil to 180 C. Fry wings again 4-5 minutes until deep golden.",
            "Simmer gochujang, honey, soy, vinegar, and garlic until syrupy.",
            "Toss hot wings in sauce; finish with sesame seeds.",
        ],
    },
    # ---- Japanese ----
    {
        "title": "Tamago Donburi",
        "description": "Soft, custardy egg over rice with sweet-savory dashi sauce.",
        "cuisine": "japanese", "language": "en", "spice_level": 0,
        "prep": 5, "cook": 8, "servings": 1, "image": _img("tamago-donburi"),
        "tags": ["rice", "quick", "comfort"],
        "ingredients": [
            {"quantity": 1, "unit": "bowl", "name": "hot cooked rice"},
            {"quantity": 3, "name": "eggs, lightly beaten"},
            {"quantity": 100, "unit": "ml", "name": "dashi"},
            {"quantity": 1, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "mirin"},
            {"quantity": 1, "unit": "tsp", "name": "sugar"},
            {"name": "spring onion, sliced thin"},
        ],
        "steps": [
            "Combine dashi, soy, mirin, and sugar in a small pan; bring to a simmer.",
            "Pour in beaten eggs in two stages, swirling gently.",
            "Cover and cook 30 seconds; eggs should be just-set, glossy.",
            "Slide onto rice. Top with spring onion.",
        ],
    },
    {
        "title": "Miso Glazed Salmon",
        "description": "Sweet-savory miso lacquer, sticky outside, just-cooked center.",
        "cuisine": "japanese", "language": "en", "spice_level": 0,
        "prep": 10, "cook": 12, "servings": 2, "image": _img("miso-salmon"),
        "tags": ["fish", "weeknight", "gluten-free"],
        "ingredients": [
            {"quantity": 2, "unit": "fillets", "name": "salmon"},
            {"quantity": 3, "unit": "tbsp", "name": "white miso"},
            {"quantity": 2, "unit": "tbsp", "name": "mirin"},
            {"quantity": 1, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "sugar"},
            {"quantity": 1, "unit": "tsp", "name": "grated ginger"},
            {"name": "spring onion, sesame seeds"},
        ],
        "steps": [
            "Whisk miso, mirin, soy, sugar, and ginger.",
            "Marinate salmon in half the glaze 20 minutes.",
            "Roast at 220 C for 8 minutes.",
            "Brush with remaining glaze, broil 2-3 minutes until lacquered.",
            "Garnish with spring onion and sesame.",
        ],
    },
    {
        "title": "Cold Soba with Dipping Sauce",
        "description": "Buckwheat noodles served chilled with a savory tsuyu dip.",
        "cuisine": "japanese", "language": "en", "spice_level": 0,
        "prep": 5, "cook": 10, "servings": 2, "image": _img("cold-soba"),
        "tags": ["noodles", "summer", "vegetarian"],
        "ingredients": [
            {"quantity": 200, "unit": "g", "name": "dried soba noodles"},
            {"quantity": 200, "unit": "ml", "name": "dashi"},
            {"quantity": 50, "unit": "ml", "name": "soy sauce"},
            {"quantity": 50, "unit": "ml", "name": "mirin"},
            {"quantity": 1, "unit": "tbsp", "name": "sugar"},
            {"name": "wasabi, grated daikon, spring onion"},
            {"name": "shredded nori"},
        ],
        "steps": [
            "Simmer dashi, soy, mirin, and sugar 2 minutes; chill the tsuyu.",
            "Boil soba per package, then shock in iced water and drain well.",
            "Plate noodles on bamboo mats with shredded nori on top.",
            "Serve tsuyu in small cups alongside wasabi, daikon, and spring onion.",
        ],
    },
    # ---- Chinese ----
    {
        "title": "Mapo Tofu",
        "description": "Sichuan classic: silken tofu in a numbing-spicy chili-bean sauce.",
        "cuisine": "chinese", "language": "en", "spice_level": 3,
        "prep": 10, "cook": 15, "servings": 3, "image": _img("mapo-tofu"),
        "tags": ["sichuan", "tofu", "weeknight"],
        "ingredients": [
            {"quantity": 1, "unit": "block", "name": "silken tofu, cubed"},
            {"quantity": 150, "unit": "g", "name": "ground pork or beef"},
            {"quantity": 2, "unit": "tbsp", "name": "doubanjiang"},
            {"quantity": 1, "unit": "tbsp", "name": "fermented black beans, rinsed"},
            {"quantity": 1, "unit": "tsp", "name": "ground Sichuan peppercorn"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 200, "unit": "ml", "name": "stock"},
            {"quantity": 1, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "cornstarch slurry"},
            {"name": "spring onion, chili oil"},
        ],
        "steps": [
            "Brown ground meat in oil until crisp.",
            "Stir in doubanjiang, black beans, peppercorn, and garlic until fragrant.",
            "Pour in stock and soy sauce; slip in tofu.",
            "Simmer 5 minutes, gently folding to coat.",
            "Thicken with cornstarch slurry. Finish with spring onion and chili oil.",
        ],
    },
    {
        "title": "Egg Drop Soup",
        "description": "Silky egg ribbons in a clean ginger-scented broth.",
        "cuisine": "chinese", "language": "en", "spice_level": 0,
        "prep": 5, "cook": 10, "servings": 4, "image": _img("egg-drop-soup"),
        "tags": ["soup", "quick", "comfort"],
        "ingredients": [
            {"quantity": 1, "unit": "L", "name": "chicken stock"},
            {"quantity": 1, "unit": "tsp", "name": "grated ginger"},
            {"quantity": 1, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "tsp", "name": "sesame oil"},
            {"quantity": 1, "unit": "tbsp", "name": "cornstarch slurry"},
            {"quantity": 3, "name": "eggs, beaten"},
            {"name": "spring onion to garnish"},
            {"name": "white pepper"},
        ],
        "steps": [
            "Simmer stock, ginger, soy, and sesame oil.",
            "Stir in cornstarch slurry; cook until lightly thickened.",
            "Drizzle in beaten eggs while gently swirling the soup.",
            "Cut heat once ribbons set. Top with spring onion and white pepper.",
        ],
    },
    {
        "title": "Beef and Broccoli",
        "description": "Tender stir-fried beef and crisp-tender broccoli in a glossy soy sauce.",
        "cuisine": "chinese", "language": "en", "spice_level": 1,
        "prep": 15, "cook": 8, "servings": 2, "image": _img("beef-broccoli"),
        "tags": ["stir-fry", "weeknight", "high-protein"],
        "ingredients": [
            {"quantity": 300, "unit": "g", "name": "beef sirloin, thinly sliced"},
            {"quantity": 1, "unit": "tbsp", "name": "cornstarch"},
            {"quantity": 1, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 400, "unit": "g", "name": "broccoli florets"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 1, "unit": "tbsp", "name": "ginger, minced"},
            {"quantity": 2, "unit": "tbsp", "name": "oyster sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "shaoxing wine"},
            {"quantity": 100, "unit": "ml", "name": "stock"},
        ],
        "steps": [
            "Toss beef with cornstarch and soy. Rest 10 minutes.",
            "Blanch broccoli 1 minute, drain.",
            "Sear beef in hot wok until browned; remove.",
            "Stir-fry garlic and ginger 30 seconds. Add broccoli and beef back.",
            "Pour in oyster sauce, wine, and stock. Toss until glossy and coated.",
        ],
    },
    # ---- Burmese ----
    {
        "title": "Mohinga",
        "description": "Burmese national dish: lemongrass-fish broth with rice noodles.",
        "cuisine": "burmese", "language": "en", "spice_level": 1,
        "prep": 20, "cook": 50, "servings": 4, "image": _img("mohinga"),
        "tags": ["soup", "noodles", "weekend"],
        "ingredients": [
            {"quantity": 500, "unit": "g", "name": "catfish or tilapia, cleaned"},
            {"quantity": 2, "unit": "stalks", "name": "lemongrass, bruised"},
            {"quantity": 1, "name": "large onion, chopped"},
            {"quantity": 4, "unit": "cloves", "name": "garlic"},
            {"quantity": 1, "unit": "thumb", "name": "ginger"},
            {"quantity": 60, "unit": "g", "name": "chickpea flour"},
            {"quantity": 1, "unit": "L", "name": "fish stock or water"},
            {"quantity": 2, "unit": "tbsp", "name": "fish sauce"},
            {"quantity": 1, "unit": "tsp", "name": "turmeric"},
            {"quantity": 300, "unit": "g", "name": "rice vermicelli"},
            {"name": "boiled egg, lime wedges, fried garlic"},
        ],
        "steps": [
            "Poach fish with lemongrass and turmeric until cooked. Reserve broth, flake the fish.",
            "Blend onion, garlic, and ginger to a paste; saute in oil with turmeric.",
            "Stir chickpea flour with cold water and whisk into broth.",
            "Add aromatic paste, flaked fish, and fish sauce; simmer 30 minutes.",
            "Cook rice vermicelli per package and divide between bowls.",
            "Ladle hot broth on top. Garnish with boiled egg, lime, and fried garlic.",
        ],
    },
    {
        "title": "Burmese Tea Leaf Salad",
        "description": "Lahpet thoke: pickled tea leaves with crunchy beans, peanuts, and lime.",
        "cuisine": "burmese", "language": "en", "spice_level": 1,
        "prep": 15, "cook": 0, "servings": 4, "image": _img("lahpet-thoke"),
        "tags": ["salad", "snack", "vegetarian"],
        "ingredients": [
            {"quantity": 100, "unit": "g", "name": "fermented tea leaves (lahpet)"},
            {"quantity": 60, "unit": "g", "name": "fried split chickpeas"},
            {"quantity": 60, "unit": "g", "name": "fried garlic"},
            {"quantity": 60, "unit": "g", "name": "roasted peanuts"},
            {"quantity": 40, "unit": "g", "name": "toasted sesame seeds"},
            {"quantity": 2, "name": "ripe tomatoes, diced"},
            {"quantity": 1, "name": "garlic clove, minced"},
            {"quantity": 1, "name": "green chili, sliced"},
            {"quantity": 1, "name": "lime, juiced"},
            {"name": "shredded cabbage to bed"},
        ],
        "steps": [
            "Bed a platter with shredded cabbage.",
            "Mound tea leaves in the center.",
            "Arrange peanuts, chickpeas, garlic, sesame, tomato, and chili in stripes.",
            "Squeeze lime over and toss everything together at the table.",
        ],
    },
    {
        "title": "Shan Noodles",
        "description": "Shan-style rice noodles with lightly spiced tomato-pork sauce.",
        "cuisine": "burmese", "language": "en", "spice_level": 1,
        "prep": 15, "cook": 25, "servings": 3, "image": _img("shan-noodles"),
        "tags": ["noodles", "comfort", "weeknight"],
        "ingredients": [
            {"quantity": 300, "unit": "g", "name": "rice noodles"},
            {"quantity": 250, "unit": "g", "name": "ground pork or chicken"},
            {"quantity": 3, "name": "tomatoes, chopped"},
            {"quantity": 1, "name": "onion, finely chopped"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 1, "unit": "tsp", "name": "paprika"},
            {"quantity": 1, "unit": "tsp", "name": "turmeric"},
            {"quantity": 2, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "fish sauce"},
            {"name": "spring onion, chili oil, peanuts"},
        ],
        "steps": [
            "Saute onion and garlic until soft.",
            "Add pork, paprika, turmeric; brown until crumbled.",
            "Add tomatoes and a splash of water; simmer 15 minutes until jammy.",
            "Season with soy and fish sauce.",
            "Cook noodles, drain, and toss with the sauce.",
            "Top with spring onion, chili oil, and peanuts.",
        ],
    },
    # ---- Thai ----
    {
        "title": "Pad Krapow Gai",
        "description": "Thai street-food classic: chicken stir-fried with holy basil and chili.",
        "cuisine": "thai", "language": "en", "spice_level": 3,
        "prep": 5, "cook": 8, "servings": 2, "image": _img("pad-krapow"),
        "tags": ["weeknight", "spicy", "rice"],
        "ingredients": [
            {"quantity": 400, "unit": "g", "name": "ground chicken"},
            {"quantity": 4, "unit": "cloves", "name": "garlic"},
            {"quantity": 4, "name": "Thai bird chilies"},
            {"quantity": 1, "unit": "tbsp", "name": "oyster sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "tsp", "name": "fish sauce"},
            {"quantity": 1, "unit": "tsp", "name": "sugar"},
            {"quantity": 1, "unit": "cup", "name": "holy basil leaves"},
            {"quantity": 2, "name": "fried eggs, to serve"},
            {"name": "jasmine rice"},
        ],
        "steps": [
            "Pound garlic and chilies into a rough paste.",
            "Sear paste in hot oil until fragrant.",
            "Add chicken; break it up and sear until lightly browned.",
            "Stir in oyster sauce, soy, fish sauce, and sugar; toss 1 minute.",
            "Off heat, fold in holy basil.",
            "Serve over jasmine rice with a crisp-edged fried egg.",
        ],
    },
    {
        "title": "Tom Yum Goong",
        "description": "Spicy-sour shrimp soup with lemongrass, lime leaves, and chili.",
        "cuisine": "thai", "language": "en", "spice_level": 3,
        "prep": 10, "cook": 15, "servings": 3, "image": _img("tom-yum"),
        "tags": ["soup", "weeknight", "gluten-free"],
        "ingredients": [
            {"quantity": 500, "unit": "ml", "name": "shrimp or chicken stock"},
            {"quantity": 2, "unit": "stalks", "name": "lemongrass, bruised"},
            {"quantity": 4, "name": "kaffir lime leaves"},
            {"quantity": 4, "unit": "slices", "name": "galangal"},
            {"quantity": 300, "unit": "g", "name": "shrimp, peeled"},
            {"quantity": 200, "unit": "g", "name": "mushrooms, halved"},
            {"quantity": 2, "unit": "tbsp", "name": "fish sauce"},
            {"quantity": 2, "unit": "tbsp", "name": "lime juice"},
            {"quantity": 1, "unit": "tbsp", "name": "Thai chili paste (nam prik pao)"},
            {"name": "Thai chili and cilantro to finish"},
        ],
        "steps": [
            "Simmer stock with lemongrass, lime leaves, and galangal 5 minutes.",
            "Stir in chili paste. Add mushrooms and shrimp.",
            "Cook just until shrimp curl, about 3 minutes.",
            "Off heat, season with fish sauce, lime juice, and chili.",
            "Top with cilantro.",
        ],
    },
    {
        "title": "Green Papaya Salad",
        "description": "Som tum: pounded green papaya, lime, fish sauce, peanuts, fire.",
        "cuisine": "thai", "language": "en", "spice_level": 2,
        "prep": 15, "cook": 0, "servings": 2, "image": _img("som-tum"),
        "tags": ["salad", "spicy", "vegetarian-friendly"],
        "ingredients": [
            {"quantity": 1, "name": "small green papaya, shredded"},
            {"quantity": 8, "name": "cherry tomatoes, halved"},
            {"quantity": 8, "name": "long beans, cut into 2-inch pieces"},
            {"quantity": 2, "unit": "cloves", "name": "garlic"},
            {"quantity": 2, "name": "Thai chilies"},
            {"quantity": 2, "unit": "tbsp", "name": "lime juice"},
            {"quantity": 2, "unit": "tbsp", "name": "fish sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "palm sugar"},
            {"quantity": 30, "unit": "g", "name": "roasted peanuts"},
        ],
        "steps": [
            "Pound garlic and chilies in a mortar.",
            "Add long beans; bruise lightly.",
            "Add tomatoes; press to release juice.",
            "Toss in papaya. Pound and mix while adding lime, fish sauce, and palm sugar.",
            "Top with peanuts. Taste should be hot, sour, salty, and sweet.",
        ],
    },
    # ---- Indian ----
    {
        "title": "Chicken Tikka Masala",
        "description": "Restaurant-style: marinated chicken in a creamy spiced tomato sauce.",
        "cuisine": "indian", "language": "en", "spice_level": 2,
        "prep": 25, "cook": 40, "servings": 4, "image": _img("tikka-masala"),
        "tags": ["curry", "weekend", "comfort"],
        "ingredients": [
            {"quantity": 700, "unit": "g", "name": "boneless chicken thighs"},
            {"quantity": 200, "unit": "g", "name": "Greek yogurt"},
            {"quantity": 3, "unit": "tbsp", "name": "garam masala"},
            {"quantity": 2, "unit": "tbsp", "name": "ginger-garlic paste"},
            {"quantity": 1, "name": "large onion, finely chopped"},
            {"quantity": 1, "unit": "can", "name": "tomato puree"},
            {"quantity": 200, "unit": "ml", "name": "double cream"},
            {"quantity": 2, "unit": "tbsp", "name": "ghee"},
            {"quantity": 1, "unit": "tsp", "name": "kashmiri chili powder"},
            {"name": "fresh coriander"},
        ],
        "steps": [
            "Marinate chicken in yogurt, half the garam masala, and ginger-garlic paste at least 1 hour.",
            "Sear chicken until charred at the edges.",
            "Saute onion in ghee until deeply golden.",
            "Stir in remaining garam masala and chili. Add tomato puree; simmer 10 minutes.",
            "Add cream and chicken; simmer 15 minutes.",
            "Finish with coriander.",
        ],
    },
    {
        "title": "Dal Tadka",
        "description": "Yellow lentils tempered with cumin, garlic, and ghee.",
        "cuisine": "indian", "language": "en", "spice_level": 1,
        "prep": 5, "cook": 35, "servings": 4, "image": _img("dal-tadka"),
        "tags": ["vegetarian", "weeknight", "lentils"],
        "ingredients": [
            {"quantity": 250, "unit": "g", "name": "toor dal (split pigeon peas)"},
            {"quantity": 1, "unit": "tsp", "name": "turmeric"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 2, "unit": "tbsp", "name": "ghee"},
            {"quantity": 1, "unit": "tsp", "name": "cumin seeds"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, sliced"},
            {"quantity": 1, "name": "small onion, sliced"},
            {"quantity": 2, "name": "dried red chilies"},
            {"quantity": 1, "unit": "tsp", "name": "kashmiri chili powder"},
            {"name": "cilantro to finish"},
        ],
        "steps": [
            "Pressure-cook (or simmer) dal with water, turmeric, and salt until soft.",
            "In a small pan, heat ghee and bloom cumin seeds.",
            "Add garlic, onion, and dried chilies; cook to deep golden.",
            "Stir in chili powder. Pour the tempering over the dal.",
            "Top with cilantro.",
        ],
    },
    {
        "title": "Aloo Gobi",
        "description": "Dry-style potato and cauliflower with toasted spices.",
        "cuisine": "indian", "language": "en", "spice_level": 1,
        "prep": 10, "cook": 25, "servings": 4, "image": _img("aloo-gobi"),
        "tags": ["vegetarian", "vegan", "weeknight", "gluten-free"],
        "ingredients": [
            {"quantity": 1, "name": "cauliflower, in florets"},
            {"quantity": 2, "name": "potatoes, cubed"},
            {"quantity": 1, "name": "onion, sliced"},
            {"quantity": 2, "name": "tomatoes, chopped"},
            {"quantity": 1, "unit": "tbsp", "name": "ginger-garlic paste"},
            {"quantity": 1, "unit": "tsp", "name": "cumin seeds"},
            {"quantity": 1, "unit": "tsp", "name": "turmeric"},
            {"quantity": 1, "unit": "tsp", "name": "garam masala"},
            {"quantity": 1, "unit": "tsp", "name": "coriander powder"},
            {"name": "cilantro, lemon"},
        ],
        "steps": [
            "Bloom cumin seeds in oil. Add onion and ginger-garlic paste; cook until golden.",
            "Stir in tomatoes and dry spices; cook to a thick masala.",
            "Toss in potatoes; cover and cook 8 minutes.",
            "Add cauliflower; cover and cook 10 minutes more, stirring occasionally.",
            "Finish with garam masala, lemon, and cilantro.",
        ],
    },
    # ---- Italian ----
    {
        "title": "Spaghetti Carbonara",
        "description": "The real Roman version: eggs, pecorino, guanciale, pepper. No cream.",
        "cuisine": "italian", "language": "en", "spice_level": 0,
        "prep": 10, "cook": 15, "servings": 2, "image": _img("carbonara"),
        "tags": ["pasta", "weeknight", "classic"],
        "ingredients": [
            {"quantity": 200, "unit": "g", "name": "spaghetti"},
            {"quantity": 100, "unit": "g", "name": "guanciale, diced"},
            {"quantity": 2, "name": "egg yolks"},
            {"quantity": 1, "name": "whole egg"},
            {"quantity": 50, "unit": "g", "name": "pecorino romano, grated"},
            {"name": "freshly cracked black pepper"},
        ],
        "steps": [
            "Boil spaghetti to al dente in salted water.",
            "Render guanciale slowly in a cold pan until crisp.",
            "Whisk yolks, whole egg, and pecorino with plenty of pepper.",
            "Drain pasta, reserving a cup of pasta water.",
            "Off heat, toss pasta with guanciale, then with the egg mixture and pasta water until creamy.",
            "Serve immediately with more pecorino and pepper.",
        ],
    },
    {
        "title": "Aglio e Olio",
        "description": "Pantry pasta with garlic, chili, parsley, and excellent olive oil.",
        "cuisine": "italian", "language": "en", "spice_level": 1,
        "prep": 5, "cook": 12, "servings": 2, "image": _img("aglio-olio"),
        "tags": ["pasta", "weeknight", "vegetarian"],
        "ingredients": [
            {"quantity": 200, "unit": "g", "name": "spaghetti"},
            {"quantity": 60, "unit": "ml", "name": "extra virgin olive oil"},
            {"quantity": 6, "unit": "cloves", "name": "garlic, sliced thin"},
            {"quantity": 1, "unit": "tsp", "name": "red chili flakes"},
            {"quantity": 30, "unit": "g", "name": "parsley, chopped"},
            {"name": "salt, lemon zest"},
        ],
        "steps": [
            "Cook spaghetti to al dente in well-salted water.",
            "Warm olive oil with garlic and chili over low heat until just golden.",
            "Add a splash of pasta water; emulsify the sauce.",
            "Toss pasta in the pan; finish with parsley and lemon zest.",
        ],
    },
    {
        "title": "Margherita Pizza",
        "description": "Tomato, mozzarella, basil. The whole world in three ingredients.",
        "cuisine": "italian", "language": "en", "spice_level": 0,
        "prep": 90, "cook": 8, "servings": 2, "image": _img("margherita"),
        "tags": ["pizza", "weekend", "classic"],
        "ingredients": [
            {"quantity": 250, "unit": "g", "name": "00 flour"},
            {"quantity": 160, "unit": "ml", "name": "warm water"},
            {"quantity": 5, "unit": "g", "name": "salt"},
            {"quantity": 2, "unit": "g", "name": "instant yeast"},
            {"quantity": 200, "unit": "g", "name": "San Marzano tomatoes"},
            {"quantity": 150, "unit": "g", "name": "fresh mozzarella, torn"},
            {"name": "fresh basil, olive oil, salt"},
        ],
        "steps": [
            "Mix flour, water, salt, and yeast; knead to smooth. Rise 1 hour.",
            "Divide into 2 balls; rest 30 minutes.",
            "Preheat oven (with stone or steel) to maximum.",
            "Stretch each ball thin. Top with crushed tomatoes and salt.",
            "Bake until base just sets; add mozzarella and bake until bubbly.",
            "Finish with basil and olive oil.",
        ],
    },
    # ---- American / Western ----
    {
        "title": "Sheet-Pan Chicken with Vegetables",
        "description": "One tray, two heat zones, dinner in 35 minutes.",
        "cuisine": "american_western", "language": "en", "spice_level": 1,
        "prep": 10, "cook": 30, "servings": 4, "image": _img("sheet-pan-chicken"),
        "tags": ["weeknight", "one-pan", "gluten-free"],
        "ingredients": [
            {"quantity": 6, "name": "chicken thighs, bone-in"},
            {"quantity": 500, "unit": "g", "name": "baby potatoes, halved"},
            {"quantity": 1, "name": "red onion, wedged"},
            {"quantity": 200, "unit": "g", "name": "green beans"},
            {"quantity": 2, "unit": "tbsp", "name": "olive oil"},
            {"quantity": 1, "unit": "tbsp", "name": "smoked paprika"},
            {"quantity": 2, "unit": "tsp", "name": "garlic powder"},
            {"name": "salt, pepper, lemon"},
        ],
        "steps": [
            "Preheat oven to 220 C.",
            "Toss potatoes, onion, oil, paprika, garlic powder, salt and pepper on a sheet.",
            "Nestle chicken on top, skin-up. Roast 20 minutes.",
            "Add green beans; roast another 10 minutes until chicken is golden.",
            "Squeeze with lemon at the table.",
        ],
    },
    {
        "title": "Classic Cheeseburger",
        "description": "Smashed patty, melted American cheese, butter-toasted bun.",
        "cuisine": "american_western", "language": "en", "spice_level": 0,
        "prep": 10, "cook": 8, "servings": 2, "image": _img("cheeseburger"),
        "tags": ["burger", "weeknight", "comfort"],
        "ingredients": [
            {"quantity": 400, "unit": "g", "name": "ground beef (80/20)"},
            {"quantity": 2, "name": "soft brioche buns"},
            {"quantity": 4, "unit": "slices", "name": "American cheese"},
            {"quantity": 1, "name": "small onion, finely diced"},
            {"name": "yellow mustard, ketchup, dill pickles"},
            {"name": "butter, salt, pepper"},
        ],
        "steps": [
            "Form beef into 4 loose 100 g balls.",
            "Heat a heavy skillet ripping hot. Butter and toast buns; set aside.",
            "Place a beef ball in the pan, smash thin, season heavily, sear 90 seconds.",
            "Flip, lay onion on the patty, add cheese; cover briefly to melt.",
            "Stack 2 patties per bun with mustard, ketchup, and pickles.",
        ],
    },
    {
        "title": "Classic Chocolate Chip Cookies",
        "description": "Crispy edges, chewy center. The kind everyone fights over.",
        "cuisine": "american_western", "language": "en", "spice_level": 0,
        "prep": 15, "cook": 12, "servings": 24, "image": _img("choc-chip-cookies"),
        "tags": ["dessert", "baking", "kid-friendly"],
        "ingredients": [
            {"quantity": 225, "unit": "g", "name": "unsalted butter, softened"},
            {"quantity": 200, "unit": "g", "name": "brown sugar"},
            {"quantity": 100, "unit": "g", "name": "granulated sugar"},
            {"quantity": 2, "name": "eggs"},
            {"quantity": 1, "unit": "tsp", "name": "vanilla extract"},
            {"quantity": 300, "unit": "g", "name": "all-purpose flour"},
            {"quantity": 1, "unit": "tsp", "name": "baking soda"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 300, "unit": "g", "name": "dark chocolate chips"},
        ],
        "steps": [
            "Preheat oven to 180 C and line two baking sheets.",
            "Cream butter and sugars until fluffy.",
            "Beat in eggs one at a time, then vanilla.",
            "Whisk flour, baking soda, salt; fold into wet ingredients.",
            "Fold in chocolate chips. Scoop tablespoon balls.",
            "Bake 11-13 minutes until edges are golden, centers underdone.",
            "Cool on the sheet 5 minutes before transferring.",
        ],
    },
    # ---- Mexican ----
    {
        "title": "Chicken Tinga Tacos",
        "description": "Smoky chipotle-tomato shredded chicken on warm corn tortillas.",
        "cuisine": "mexican", "language": "en", "spice_level": 2,
        "prep": 10, "cook": 35, "servings": 4, "image": _img("chicken-tinga"),
        "tags": ["tacos", "weeknight", "spicy"],
        "ingredients": [
            {"quantity": 600, "unit": "g", "name": "chicken thighs, boneless"},
            {"quantity": 1, "name": "white onion, sliced"},
            {"quantity": 4, "unit": "cloves", "name": "garlic"},
            {"quantity": 4, "name": "Roma tomatoes"},
            {"quantity": 2, "name": "chipotle peppers in adobo"},
            {"quantity": 1, "unit": "tsp", "name": "oregano"},
            {"quantity": 1, "unit": "tsp", "name": "cumin"},
            {"quantity": 12, "name": "corn tortillas"},
            {"name": "cilantro, lime, queso fresco, onion to garnish"},
        ],
        "steps": [
            "Simmer chicken with half the onion, half the garlic, and salt 25 minutes; shred.",
            "Char tomatoes and remaining garlic under broiler.",
            "Blend tomatoes, garlic, chipotles, cumin, oregano, and a ladle of cooking liquid.",
            "Saute remaining onion in oil; pour in salsa, simmer 5 minutes.",
            "Add shredded chicken; cook until coated and saucy.",
            "Serve on warm tortillas with cilantro, onion, queso fresco, and lime.",
        ],
    },
    {
        "title": "Guacamole",
        "description": "Avocado, lime, onion, cilantro. The salsa bar standard.",
        "cuisine": "mexican", "language": "en", "spice_level": 1,
        "prep": 8, "cook": 0, "servings": 4, "image": _img("guacamole"),
        "tags": ["dip", "vegan", "gluten-free", "quick"],
        "ingredients": [
            {"quantity": 3, "name": "ripe avocados"},
            {"quantity": 1, "name": "lime, juiced"},
            {"quantity": 0.5, "name": "small white onion, diced"},
            {"quantity": 1, "name": "small tomato, diced"},
            {"quantity": 1, "name": "jalapeno, seeded and minced"},
            {"quantity": 1, "unit": "handful", "name": "cilantro, chopped"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
        ],
        "steps": [
            "Mash avocado roughly in a bowl.",
            "Stir in lime juice and salt.",
            "Fold in onion, tomato, jalapeno, and cilantro.",
            "Taste and adjust salt and lime. Serve with chips.",
        ],
    },
    {
        "title": "Carne Asada",
        "description": "Citrus-marinated grilled flank steak, sliced thin against the grain.",
        "cuisine": "mexican", "language": "en", "spice_level": 1,
        "prep": 90, "cook": 12, "servings": 4, "image": _img("carne-asada"),
        "tags": ["grill", "weekend", "high-protein"],
        "ingredients": [
            {"quantity": 700, "unit": "g", "name": "flank or skirt steak"},
            {"quantity": 1, "name": "orange, juiced"},
            {"quantity": 2, "name": "limes, juiced"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 1, "unit": "bunch", "name": "cilantro, chopped"},
            {"quantity": 1, "unit": "tsp", "name": "cumin"},
            {"quantity": 60, "unit": "ml", "name": "olive oil"},
            {"name": "salt, pepper"},
        ],
        "steps": [
            "Whisk juices, garlic, cumin, oil, salt, pepper, and most of the cilantro.",
            "Marinate steak 1-3 hours in the fridge.",
            "Grill very hot, 3-4 minutes per side for medium-rare.",
            "Rest 10 minutes; slice thinly across the grain.",
            "Top with remaining cilantro and a fresh lime squeeze.",
        ],
    },
]

