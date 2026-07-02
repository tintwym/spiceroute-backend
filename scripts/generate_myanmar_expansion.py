"""One-shot generator for v7 Myanmar regional cuisine expansion.

Run: uv run python -m scripts.generate_myanmar_expansion
Writes: scripts/cuisine_expansion_v7_myanmar.py

Adds 20 regional / ethnic Myanmar cuisines (3 recipes each) alongside
the existing national `burmese` umbrella — 60 new curated recipes.
"""

from __future__ import annotations

from pathlib import Path


def _seed_cuisine(wire: str) -> str:
    """Store the regional wire (shan, yangon, …) — not the burmese umbrella."""
    return wire

# (wire, slug, title, description, spice, tags, ingredients, steps)
_DISHES: list[tuple] = [
    # shan
    ("shan", "shan-khauk-swe", "Shan Khauk Swe", "Tomato-garlic rice noodles with ground pork and pickled mustard.", 1,
     ["noodles", "pork", "classic"],
     ["rice noodles", "ground pork", "tomato", "garlic", "pickled mustard", "peanuts"],
     ["Fry garlic and tomato into a thick sauce.", "Brown pork; simmer with stock.", "Toss cooked noodles in sauce.", "Top with peanuts and mustard greens.", "Serve immediately."]),
    ("shan", "shan-tofu-nway", "Shan Tofu Nway", "Silky chickpea tofu in warm savory gravy over rice noodles.", 0,
     ["noodles", "tofu", "comfort"],
     ["chickpea flour", "rice noodles", "turmeric", "ginger", "shallot oil", "chili flakes"],
     ["Cook chickpea batter into soft tofu.", "Warm noodles in shallow broth.", "Slice tofu over noodles.", "Drizzle shallot oil and chili.", "Serve warm."]),
    ("shan", "hinny-paw", "Hinny Paw", "Shan-style sticky rice cakes with sesame and palm sugar.", 0,
     ["snack", "rice", "festival"],
     ["glutinous rice flour", "palm sugar", "sesame", "coconut", "banana leaf"],
     ["Mix rice flour with sugar syrup.", "Fold in sesame and coconut.", "Wrap in banana leaves.", "Steam 25 minutes.", "Cool slightly before serving."]),
    # rakhine
    ("rakhine", "rakhine-mont-di", "Rakhine Mont Di", "Fish-turmeric noodle soup with crisp shallots and chili oil.", 2,
     ["noodles", "fish", "classic"],
     ["rice noodles", "mackerel", "turmeric", "shallots", "chili oil", "lemongrass"],
     ["Poach fish; flake meat.", "Simmer turmeric broth with lemongrass.", "Cook noodles separately.", "Assemble bowls with fish and noodles.", "Top with fried shallots and chili oil."]),
    ("rakhine", "rakhine-fish-curry", "Rakhine Fish Curry", "Coastal curry with dried chilies and ngapi shrimp paste.", 2,
     ["curry", "fish", "coastal"],
     ["white fish", "ngapi", "dried chilies", "garlic", "turmeric", "oil"],
     ["Marinate fish with turmeric.", "Fry chili-garlic paste.", "Simmer fish in ngapi sauce.", "Reduce until glossy.", "Serve with rice."]),
    ("rakhine", "bamboo-shoot-fish", "Bamboo Shoot with Fish", "Tender bamboo shoots braised with river fish and herbs.", 1,
     ["stew", "fish", "comfort"],
     ["bamboo shoots", "catfish", "garlic", "turmeric", "coriander", "stock"],
     ["Parboil bamboo to remove bitterness.", "Brown fish lightly.", "Simmer bamboo and fish in stock.", "Finish with fresh coriander.", "Serve with steamed rice."]),
    # mon
    ("mon", "mon-curry", "Mon Curry", "Mild coconut curry with aromatics from lower Myanmar.", 1,
     ["curry", "chicken", "classic"],
     ["chicken", "coconut milk", "onion", "garlic", "ginger", "Mon curry paste"],
     ["Bloom curry paste in oil.", "Brown chicken pieces.", "Add coconut milk; simmer 35 min.", "Adjust salt and palm sugar.", "Serve with rice."]),
    ("mon", "htamane-mon", "Mon Htamane", "Festival sticky rice with coconut, peanuts, and sesame.", 0,
     ["rice", "festival", "sweet"],
     ["glutinous rice", "coconut milk", "peanuts", "sesame", "ginger", "palm sugar"],
     ["Soak rice overnight.", "Cook with coconut and sugar.", "Stir vigorously as it thickens.", "Fold in peanuts and sesame.", "Serve warm from the pot."]),
    ("mon", "ngapi-dip", "Mon Fermented Fish Dip", "Pungent ngapi relish with chilies and lime for vegetables.", 2,
     ["dip", "fermented", "side"],
     ["ngapi", "dried chilies", "garlic", "lime", "oil", "raw vegetables"],
     ["Pound ngapi with chilies and garlic.", "Fry paste until fragrant.", "Cool; brighten with lime.", "Serve with raw veg.", "Eat family-style."]),
    # kachin
    ("kachin", "kachin-rice", "Kachin Style Htamin", "Herbed rice steamed with ginger and wild pepper leaf.", 1,
     ["rice", "aromatic", "classic"],
     ["jasmine rice", "ginger", "wild pepper leaf", "garlic", "salt", "oil"],
     ["Rinse rice until water runs clear.", "Sauté ginger and garlic.", "Steam rice with herbs.", "Rest 10 minutes.", "Fluff and serve."]),
    ("kachin", "kachin-singju", "Kachin Singju", "Tangy salad with fermented bamboo and roasted chickpea powder.", 1,
     ["salad", "vegetarian", "fresh"],
     ["fermented bamboo", "cabbage", "roasted chickpea powder", "chili", "lime", "coriander"],
     ["Shred cabbage finely.", "Toss with fermented bamboo.", "Add chickpea powder and chili.", "Dress with lime.", "Serve immediately."]),
    ("kachin", "bamboo-soup-kachin", "Kachin Bamboo Shoot Soup", "Light broth with young bamboo and smoked pork.", 1,
     ["soup", "pork", "comfort"],
     ["young bamboo", "smoked pork", "ginger", "garlic", "stock", "scallion"],
     ["Simmer smoked pork in stock.", "Add bamboo shoots.", "Season with ginger and garlic.", "Garnish with scallion.", "Serve hot."]),
    # kayin
    ("kayin", "kayin-sour-soup", "Kayin Sour Soup", "Tamarind-sour soup with greens and smoked fish.", 1,
     ["soup", "sour", "classic"],
     ["tamarind", "smoked fish", "morning glory", "garlic", "chili", "stock"],
     ["Dissolve tamarind in warm stock.", "Simmer smoked fish.", "Add greens at the end.", "Season with garlic and chili.", "Serve with rice."]),
    ("kayin", "kayin-bamboo-curry", "Kayin Bamboo Curry", "Rich curry of bamboo shoots and pork belly.", 2,
     ["curry", "pork", "comfort"],
     ["bamboo shoots", "pork belly", "onion", "turmeric", "chili paste", "oil"],
     ["Render pork belly slowly.", "Add chili paste and turmeric.", "Simmer bamboo until tender.", "Reduce sauce.", "Serve with rice."]),
    ("kayin", "fermented-pork-kayin", "Kayin Fermented Pork", "Sour fermented pork salad with herbs and chili.", 2,
     ["salad", "pork", "fermented"],
     ["fermented pork", "shallots", "chili", "lime leaves", "coriander", "rice"],
     ["Slice fermented pork thin.", "Toss with shallots and chili.", "Add herbs and lime.", "Serve with warm rice.", "Eat immediately."]),
    # chin
    ("chin", "chin-baum", "Chin Baum", "Corn rice porridge with leafy greens and smoked meat.", 0,
     ["rice", "corn", "comfort"],
     ["ground corn", "rice", "smoked meat", "mustard greens", "salt", "water"],
     ["Simmer corn and rice into porridge.", "Shred smoked meat.", "Blanch greens.", "Assemble bowls.", "Serve steaming."]),
    ("chin", "chin-smoked-meat", "Chin Smoked Meat", "Hill-country smoked pork with chili salt.", 1,
     ["pork", "smoked", "classic"],
     ["pork shoulder", "salt", "chili flakes", "ginger", "garlic", "smoking chips"],
     ["Cure pork with salt and spices.", "Smoke low 4 hours.", "Rest and slice.", "Serve with chili salt.", "Pair with rice."]),
    ("chin", "chin-bamboo-stew", "Chin Bamboo Stew", "Hearty stew of bamboo, beans, and smoked beef.", 1,
     ["stew", "beef", "comfort"],
     ["bamboo shoots", "smoked beef", "black beans", "onion", "garlic", "stock"],
     ["Brown smoked beef.", "Add bamboo and beans.", "Simmer 90 minutes.", "Adjust seasoning.", "Serve with rice."]),
    # kayah
    ("kayah", "kayah-pork-rice", "Kayah Pork and Rice", "Turmeric rice cooked with pork and Kayah spices.", 1,
     ["rice", "pork", "classic"],
     ["jasmine rice", "pork", "turmeric", "garlic", "Kayah spice mix", "oil"],
     ["Marinate pork with spices.", "Sauté garlic and turmeric.", "Cook rice with pork and stock.", "Steam until fluffy.", "Rest before serving."]),
    ("kayah", "kayah-sour-leaf", "Kayah Sour Leaf Soup", "Soup of sour roselle leaves with fish and herbs.", 1,
     ["soup", "sour", "comfort"],
     ["roselle leaves", "fish", "tomato", "garlic", "chili", "stock"],
     ["Simmer roselle leaves in stock.", "Add fish pieces.", "Finish with tomato and chili.", "Garnish with herbs.", "Serve hot."]),
    ("kayah", "kayah-tomato-salad", "Kayah Tomato Salad", "Pounded tomato salad with peanuts and sesame.", 1,
     ["salad", "vegetarian", "fresh"],
     ["ripe tomatoes", "peanuts", "sesame", "chili", "lime", "coriander"],
     ["Pound tomatoes lightly.", "Toast peanuts and sesame.", "Toss with chili and lime.", "Top with coriander.", "Serve as side."]),
    # mandalay
    ("mandalay", "mee-shay", "Mandalay Mee Shay", "Rice noodle soup with pork, garlic oil, and pickled greens.", 1,
     ["noodles", "pork", "classic"],
     ["rice noodles", "pork", "garlic oil", "pickled mustard", "soy", "stock"],
     ["Simmer pork in spiced stock.", "Cook noodles.", "Assemble bowls.", "Top with garlic oil and pickles.", "Serve immediately."]),
    ("mandalay", "mandalay-tea-leaf", "Mandalay Tea Leaf Salad", "Royal-city laphet thoke with crunchy mix-ins.", 1,
     ["salad", "fermented", "classic"],
     ["fermented tea leaves", "fried garlic", "peanuts", "sesame", "tomato", "cabbage"],
     ["Mix tea leaves with aromatics.", "Toast peanuts and sesame.", "Toss with shredded cabbage.", "Add tomato and fried garlic.", "Serve family-style."]),
    ("mandalay", "mandalay-beef-curry", "Mandalay Beef Curry", "Slow-braised beef with star anise and onion.", 2,
     ["curry", "beef", "comfort"],
     ["beef chuck", "onion", "star anise", "turmeric", "garlic", "oil"],
     ["Brown beef in batches.", "Caramelize onions.", "Braise with spices 2 hours.", "Reduce gravy.", "Serve with rice."]),
    # yangon
    ("yangon", "yangon-mohinga", "Yangon Mohinga", "Street-style fish noodle soup with crisp fritters.", 2,
     ["noodles", "fish", "street food"],
     ["rice noodles", "catfish", "rice flour", "turmeric", "banana stem", "crispy fritters"],
     ["Make fish broth with turmeric.", "Whisk rice flour slurry to thicken.", "Cook noodles.", "Assemble with banana stem.", "Top with fritters and lime."]),
    ("yangon", "samosa-thoke", "Yangon Samosa Thoke", "Chopped samosa salad with chickpea curry and herbs.", 2,
     ["salad", "street food", "snack"],
     ["samosa", "chickpea curry", "cabbage", "mint", "lime", "chili"],
     ["Fry samosas crisp.", "Chop and toss with cabbage.", "Spoon warm chickpea curry.", "Finish with mint and lime.", "Serve immediately."]),
    ("yangon", "tea-shop-eggs", "Tea Shop Eggs", "Soft-boiled eggs with soy-pepper dip from corner tea stalls.", 0,
     ["eggs", "breakfast", "street food"],
     ["eggs", "soy sauce", "pepper", "chili oil", "scallion", "toast"],
     ["Soft-boil eggs 6 minutes.", "Make soy-pepper dip.", "Peel and halve eggs.", "Drizzle chili oil.", "Serve with toast."]),
    # ayeyarwady
    ("ayeyarwady", "delta-fish-curry", "Delta Fish Curry", "Irrawaddy Delta fish curry with tamarind and herbs.", 1,
     ["curry", "fish", "classic"],
     ["river fish", "tamarind", "turmeric", "garlic", "cilantro", "oil"],
     ["Marinate fish with turmeric.", "Fry aromatics.", "Simmer in tamarind sauce.", "Garnish with cilantro.", "Serve with rice."]),
    ("ayeyarwady", "river-prawn-soup", "River Prawn Soup", "Sweet prawn broth with morning glory and lime.", 1,
     ["soup", "seafood", "comfort"],
     ["river prawns", "morning glory", "lime", "garlic", "ginger", "stock"],
     ["Shell prawns; reserve heads for stock.", "Simmer broth with aromatics.", "Poach prawns briefly.", "Add greens at end.", "Serve with lime."]),
    ("ayeyarwady", "tamarind-fish", "Ayeyarwady Tamarind Fish", "Whole fish glazed with delta tamarind and palm sugar.", 1,
     ["fish", "sweet-sour", "classic"],
     ["whole fish", "tamarind paste", "palm sugar", "garlic", "chili", "oil"],
     ["Fry fish until golden.", "Reduce tamarind and sugar glaze.", "Coat fish in glaze.", "Garnish with chili.", "Serve with rice."]),
    # tanintharyi
    ("tanintharyi", "southern-sour-curry", "Southern Myanmar Sour Curry", "Peninsula sour curry with green mango and seafood.", 2,
     ["curry", "seafood", "sour"],
     ["fish or prawns", "green mango", "turmeric", "chili", "ngapi", "oil"],
     ["Make sour base with green mango.", "Add seafood and simmer.", "Season with ngapi.", "Finish with fresh chili.", "Serve with rice."]),
    ("tanintharyi", "coastal-crab-curry", "Coastal Crab Curry", "Spiced crab curry from the Tanintharyi coast.", 2,
     ["curry", "crab", "coastal"],
     ["mud crab", "turmeric", "garlic", "dried chilies", "coconut milk", "lemongrass"],
     ["Clean and crack crab.", "Fry chili-turmeric paste.", "Simmer crab in coconut milk.", "Reduce until thick.", "Serve immediately."]),
    ("tanintharyi", "dawei-noodles", "Dawei Noodles", "Southern coastal noodles with fish cake and peanut.", 1,
     ["noodles", "fish", "street food"],
     ["rice noodles", "fish cake", "peanuts", "garlic oil", "lime", "stock"],
     ["Simmer fish cake in broth.", "Cook noodles.", "Toss with garlic oil.", "Top with peanuts and lime.", "Serve hot."]),
    # intha
    ("intha", "intha-htamin-jin", "Inle Htamin Jin", "Inle fermented rice cake with tomato and sesame.", 1,
     ["rice", "fermented", "classic"],
     ["cooked rice", "tomato", "sesame", "peanuts", "garlic", "chili"],
     ["Ferment rice lightly overnight.", "Pan-fry cakes until crisp.", "Top with tomato-chili relish.", "Garnish with sesame.", "Serve warm."]),
    ("intha", "intha-tomato-salad", "Inle Tomato Salad", "Lake-region tomato salad with roasted peanuts.", 0,
     ["salad", "vegetarian", "fresh"],
     ["ripe tomatoes", "peanuts", "sesame", "lime", "chili", "shallots"],
     ["Slice tomatoes thick.", "Toast peanuts.", "Dress with lime and chili.", "Garnish with shallots.", "Serve chilled."]),
    ("intha", "intha-fish-curry", "Inle Fish Curry", "Mild tomato fish curry from floating gardens.", 1,
     ["curry", "fish", "comfort"],
     ["Inle carp", "tomato", "turmeric", "garlic", "onion", "oil"],
     ["Fry fish lightly.", "Cook tomato-onion base.", "Simmer fish in sauce.", "Rest flavors 5 minutes.", "Serve with rice."]),
    # naga
    ("naga", "naga-smoked-pork", "Naga Smoked Pork", "Smoky hill pork with king chili and herbs.", 3,
     ["pork", "smoked", "spicy"],
     ["pork belly", "king chili", "ginger", "garlic", "salt", "smoking wood"],
     ["Salt pork overnight.", "Smoke over low heat.", "Char chili and pound.", "Toss pork with chili paste.", "Serve with rice."]),
    ("naga", "naga-bamboo", "Naga Bamboo Shoot Stew", "Fiery bamboo stew with smoked meat and herbs.", 3,
     ["stew", "bamboo", "spicy"],
     ["bamboo shoots", "smoked meat", "king chili", "ginger", "garlic", "stock"],
     ["Parboil bamboo.", "Simmer smoked meat in stock.", "Add chili and bamboo.", "Cook until tender.", "Serve hot."]),
    ("naga", "naga-chili-chutney", "Naga King Chili Chutney", "Incendiary chutney of king chilies and fermented soy.", 3,
     ["condiment", "spicy", "fermented"],
     ["king chilies", "fermented soy", "garlic", "salt", "lime", "oil"],
     ["Roast chilies.", "Pound with fermented soy.", "Fry briefly in oil.", "Cool and jar.", "Use sparingly."]),
    # pa_o
    ("pa_o", "pao-htamin-jin", "Pa'O Htamin Jin", "Pa'O fermented rice cakes with garlic and chili.", 1,
     ["rice", "fermented", "classic"],
     ["cooked rice", "garlic", "chili", "sesame", "oil", "salt"],
     ["Shape rice into patties.", "Pan-fry until crisp.", "Top with fried garlic.", "Add chili oil.", "Serve warm."]),
    ("pa_o", "pao-shan-tofu", "Pa'O Shan Tofu", "Chickpea tofu salad with herbs from Pa'O hills.", 0,
     ["salad", "tofu", "vegetarian"],
     ["chickpea tofu", "coriander", "lime", "chili", "shallot oil", "peanuts"],
     ["Slice tofu thick.", "Dress with lime and chili.", "Top with herbs and peanuts.", "Drizzle shallot oil.", "Serve fresh."]),
    ("pa_o", "pao-sour-mustard", "Pa'O Sour Mustard", "Pickled mustard greens stir-fried with pork.", 1,
     ["stir-fry", "pork", "pickled"],
     ["pickled mustard", "pork", "garlic", "chili", "oil", "soy"],
     ["Rinse pickled mustard.", "Stir-fry pork and garlic.", "Add mustard and chili.", "Toss over high heat.", "Serve with rice."]),
    # danu
    ("danu", "danu-fermented-tea", "Danu Fermented Tea Rice", "Danu celebratory rice mixed with laphet and nuts.", 1,
     ["rice", "fermented", "festival"],
     ["steamed rice", "fermented tea leaves", "peanuts", "sesame", "fried garlic", "oil"],
     ["Cool rice slightly.", "Fold in tea leaves and nuts.", "Season with salt.", "Garnish with fried garlic.", "Serve at room temperature."]),
    ("danu", "danu-pork-curry", "Danu Pork Curry", "Mountain pork curry with turmeric and ginger.", 2,
     ["curry", "pork", "comfort"],
     ["pork", "turmeric", "ginger", "garlic", "chili paste", "oil"],
     ["Brown pork.", "Add chili paste and turmeric.", "Simmer until tender.", "Reduce sauce.", "Serve with rice."]),
    ("danu", "danu-chicken", "Danu Rice Wine Chicken", "Chicken braised with homemade rice wine aromatics.", 1,
     ["chicken", "braised", "classic"],
     ["chicken", "rice wine", "ginger", "garlic", "soy", "scallion"],
     ["Marinate chicken in wine.", "Braise with ginger 40 min.", "Reduce liquid.", "Garnish with scallion.", "Serve with rice."]),
    # wa
    ("wa", "wa-grilled-meat", "Wa Grilled Meat", "Char-grilled marinated meat with wild herbs.", 2,
     ["grill", "beef", "classic"],
     ["beef", "wild herbs", "chili", "garlic", "salt", "lime"],
     ["Marinate beef with herbs.", "Grill over high heat.", "Rest and slice.", "Serve with lime and chili.", "Eat with sticky rice."]),
    ("wa", "wa-chili-paste", "Wa Chili Paste", "Bold chili paste with fermented beans and herbs.", 3,
     ["condiment", "spicy", "fermented"],
     ["dried chilies", "fermented beans", "garlic", "salt", "herbs", "oil"],
     ["Toast chilies.", "Pound with beans and garlic.", "Fry in oil.", "Cool before serving.", "Use as dip."]),
    ("wa", "wa-rice", "Wa Sticky Rice", "Steamed sticky rice served with grilled meats and herbs.", 0,
     ["rice", "side", "classic"],
     ["glutinous rice", "salt", "banana leaf", "herbs"],
     ["Soak rice 4 hours.", "Steam in banana leaf.", "Fluff with salt.", "Serve with meats.", "Eat with hands."]),
    # magway
    ("magway", "peanut-curry", "Dry Zone Peanut Curry", "Central Myanmar peanut curry with chicken.", 1,
     ["curry", "chicken", "peanut"],
     ["chicken", "peanuts", "turmeric", "onion", "garlic", "oil"],
     ["Grind peanuts to paste.", "Brown chicken.", "Simmer in peanut sauce.", "Reduce until thick.", "Serve with rice."]),
    ("magway", "sesame-chicken", "Magway Sesame Chicken", "Pan-roasted chicken coated in toasted sesame.", 1,
     ["chicken", "roast", "classic"],
     ["chicken thighs", "sesame", "turmeric", "garlic", "soy", "oil"],
     ["Marinate chicken.", "Pan-roast until golden.", "Coat with toasted sesame.", "Rest briefly.", "Serve with rice."]),
    ("magway", "bean-soup-magway", "Magway Bean Soup", "Hearty bean soup from the dry zone.", 0,
     ["soup", "beans", "comfort"],
     ["yellow beans", "onion", "turmeric", "garlic", "ginger", "stock"],
     ["Soak beans overnight.", "Simmer with aromatics.", "Mash partially for body.", "Season to taste.", "Serve hot."]),
    # bago
    ("bago", "fish-paste-curry", "Bago Fish Paste Curry", "Pungent ngapi curry with pork and vegetables.", 2,
     ["curry", "pork", "fermented"],
     ["pork", "ngapi", "eggplant", "turmeric", "chili", "oil"],
     ["Fry ngapi paste.", "Brown pork.", "Add eggplant; simmer.", "Finish with chili.", "Serve with rice."]),
    ("bago", "palm-sugar-dessert", "Bago Palm Sugar Moh", "Palm-sugar rice pudding with coconut.", 0,
     ["dessert", "sweet", "classic"],
     ["glutinous rice", "palm sugar", "coconut milk", "salt", "banana leaf"],
     ["Cook rice in coconut milk.", "Stir in palm sugar.", "Steam until set.", "Cool in banana leaf cups.", "Serve warm or chilled."]),
    ("bago", "tamarind-leaves", "Bago Tamarind Leaf Curry", "Sour curry of young tamarind leaves and fish.", 1,
     ["curry", "fish", "sour"],
     ["young tamarind leaves", "fish", "turmeric", "garlic", "chili", "oil"],
     ["Blanch tamarind leaves.", "Fry fish with turmeric.", "Simmer leaves in light gravy.", "Adjust sourness.", "Serve with rice."]),
    # sagaing
    ("sagaing", "monastic-curry", "Sagaing Monastic Curry", "Mild vegetable curry from monastery kitchens.", 0,
     ["curry", "vegetarian", "comfort"],
     ["mixed vegetables", "turmeric", "ginger", "garlic", "coconut milk", "oil"],
     ["Sauté aromatics.", "Add vegetables in order of cook time.", "Simmer in coconut milk.", "Keep flavors gentle.", "Serve with rice."]),
    ("sagaing", "moringa-soup", "Sagaing Moringa Soup", "Light soup of moringa leaves and lentils.", 0,
     ["soup", "vegetarian", "healthy"],
     ["moringa leaves", "red lentils", "turmeric", "garlic", "onion", "stock"],
     ["Cook lentils until soft.", "Add moringa briefly.", "Season with turmeric.", "Serve hot.", "Garnish with fried garlic."]),
    ("sagaing", "bean-fritters", "Sagaing Bean Fritters", "Crisp split-pea fritters sold at pagoda fairs.", 0,
     ["fried", "snack", "street food"],
     ["split peas", "onion", "turmeric", "chili", "oil", "salt"],
     ["Soak peas; grind coarse.", "Mix with onion and spices.", "Drop spoonfuls into hot oil.", "Fry until golden.", "Drain and serve."]),
    # taunggyi
    ("taunggyi", "taunggyi-khauk-swe", "Taunggyi Khauk Swe", "Shan capital noodles with tomato pork sauce.", 1,
     ["noodles", "pork", "classic"],
     ["rice noodles", "ground pork", "tomato", "garlic", "mustard greens", "oil"],
     ["Cook tomato-pork sauce.", "Boil noodles.", "Toss noodles in sauce.", "Top with greens.", "Serve immediately."]),
    ("taunggyi", "shan-khao-suey", "Taunggyi Shan Khao Suey", "Curried coconut noodle soup with crispy toppings.", 2,
     ["noodles", "coconut", "comfort"],
     ["egg noodles", "coconut milk", "curry powder", "chicken", "crispy noodles", "lime"],
     ["Simmer coconut curry broth.", "Cook chicken and noodles.", "Assemble bowls.", "Top with crispy noodles.", "Serve with lime."]),
    ("taunggyi", "pickled-tea-snack", "Taunggyi Pickled Tea Mix", "Snack mix of laphet, nuts, and fried garlic.", 1,
     ["snack", "fermented", "classic"],
     ["fermented tea", "peanuts", "sesame", "fried garlic", "dried shrimp", "chili"],
     ["Mix tea leaves with nuts.", "Toast sesame.", "Fold in fried garlic.", "Season with chili.", "Serve as snack."]),
]


def _fmt_ingredients(raw: list[str]) -> str:
    return ",\n".join(f'            {{"name": "{item}"}}' for item in raw)


def _fmt_steps(steps: list[str]) -> str:
    escaped = [s.replace('"', '\\"') for s in steps]
    return ",\n".join(f'            "{s}"' for s in escaped)


def _esc(s: str) -> str:
    return s.replace('"', '\\"')


def main() -> None:
    out = Path(__file__).parent / "cuisine_expansion_v7_myanmar.py"
    chunks = [
        '"""v7 Myanmar regional expansion — 20 cuisines × 3 recipes (60 total).',
        "",
        "Auto-generated by `generate_myanmar_expansion.py`.",
        '"""',
        "",
        "from scripts.curated_data import RecipeSpec, _img",
        "",
        "MYANMAR_EXPANSION_RECIPES: list[RecipeSpec] = [",
    ]
    for row in _DISHES:
        cuisine, slug, title, desc, spice, tags, ings, steps = row
        tag_str = ", ".join(f'"{t}"' for t in tags)
        chunks.append("    {")
        chunks.append(f'        "title": "{_esc(title)}",')
        chunks.append(f'        "description": "{_esc(desc)}",')
        chunks.append(
            f'        "cuisine": "{_seed_cuisine(cuisine)}", '
            f'"language": "en", "spice_level": {spice},'
        )
        chunks.append(f'        "prep": 15, "cook": 25, "servings": 4, "image": _img("{slug}"),')
        chunks.append(f'        "tags": [{tag_str}],')
        chunks.append('        "ingredients": [')
        chunks.append(_fmt_ingredients(ings))
        chunks.append("        ],")
        chunks.append('        "steps": [')
        chunks.append(_fmt_steps(steps))
        chunks.append("        ],")
        chunks.append("    },")
    chunks.append("]")
    chunks.append("")
    out.write_text("\n".join(chunks))
    print(f"Wrote {len(_DISHES)} recipes to {out}")


if __name__ == "__main__":
    main()
