"""Curated seed recipes for the Explore tab (3 per cuisine, 27 total).

Image URLs go through LoremFlickr, which does a Flickr Creative Commons
keyword search per dish, so every card shows a photo of the *actual* dish
rather than a random stock image. Earlier attempts hard-coded Unsplash IDs
guessed by hand and frequently mis-matched (a deer for "Egg Drop Soup", a
museum for "Shan Noodles"). Search-by-keyword is far more accurate for the
long tail of regional dishes (Mohinga, Lahpet Thoke, Shan Noodles, etc.)
that don't have famous canonical Unsplash photos.
"""

import zlib
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
    # Optional per-locale title + description overrides. Shape:
    #
    #   {
    #     "my": {"title": "...", "description": "..."},
    #     "ko": {"title": "...", "description": "..."},
    #     ...
    #   }
    #
    # The seeder writes the dict verbatim into `spice_routes.translations`
    # (a JSONB column). The list / detail endpoints accept
    # `?translate_to=<locale>` and swap the matching entry onto the row
    # before serialising. Recipes without this key (or without an entry
    # for a particular locale) fall back to `title` / `description`
    # silently, so partial coverage is safe — start with the dishes the
    # PM wants localised first, fill in the rest later.
    translations: NotRequired[dict[str, dict[str, str]]]


# Slug -> comma-separated Flickr search keywords. The keywords are the
# dish name + a couple of disambiguating cuisine / preparation words so
# the Flickr CC pool returns an obvious match. Order matters slightly
# (Flickr weights early terms higher) so dish name comes first.
#
# Rules learned from probing the Flickr CC pool:
#   - Keep keywords SHORT (2-3 words max). LoremFlickr uses `/all` matching
#     so adding more terms makes a hit less likely. e.g. "tom,yum,goong,
#     shrimp,soup,thai" returned the default placeholder, but "tom,yum"
#     returns dozens of real photos.
#   - Use the dish's *common name* first, with a single cuisine/format
#     disambiguator second. Don't try to pile on ingredients.
_FLICKR_KEYWORDS_BY_SLUG: dict[str, str] = {
    # Korean
    "kimchi-jjigae": "kimchi,stew",
    "bibimbap": "bibimbap",
    "kfc-yangnyeom": "korean,chicken",
    # Japanese
    "tamago-donburi": "donburi",
    "miso-salmon": "salmon,miso",
    "cold-soba": "soba",
    # Chinese
    "mapo-tofu": "mapo,tofu",
    "egg-drop-soup": "soup,chinese",
    "beef-broccoli": "beef,broccoli",
    # Burmese
    "mohinga": "noodle,soup",
    "lahpet-thoke": "salad,asian",
    "shan-noodles": "noodles,bowl",
    # Thai
    "pad-krapow": "thai,basil",
    "tom-yum": "tom,yum",
    "som-tum": "papaya,salad",
    # Vietnamese
    "pho-bo": "pho,beef",
    "banh-mi-thit": "banh,mi,sandwich",
    "goi-cuon": "spring,roll,vietnamese",
    # Indian
    "tikka-masala": "tikka,masala",
    "dal-tadka": "dal,curry",
    "aloo-gobi": "aloo,gobi",
    # Italian
    "carbonara": "carbonara",
    "aglio-olio": "aglio,olio",
    "margherita": "margherita,pizza",
    # American / Western
    "sheet-pan-chicken": "roast,chicken",
    "cheeseburger": "cheeseburger",
    "choc-chip-cookies": "chocolate,cookies",
    # Mexican
    "chicken-tinga": "tinga,tacos",
    "guacamole": "guacamole",
    "carne-asada": "carne,asada",
    # French
    "coq-au-vin": "coq,vin",
    "ratatouille": "ratatouille",
    "quiche-lorraine": "quiche,lorraine",
}


# Hand-curated Wikimedia Commons URLs for every dish — one editorial-quality
# photo per recipe, all pulled from the dish's English Wikipedia article or
# the top Commons search result and verified by hand to actually depict the
# dish (not raw ingredients, not a tangentially related photo, not a deleted
# Flickr import).
#
# Wikimedia is rock-solid infrastructure: these URLs point at specific
# Commons files that have been on Wikipedia for years and won't 410 like
# Flickr does, won't rotate like LoremFlickr does, and don't depend on any
# rate-limited third-party API at runtime.
#
# Sized at 1280px because Wikimedia's thumbnail server only accepts a small
# whitelist of widths (1200px is rejected with HTTP 400). 1280 downscales
# cleanly to the 1200x800 cards.
_WIKIMEDIA_IMAGE_BY_SLUG: dict[str, str] = {
    # Korean
    "kimchi-jjigae": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Korean_stew_dish_-_Kimchi-jjigae_Kimchi_Stew_2019_%2801%29.jpg/1280px-Korean_stew_dish_-_Kimchi-jjigae_Kimchi_Stew_2019_%2801%29.jpg",
    "bibimbap": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Dolsot-bibimbap.jpg/1280px-Dolsot-bibimbap.jpg",
    "kfc-yangnyeom": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Iksan_City_48_Korean_Style_Fried_chicken.jpg/1280px-Iksan_City_48_Korean_Style_Fried_chicken.jpg",
    # Japanese
    "tamago-donburi": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Oyakodon_003.jpg/1280px-Oyakodon_003.jpg",
    "miso-salmon": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/Salmon_Saikyo-Yaki.jpg/1280px-Salmon_Saikyo-Yaki.jpg",
    "cold-soba": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Zaru_soba_by_spinachdip.jpg/1280px-Zaru_soba_by_spinachdip.jpg",
    # Chinese
    "mapo-tofu": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Chen_Mapo_Tofu.jpg/1280px-Chen_Mapo_Tofu.jpg",
    "egg-drop-soup": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/5-Minute_Egg_Drop_Soup-5_%2832079790121%29.jpg/1280px-5-Minute_Egg_Drop_Soup-5_%2832079790121%29.jpg",
    "beef-broccoli": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/58/Beef_and_broccoli_stir_fry.jpg/1280px-Beef_and_broccoli_stir_fry.jpg",
    # Burmese
    "mohinga": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Mohnga.jpg/1280px-Mohnga.jpg",
    "lahpet-thoke": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Laphet_thoke.JPG/1280px-Laphet_thoke.JPG",
    "shan-noodles": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Shan_Noodle.jpg/1280px-Shan_Noodle.jpg",
    # Thai
    "pad-krapow": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Basil_fried_crispy_pork_with_rice_-_Chiang_Mai_-_2017-07-11_%28002%29.jpg/1280px-Basil_fried_crispy_pork_with_rice_-_Chiang_Mai_-_2017-07-11_%28002%29.jpg",
    "tom-yum": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Tom_yam_kung_maenam.jpg/1280px-Tom_yam_kung_maenam.jpg",
    "som-tum": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/2013_Tam_Lao.jpg/1280px-2013_Tam_Lao.jpg",
    # Vietnamese
    "pho-bo": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Bowl_of_Meatball_pho.jpg/1280px-Bowl_of_Meatball_pho.jpg",
    "banh-mi-thit": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/B%C3%A1nh_m%C3%AC_th%E1%BB%8Bt_n%C6%B0%E1%BB%9Bng.png/1280px-B%C3%A1nh_m%C3%AC_th%E1%BB%8Bt_n%C6%B0%E1%BB%9Bng.png",
    "goi-cuon": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Homemade_spring_rolls_%287010969349%29.jpg/1280px-Homemade_spring_rolls_%287010969349%29.jpg",
    # Indian
    "tikka-masala": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/Chicken_tikka_masala_%28cropped%29.jpg/1280px-Chicken_tikka_masala_%28cropped%29.jpg",
    "dal-tadka": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Dal_Tadka-Delhi.jpg/1280px-Dal_Tadka-Delhi.jpg",
    "aloo-gobi": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Aloo_Ghobi.jpg/1280px-Aloo_Ghobi.jpg",
    # Italian
    "carbonara": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Espaguetis_carbonara.jpg/1280px-Espaguetis_carbonara.jpg",
    "aglio-olio": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Aglio_e_olio.jpg/1280px-Aglio_e_olio.jpg",
    "margherita": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Pizza_Margherita_stu_spivack.jpg/1280px-Pizza_Margherita_stu_spivack.jpg",
    # American / Western
    "sheet-pan-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Max%27s_Roasted_Chicken_-_Evan_Swigart.jpg/1280px-Max%27s_Roasted_Chicken_-_Evan_Swigart.jpg",
    "cheeseburger": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cheeseburger.jpg/1280px-Cheeseburger.jpg",
    "choc-chip-cookies": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Choco_chip_cookie.png/1280px-Choco_chip_cookie.png",
    # Mexican
    "chicken-tinga": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Tinga_de_pollo.JPG/1280px-Tinga_de_pollo.JPG",
    "guacamole": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Guacamole_IMGP1271.jpg/1280px-Guacamole_IMGP1271.jpg",
    "carne-asada": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d0/Carne_asada_%284472586086%29.jpg/1280px-Carne_asada_%284472586086%29.jpg",
    # French
    "coq-au-vin": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Coq_au_vin%2C_Linden.jpg/1280px-Coq_au_vin%2C_Linden.jpg",
    "ratatouille": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/03/Ratatouille-Dish.jpg/1280px-Ratatouille-Dish.jpg",
    "quiche-lorraine": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/Quiche_lorraine_01.JPG/1280px-Quiche_lorraine_01.JPG",
}


def _img(slug: str) -> str:
    """Build a stable, search-based food image URL for a recipe.

    - If a slug has an entry in `_WIKIMEDIA_IMAGE_BY_SLUG`, that URL is
      returned as-is. The seed script's resolver passes through any
      non-LoremFlickr URL unchanged, so this becomes the permanent URL.
    - Otherwise, use LoremFlickr keyword search. The seed script will
      resolve this to a permanent Flickr CDN URL.
    - `/all` forces *all* keywords to match -> much more accurate than
      the default OR-search.
    - `lock=<stable hash>` makes the returned photo deterministic so the
      same recipe always shows the same image (otherwise it'd shuffle on
      every page load and the card would feel unstable).
    - Generic "food,plated" fallback if a slug isn't registered.
    """
    if slug in _WIKIMEDIA_IMAGE_BY_SLUG:
        return _WIKIMEDIA_IMAGE_BY_SLUG[slug]
    keywords = _FLICKR_KEYWORDS_BY_SLUG.get(slug, "food,plated,dish")
    seed = zlib.crc32(slug.encode("utf-8")) % 99999
    return (
        "https://loremflickr.com/1200/800/"
        f"{keywords}/all?lock={seed}"
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
        "translations": {
            "zh": {
                "title": "泡菜汤",
                "description": "暖心发酵泡菜汤，配以五花肉和豆腐。",
            },
            "ja": {
                "title": "キムチチゲ",
                "description": "豚バラ肉と豆腐が入った、心温まる発酵キムチ鍋。",
            },
            "ko": {
                "title": "김치찌개",
                "description": "돼지고기와 두부를 넣고 끓인, 속을 든든하게 해주는 김치찌개.",
            },
            "vi": {
                "title": "Kimchi Jjigae",
                "description": "Món hầm kim chi lên men ấm lòng với thịt ba chỉ và đậu phụ.",
            },
            "my": {
                "description": "ဝက်သားတုံးနှင့် တို့ဟူးတို့ပါဝင်သော စိတ်ကျေနပ်စေသည့် က fermented kimchi စွပ်ပြုတ်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "石锅拌饭",
                "description": "石锅拌饭，配有调味蔬菜、牛肉和太阳蛋。",
            },
            "ja": {
                "title": "ビビンバ",
                "description": "野菜、牛肉、そして目玉焼きを混ぜていただくご飯ボウル。",
            },
            "ko": {
                "title": "비빔밥",
                "description": "각종 나물과 쇠고기, 계란 프라이를 비벼 먹는 밥.",
            },
            "vi": {
                "title": "Cơm trộn Bibimbap",
                "description": "Cơm trộn với rau củ nêm nếm, thịt bò và trứng ốp la lòng đào.",
            },
            "my": {
                "description": "ရော水饭，配有调味蔬菜、牛肉和太阳蛋。",
            },
        },
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
        "translations": {
            "zh": {
                "title": "亲子饭",
                "description": "米饭上铺着软嫩的蒸蛋，淋上甜咸的日式高汤酱汁。",
            },
            "ja": {
                "title": "親子丼",
                "description": "ご飯の上に、とろとろの卵と甘辛い出汁のあんがかかった親子丼。",
            },
            "ko": {
                "title": "오야코동",
                "description": "밥 위에 부드럽고 촉촉한 계란과 달콤짭짤한 다시 소스를 곁들인 요리.",
            },
            "vi": {
                "title": "Oyakodon",
                "description": "Trứng mềm mịn phủ trên cơm, rưới sốt dashi mặn ngọt.",
            },
            "my": {
                "description": "နူးညံ့သော ကြက်ဥကို ထမင်းပေါ်တွင် တင်ပြီး ချို-ငန်အရသာရှိသော ဒါရှီဆော့စ်ဖြင့် အုပ်ထားသည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "冷荞麦蘸汁",
                "description": "荞麦面冷食，搭配鲜美的日式蘸汁。",
            },
            "ja": {
                "title": "冷たいそばつゆ",
                "description": "冷たいそばを、風味豊かなつけつゆでお楽しみください。",
            },
            "ko": {
                "title": "차가운 소바와 쯔유",
                "description": "차가운 메밀국수를 감칠맛 나는 쯔유 소스에 찍어 드세요.",
            },
            "vi": {
                "title": "Mì Soba Lạnh Chấm Nước Sốt",
                "description": "Mì kiều mạch dùng lạnh với nước chấm tsuyu đậm đà hương vị.",
            },
            "my": {
                "description": "မြန်မာ့ရိုးရာဟင်းလျာများ",
            },
        },
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
        "translations": {
            "zh": {
                "title": "蛋花汤",
                "description": "丝滑的蛋花漂浮在清爽的姜味汤中。",
            },
            "ja": {
                "title": "卵スープ",
                "description": "生姜の香りがする澄んだスープに、とろりとした卵の帯。",
            },
            "ko": {
                "title": "계란탕",
                "description": "맑은 육수에 부드러운 계란이 흩뿌려진 수프.",
            },
            "vi": {
                "title": "Súp trứng",
                "description": "Những dải trứng mềm mượt trong nước dùng thanh tao thoang thoảng hương gừng.",
            },
            "my": {
                "description": "ကြက်ဥချောင်းများပါဝင်သော သန့်ရှင်းသော ဂျင်းအရသာဟင်းရည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "缅甸鱼汤米粉",
                "description": "缅甸国菜：用香茅鱼汤煮的米粉。",
            },
            "ja": {
                "title": "モヒンガ",
                "description": "ミャンマーの国民食：レモングラス風味の魚介スープと米麺。",
            },
            "ko": {
                "title": "모힝가",
                "description": "미얀마의 국민 요리: 레몬그라스 생선 육수에 쌀국수를 곁들인 요리.",
            },
            "vi": {
                "title": "Mohinga",
                "description": "Món ăn quốc hồn quốc túy của Myanmar: nước dùng cá nấu với sả, ăn cùng bún gạo.",
            },
            "my": {
                "description": "မြန်မာ့အမျိုးသားအစားအစာ- ကြာစင်နံ့သာ၊ ငါး၊ ဆန်ခေါက်ဆွဲ။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "缅甸茶叶沙拉",
                "description": "腌制茶叶，搭配酥脆的豆子、花生和青柠。",
            },
            "ja": {
                "title": "ミャンマー風茶葉サラダ",
                "description": "ピクルスにした茶葉に、カリカリの豆、ピーナッツ、ライムを添えて。",
            },
            "ko": {
                "title": "미얀마 차잎 샐러드",
                "description": "절인 찻잎에 바삭한 콩, 땅콩, 라임을 곁들인 샐러드입니다.",
            },
            "vi": {
                "title": "Salad lá trà kiểu Myanmar",
                "description": "Lá trà muối chua với đậu giòn, đậu phộng và chanh.",
            },
            "my": {
                "description": "လက်ဖက်စိမ်းကို ကြော်ထားသော ပဲများ၊ မြေပဲနှင့် သံပုရာသီးတို့ဖြင့် သုပ်ထားခြင်း။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "泰式打抛鸡",
                "description": "泰国街头经典：罗勒叶与辣椒炒鸡肉。",
            },
            "ja": {
                "title": "パッガパオガイ",
                "description": "タイの屋台料理の定番：ホーリーバジルと唐辛子で炒めた鶏肉。",
            },
            "ko": {
                "title": "팟 까파오 까이",
                "description": "태국 길거리 음식의 고전: 홀리 바질과 고추를 볶은 치킨.",
            },
            "vi": {
                "title": "Pad Krapow Gai",
                "description": "Món kinh điển của ẩm thực đường phố Thái Lan: gà xào lá húng quế và ớt.",
            },
            "my": {
                "description": "ထိုင်းနိုင်ငံ၏လမ်းဘေးအစားအစာများထဲမှ ရိုးရာဟင်းတစ်မျိုး။ ကြက်သားကို ပင်လယ်ဘေရွက်နှင့် ငရုတ်သီးတို့ဖြင့်ကြော်ထားသည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "青木瓜沙拉",
                "description": "Som tum：捣碎的青木瓜、青柠、鱼露、花生和辣椒。",
            },
            "ja": {
                "title": "グリーンパパイヤサラダ",
                "description": "ソムタム：青パパイヤ、ライム、ナンプラー、ピーナッツ、唐辛子を叩いて作るサラダ。",
            },
            "ko": {
                "title": "쏨땀",
                "description": "쏨땀: 으깬 파파야, 라임, 피시 소스, 땅콩, 고추를 넣어 만듭니다.",
            },
            "vi": {
                "title": "Gỏi đu đủ xanh",
                "description": "Gỏi đu đủ xanh (Som tum): Đu đủ xanh giã nhuyễn trộn với chanh, nước mắm, đậu phộng và ớt.",
            },
            "my": {
                "description": "Som tum: ငှက်ပျောသီးစိမ်း၊ သံပုရာသီး၊ ငါးငံပြာရည်၊ မြေပဲနှင့် ငရုတ်သီးတို့ကို ထောင်း၍ပြုလုပ်သော အသုပ်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "越南河粉牛肉汤",
                "description": "北越风味牛肉河粉汤，汤头清澈，香气四溢。",
            },
            "ja": {
                "title": "フォー・ボー",
                "description": "澄んだ香りの良いスープが特徴の、北部ベトナム風牛肉麺スープです。",
            },
            "ko": {
                "title": "퍼보",
                "description": "맑고 향긋한 국물이 특징인 북부 베트남식 소고기 쌀국수입니다.",
            },
            "vi": {
                "title": "Phở Bò",
                "description": "Món phở bò kiểu miền Bắc Việt Nam với nước dùng trong, thơm lừng.",
            },
            "my": {
                "description": "မြောက်ပိုင်းဗီယက်နမ်စတိုင် နွားသားငါးပိထမင်းဟင်းရည်၊ ပွင့်လင်းပြီးမွှေးကြိုင်သောဟင်းရည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "越南春卷",
                "description": "新鲜的越南夏卷，配有虾、猪肉、米粉和香草。",
            },
            "ja": {
                "title": "ゴイクン",
                "description": "エビ、豚肉、春雨、ハーブを使った、新鮮なベトナム風生春巻き。",
            },
            "ko": {
                "title": "고이꾸온",
                "description": "새우, 돼지고기, 쌀국수, 허브를 넣은 신선한 베트남식 월남쌈.",
            },
            "vi": {
                "title": "Gỏi cuốn",
                "description": "Cuốn tươi kiểu Việt Nam với tôm, thịt heo, bún và rau thơm.",
            },
            "my": {
                "description": "ကြက်ခြေထောက်၊ ဝက်သား၊ ဆန်ခေါက်ဆွဲနှင့် ဟင်းသီးဟင်းရွက်များဖြင့် ပြုလုပ်ထားသော လတ်ဆတ်သော ဗီယက်နမ် နွေရွက်လိပ်များ။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "印度扁豆扁豆",
                "description": "黄扁豆用孜然、大蒜和酥油调味。",
            },
            "ja": {
                "title": "ダル・タルカ",
                "description": "クミン、ニンニク、ギーで味付けした黄色いレンズ豆。",
            },
            "ko": {
                "title": "달 타드카",
                "description": "큐민, 마늘, 기버터로 양념한 노란 렌틸콩.",
            },
            "vi": {
                "title": "Dal Tadka",
                "description": "Đậu lăng vàng nấu với thì là, tỏi và bơ ghee.",
            },
            "my": {
                "description": "ဝက်သက်၊ ကြက်သွန်ဖြူနှင့် ghee တို့ဖြင့် အရသာထည့်ထားသော အဝါရောင် ပဲနီလေးများ။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "土豆花菜",
                "description": "干式烹制的土豆和花菜，搭配烤香的香料。",
            },
            "ja": {
                "title": "アルーゴビ",
                "description": "スパイスを炒めて風味をつけた、ドライスタイルのじゃがいもとカリフラワーの料理。",
            },
            "ko": {
                "title": "알루 고비",
                "description": "볶은 향신료로 맛을 낸 드라이 스타일의 감자와 콜리플라워 요리.",
            },
            "vi": {
                "title": "Aloo Gobi",
                "description": "Khoai tây và súp lơ kiểu khô với gia vị rang thơm.",
            },
            "my": {
                "description": "အာလူးနှင့် ပန်းဂေါ်ဖီတို့ကို မီးကင်ထားသော မွှေးကြိုင်သော ဟင်းခတ်အမွှေးအကြိုင်များဖြင့် အခြောက်ကြော်ထားခြင်း။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "冬阴功汤",
                "description": "香辣酸爽的鲜虾汤，融合了柠檬草、青柠叶和辣椒的独特风味。",
            },
            "ja": {
                "title": "トムヤムクン",
                "description": "レモングラス、ライムリーフ、唐辛子が効いた、スパイシーで酸味のあるエビのスープです。",
            },
            "ko": {
                "title": "똠얌꿍",
                "description": "레몬그라스, 라임 잎, 고추의 풍미가 어우러진 매콤하고 새콤한 새우 수프입니다.",
            },
            "vi": {
                "title": "Tom Yum Goong",
                "description": "Món súp tôm chua cay đậm đà với hương vị đặc trưng của sả, lá chanh và ớt.",
            },
            "my": {
                "description": "စပါးလင်၊ ရှောက်ရွက်နှင့် ငရုတ်သီးတို့ဖြင့် ချက်ပြုတ်ထားသည့် အချဉ်စပ် ပုစွန်ဟင်းရည်ဖြစ်သည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "青木瓜沙拉",
                "description": "泰式青木瓜沙拉：将青木瓜丝、青柠、鱼露和花生捣制而成，口感清爽，火辣过瘾。",
            },
            "ja": {
                "title": "ソムタム",
                "description": "ソムタム：青パパイヤ、ライム、ナンプラー、ピーナッツを叩いて和えた、刺激的な辛さが魅力の一皿。",
            },
            "ko": {
                "title": "솜땀",
                "description": "솜땀: 덜 익은 파파야, 라임, 피시 소스, 땅콩을 절구에 찧어 만든 강렬하고 매콤한 태국식 샐러드입니다.",
            },
            "vi": {
                "title": "Gỏi đu đủ",
                "description": "Som tum: đu đủ xanh giã cùng chanh, nước mắm, đậu phộng, mang đến hương vị cay nồng đầy kích thích.",
            },
            "my": {
                "description": "Som tum: မရင့်သေးသော သင်္ဘောသီး၊ သံပရာသီး၊ ငါးငံပြာရည်နှင့် မြေပဲတို့ကို ထောင်း၍ ပြုလုပ်ထားသော စပ်ရှရှ ထိုင်းသုပ်တစ်မျိုး။",
            },
        },
    },
    # ---- Vietnamese ----
    {
        "title": "Pho Bo",
        "description": "Northern-style Vietnamese beef noodle soup with a clear, fragrant broth.",
        "cuisine": "vietnamese", "language": "en", "spice_level": 1,
        "prep": 20, "cook": 180, "servings": 4, "image": _img("pho-bo"),
        "tags": ["soup", "noodles", "comfort"],
        "ingredients": [
            {"quantity": 1.5, "unit": "kg", "name": "beef bones (knuckle + marrow)"},
            {"quantity": 400, "unit": "g", "name": "beef brisket"},
            {"quantity": 250, "unit": "g", "name": "thinly sliced raw beef sirloin"},
            {"quantity": 1, "name": "large onion, halved and charred"},
            {"quantity": 50, "unit": "g", "name": "ginger, halved and charred"},
            {"quantity": 4, "name": "star anise"},
            {"quantity": 1, "name": "cinnamon stick"},
            {"quantity": 3, "name": "cloves"},
            {"quantity": 1, "unit": "tbsp", "name": "coriander seeds"},
            {"quantity": 3, "unit": "tbsp", "name": "fish sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "rock sugar"},
            {"quantity": 400, "unit": "g", "name": "banh pho rice noodles"},
            {"name": "Thai basil, bean sprouts, lime wedges, sliced chilies, hoisin and sriracha to serve"},
        ],
        "steps": [
            "Blanch beef bones and brisket for 5 minutes; drain and rinse to clear the broth.",
            "Char onion and ginger over an open flame until blackened in spots.",
            "Toast star anise, cinnamon, cloves, and coriander in a dry pan until fragrant; tie in a spice bag.",
            "Add bones, brisket, charred aromatics, and spice bag to a stockpot with 4L water. Simmer 2.5-3 hours, skimming scum.",
            "Remove brisket after 90 minutes, cool, and slice thinly. Strain broth; season with fish sauce and rock sugar.",
            "Soak and cook rice noodles per package; divide between bowls. Top with sliced brisket and raw sirloin.",
            "Ladle boiling broth over to cook the raw beef. Serve with herbs, sprouts, lime, chilies, and condiments.",
        ],
        "translations": {
            "zh": {
                "title": "越南牛肉河粉",
                "description": "源自北越的经典牛肉河粉，汤底清澈鲜美，香气四溢。",
            },
            "ja": {
                "title": "フォー・ボー",
                "description": "澄んだ香り高いスープが特徴の、北ベトナム風牛肉の米麺料理です。",
            },
            "ko": {
                "title": "퍼 보",
                "description": "맑고 향긋한 육수가 일품인 북부 스타일의 베트남식 소고기 쌀국수입니다.",
            },
            "vi": {
                "title": "Phở Bò",
                "description": "Món phở bò kiểu miền Bắc với nước dùng trong thanh, thơm nồng đặc trưng.",
            },
            "my": {
                "description": "ကြည်လင်ပြီး မွှေးကြိုင်သော ဟင်းရည်နှင့် မြောက်ပိုင်းစတိုင် ဗီယက်နမ် အမဲသားခေါက်ဆွဲပြုတ် ဖြစ်သည်။",
            },
        },
    },
    {
        "title": "Banh Mi Thit Nuong",
        "description": "Grilled lemongrass pork in a crackly baguette with pickled vegetables and herbs.",
        "cuisine": "vietnamese", "language": "en", "spice_level": 1,
        "prep": 25, "cook": 15, "servings": 4, "image": _img("banh-mi-thit"),
        "tags": ["sandwich", "lunch", "weeknight"],
        "ingredients": [
            {"quantity": 500, "unit": "g", "name": "pork shoulder, thinly sliced"},
            {"quantity": 2, "unit": "stalks", "name": "lemongrass, finely minced"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 1, "unit": "tbsp", "name": "fish sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "brown sugar"},
            {"quantity": 1, "unit": "tbsp", "name": "vegetable oil"},
            {"quantity": 4, "name": "Vietnamese baguettes (banh mi)"},
            {"quantity": 1, "name": "small carrot, julienned"},
            {"quantity": 1, "name": "small daikon, julienned"},
            {"quantity": 60, "unit": "ml", "name": "rice vinegar"},
            {"quantity": 1, "unit": "tsp", "name": "sugar (for pickle)"},
            {"name": "cucumber spears, cilantro, sliced jalapeno, pate (optional), mayo"},
        ],
        "steps": [
            "Quick-pickle carrot and daikon in rice vinegar, sugar, and a pinch of salt for at least 20 minutes.",
            "Mix pork with lemongrass, garlic, fish sauce, soy sauce, brown sugar, and oil. Marinate 20 minutes.",
            "Sear pork in a hot pan or grill in batches until caramelized on the edges, 2-3 minutes per side.",
            "Split baguettes lengthwise (without cutting through). Toast briefly until crackly.",
            "Spread mayo (and pate if using) inside. Layer cucumber, pickled vegetables, pork, jalapeno, and cilantro.",
            "Press the baguette closed and serve immediately.",
        ],
        "translations": {
            "zh": {
                "title": "越式烤肉法包",
                "description": "香茅烤猪肉搭配酥脆法棍，佐以酸甜腌菜与新鲜香草，风味十足。",
            },
            "ja": {
                "title": "バインミー・ティット・ヌオン",
                "description": "レモングラス香る焼き豚を、パリッとしたバゲットに挟みました。甘酸っぱいなますと新鮮なハーブが絶妙なハーモニーを奏でます。",
            },
            "ko": {
                "title": "반미 팃 느엉",
                "description": "레몬그라스 향이 밴 돼지고기 구이를 바삭한 바게트에 담았습니다. 아삭한 절임 채소와 향긋한 허브가 어우러진 베트남식 샌드위치입니다.",
            },
            "vi": {
                "title": "Bánh Mì Thịt Nướng",
                "description": "Thịt heo nướng sả thơm lừng trong ổ bánh mì giòn rụm, kết hợp cùng đồ chua và các loại rau thơm tươi mát.",
            },
            "my": {
                "description": "မွှေးပျံ့သော စပါးလင်ဖြင့်ကင်ထားသည့် ဝက်သားကို ကြွပ်ရွသော ပေါင်မုန့်ကြားတွင် အချဉ်စိမ်ထားသော ဟင်းသီးဟင်းရွက်များ၊ လတ်ဆတ်သည့် ဟင်းခတ်အမွှေးအကြိုင်များနှင့်အတူ တွဲဖက်စားသုံးရသည့် အရသာရှိသော အစားအစာဖြစ်သည်။",
            },
        },
    },
    {
        "title": "Goi Cuon",
        "description": "Fresh Vietnamese summer rolls with shrimp, pork, vermicelli, and herbs.",
        "cuisine": "vietnamese", "language": "en", "spice_level": 0,
        "prep": 35, "cook": 15, "servings": 4, "image": _img("goi-cuon"),
        "tags": ["appetizer", "fresh", "light"],
        "ingredients": [
            {"quantity": 12, "name": "round rice paper wrappers (22cm)"},
            {"quantity": 16, "name": "medium shrimp, peeled and deveined"},
            {"quantity": 200, "unit": "g", "name": "pork belly or shoulder"},
            {"quantity": 100, "unit": "g", "name": "rice vermicelli noodles"},
            {"quantity": 1, "name": "head butter lettuce, leaves separated"},
            {"name": "fresh mint, Thai basil, cilantro, garlic chives"},
            {"quantity": 3, "unit": "tbsp", "name": "hoisin sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "peanut butter"},
            {"quantity": 2, "unit": "tbsp", "name": "warm water"},
            {"quantity": 1, "unit": "tbsp", "name": "crushed roasted peanuts"},
        ],
        "steps": [
            "Simmer pork in salted water with a piece of ginger until tender, 25 minutes. Cool and slice thinly.",
            "Poach shrimp in the same liquid for 90 seconds until just pink. Slice each in half lengthwise.",
            "Soak vermicelli in boiling water 3-4 minutes, drain, and rinse under cold water.",
            "Dip one rice paper in warm water for 5 seconds until pliable; lay flat on a damp board.",
            "On the lower third, place lettuce, vermicelli, herbs, pork; on the upper third (face-down) line up 2 shrimp halves.",
            "Fold in the sides, roll up tightly so the shrimp shows through the top.",
            "Whisk hoisin, peanut butter, and warm water for the dipping sauce; top with crushed peanuts.",
        ],
        "translations": {
            "zh": {
                "title": "越南春卷",
                "description": "清爽的越南夏卷，内含鲜虾、猪肉、米粉和新鲜香草。",
            },
            "ja": {
                "title": "ゴイクオン",
                "description": "海老、豚肉、米粉、ハーブをライスペーパーで巻いた、さっぱりとしたベトナム風生春巻きです。",
            },
            "ko": {
                "title": "고이꾸온",
                "description": "새우, 돼지고기, 쌀국수, 신선한 허브를 넣은 깔끔하고 담백한 베트남식 월남쌈입니다.",
            },
            "vi": {
                "title": "Gỏi cuốn",
                "description": "Món cuốn tươi mát với tôm, thịt heo, bún và các loại rau thơm đặc trưng của Việt Nam.",
            },
            "my": {
                "description": "ပုစွန်၊ ဝက်သား၊ ဆန်ခေါက်ဆွဲနှင့် ဟင်းခတ်အမွှေးအကြိုင်များပါဝင်သည့် လတ်ဆတ်သော ဗီယက်နမ်စတိုင် နွေဦးလိပ်များဖြစ်သည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "印式咖喱烤鸡",
                "description": "餐厅风味：鲜嫩的腌制鸡肉，浸润在浓郁香醇的番茄酱汁中。",
            },
            "ja": {
                "title": "チキンティッカマサラ",
                "description": "レストランの味をご家庭で。スパイスでマリネした鶏肉を、クリーミーなトマトソースで煮込みました。",
            },
            "ko": {
                "title": "치킨 티카 마살라",
                "description": "레스토랑 스타일의 요리입니다. 향신료에 재운 닭고기를 크리미한 토마토 소스에 끓여내 깊은 풍미를 자랑합니다.",
            },
            "vi": {
                "title": "Gà Tikka Masala",
                "description": "Hương vị nhà hàng: gà ướp gia vị đậm đà trong nước sốt cà chua kem béo ngậy.",
            },
            "my": {
                "description": "စားသောက်ဆိုင်အရသာအတိုင်း - ဟင်းခတ်အမွှေးအကြိုင်များဖြင့် နယ်ထားသော ကြက်သားကို ခရင်မ်ဆန်သည့် ခရမ်းချဉ်သီးဆော့စ်ဖြင့် ချက်ပြုတ်ထားခြင်းဖြစ်သည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "黄豆咖喱",
                "description": "用孜然、大蒜和酥油烹调而成的黄扁豆汤，香气四溢。",
            },
            "ja": {
                "title": "ダールタルカ",
                "description": "クミン、ニンニク、ギーで風味付けした、黄色いレンズ豆のカレーです。",
            },
            "ko": {
                "title": "달 타르카",
                "description": "커민, 마늘, 기(ghee)로 향을 낸 고소하고 부드러운 노란 렌틸콩 요리입니다.",
            },
            "vi": {
                "title": "Dal Tadka",
                "description": "Món đậu lăng vàng được nấu cùng thì là, tỏi và bơ ghee thơm lừng.",
            },
            "my": {
                "description": "ဇီယာ၊ ကြက်သွန်ဖြူနှင့် ထောပတ် (ghee) တို့ဖြင့် အနှစ်ချက်ထားသော ပဲဝါဟင်းရည်ဖြစ်သည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "土豆花菜咖喱",
                "description": "一道干炒风味的土豆花菜，融合了香气四溢的烘焙香料。",
            },
            "ja": {
                "title": "アル・ゴビ",
                "description": "香ばしいスパイスで炒めた、ホクホクのジャガイモとカリフラワーのドライカレーです。",
            },
            "ko": {
                "title": "알루 고비",
                "description": "향긋하게 볶아낸 향신료와 감자, 콜리플라워가 어우러진 담백한 인도식 볶음 요리입니다.",
            },
            "vi": {
                "title": "Aloo Gobi",
                "description": "Món khoai tây và súp lơ xào khô đậm đà hương vị các loại gia vị rang thơm lừng.",
            },
            "my": {
                "description": "အာလူးနှင့် ပန်းဂေါ်ဖီကို အမွှေးအကြိုင်များဖြင့် လှော်ခတ်ထားသည့် အရသာရှိသော ဟင်းလျာတစ်မျိုးဖြစ်သည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "意式培根蛋酱面",
                "description": "正宗罗马风味：鸡蛋、佩科里诺干酪、风干猪脸肉与黑胡椒的完美融合，绝不添加奶油。",
            },
            "ja": {
                "title": "スパゲッティ・カルボナーラ",
                "description": "ローマの伝統的なレシピ。卵、ペコリーノ・ロマーノ、グアンチャーレ、黒胡椒のみを使用。生クリームは使いません。",
            },
            "ko": {
                "title": "스파게티 카르보나라",
                "description": "로마 정통 방식 그대로. 달걀, 페코리노 치즈, 관찰레, 후추만으로 맛을 냅니다. 생크림은 넣지 않습니다.",
            },
            "vi": {
                "title": "Mì Ý Carbonara",
                "description": "Hương vị chuẩn Rome: trứng, phô mai pecorino, thịt má heo guanciale và tiêu. Tuyệt đối không dùng kem tươi.",
            },
            "my": {
                "description": "ရောမမြို့တော်၏ စစ်မှန်သောအရသာ။ ကြက်ဥ၊ ပီကိုရီနိုဒိန်ခဲ၊ ဝက်ပါးစပ်သား (guanciale) နှင့် ငရုတ်ကောင်းတို့ဖြင့် ပြုလုပ်ထားပြီး နို့ခရင်မ် လုံးဝမပါဝင်ပါ။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "蒜香橄榄油意面",
                "description": "利用家中常备食材制作的意面，融合了蒜香、微辣与优质橄榄油的纯粹风味。",
            },
            "ja": {
                "title": "アーリオ・オーリオ",
                "description": "ニンニク、唐辛子、パセリ、そして上質なオリーブオイルを使った、パントリーにある食材で手軽に作れるパスタです。",
            },
            "ko": {
                "title": "알리오 올리오",
                "description": "마늘, 페페론치노, 파슬리, 그리고 좋은 올리브 오일만 있으면 완성되는 간단하고 맛있는 파스타입니다.",
            },
            "vi": {
                "title": "Mì Ý Aglio e Olio",
                "description": "Món mì Ý đơn giản với tỏi, ớt, ngò tây và dầu ô liu thượng hạng, tận dụng những nguyên liệu sẵn có trong bếp.",
            },
            "my": {
                "description": "မီးဖိုချောင်ထဲမှာ အမြဲရှိတတ်တဲ့ ကြက်သွန်ဖြူ၊ ငရုတ်သီး၊ နံနံပင်နဲ့ အရည်အသွေးကောင်းမွန်တဲ့ သံလွင်ဆီတို့ဖြင့် ပြုလုပ်ထားတဲ့ ခေါက်ဆွဲဟင်းလျာလေးပါ။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "玛格丽特披萨",
                "description": "番茄、马苏里拉奶酪与罗勒。三种食材，尽显世界风味。",
            },
            "ja": {
                "title": "マルゲリータピザ",
                "description": "トマト、モッツァレラ、バジル。たった3つの食材で表現する、世界のおいしさ。",
            },
            "ko": {
                "title": "마르게리타 피자",
                "description": "토마토, 모짜렐라, 바질. 세 가지 재료로 완성한 세상의 맛.",
            },
            "vi": {
                "title": "Pizza Margherita",
                "description": "Cà chua, phô mai mozzarella và húng quế. Cả thế giới gói gọn trong ba nguyên liệu.",
            },
            "my": {
                "description": "ခရမ်းချဉ်သီး၊ မိုဇာရဲလားဒိန်ခဲနှင့် ပင်စိမ်းတို့ဖြင့် ပြုလုပ်ထားသည်။ ပါဝင်ပစ္စည်း သုံးမျိုးတည်းဖြင့် ကမ္ဘာ့အရသာကို ခံစားလိုက်ပါ။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "烤盘鸡肉配时蔬",
                "description": "一个烤盘，两种火候，35分钟搞定晚餐。",
            },
            "ja": {
                "title": "チキンと野菜のシートパンロースト",
                "description": "天板ひとつで、焼き分けも簡単。35分で完成する夕食レシピ。",
            },
            "ko": {
                "title": "시트팬 치킨과 채소 구이",
                "description": "팬 하나로 두 가지 온도를 활용해 35분 만에 완성하는 저녁 식사.",
            },
            "vi": {
                "title": "Gà nướng khay cùng rau củ",
                "description": "Một khay nướng, hai vùng nhiệt, bữa tối sẵn sàng trong 35 phút.",
            },
            "my": {
                "description": "ဗန်းတစ်လုံး၊ အပူချိန်နှစ်မျိုး၊ ညစာအတွက် မိနစ် ၃၀ ကျော်ဆိုရင်ပဲ အဆင်သင့်ဖြစ်ပါပြီ။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "经典芝士汉堡",
                "description": "焦香肉饼，搭配融化的美式芝士，以及黄油烘烤过的汉堡胚。",
            },
            "ja": {
                "title": "クラシックチーズバーガー",
                "description": "スマッシュしたパティに、とろけるアメリカンチーズとバターでトーストしたバンズを合わせました。",
            },
            "ko": {
                "title": "클래식 치즈버거",
                "description": "바삭하게 구운 패티와 녹아내린 아메리칸 치즈, 버터에 구운 번의 조화가 일품입니다.",
            },
            "vi": {
                "title": "Bánh mì kẹp phô mai cổ điển",
                "description": "Thịt bò ép vỉ nướng xém cạnh, phô mai Mỹ tan chảy, kẹp trong vỏ bánh mì nướng bơ thơm lừng.",
            },
            "my": {
                "description": "အသားပြားကို ပြားအောင်ဖိကင်ထားပြီး အရည်ပျော်နေသော အမေရိကန်ချိစ်နှင့် ထောပတ်သုတ်၍ ကင်ထားသော ပေါင်မုန့်တို့ဖြင့် ပြုလုပ်ထားသည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "经典巧克力豆曲奇",
                "description": "边缘酥脆，中心软糯。人人都抢着吃的美味。",
            },
            "ja": {
                "title": "クラシック・チョコチップクッキー",
                "description": "縁はサクサク、中はしっとり。誰もが夢中になる美味しさです。",
            },
            "ko": {
                "title": "클래식 초콜릿 칩 쿠키",
                "description": "가장자리는 바삭하고 속은 쫀득합니다. 누구나 탐내는 최고의 맛이죠.",
            },
            "vi": {
                "title": "Bánh quy sô-cô-la chip cổ điển",
                "description": "Viền bánh giòn tan, nhân bánh mềm dẻo. Món bánh ai cũng muốn giành phần.",
            },
            "my": {
                "description": "အနားသားกรอบပြီး အလယ်သားက နူးညံ့ပါတယ်။ လူတိုင်း အလုအယက် စားချင်လောက်တဲ့ အရသာမျိုးပါ။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "墨西哥烟熏鸡肉塔可",
                "description": "烟熏风味的墨西哥辣椒番茄手撕鸡肉，搭配温热的玉米饼。",
            },
            "ja": {
                "title": "チキンティンガタコス",
                "description": "スモーキーなチポトレトマトソースで煮込んだほぐし鶏肉を、温かいトルティーヤで包みました。",
            },
            "ko": {
                "title": "치킨 팅가 타코",
                "description": "훈연 향 가득한 치폴레 토마토 소스에 버무린 닭고기를 따뜻한 옥수수 토르티야에 얹어 즐겨보세요.",
            },
            "vi": {
                "title": "Bánh Tacos Gà Tinga",
                "description": "Thịt gà xé sốt cà chua chipotle đậm đà hương khói, dùng kèm bánh ngô ấm nóng.",
            },
            "my": {
                "description": "မီးခိုးငွေ့ရနံ့သင်းသော ချီပိုတယ်ခရမ်းချဉ်သီးဆော့စ်ဖြင့် နယ်ထားသည့် ကြက်သားအမျှင်များကို ပူနွေးသော ပြောင်းဖူးမုန့်ပြားဖြင့် တွဲဖက်စားသုံးနိုင်ပါသည်။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "鳄梨酱",
                "description": "鳄梨、青柠、洋葱和香菜。莎莎酱吧的经典标配。",
            },
            "ja": {
                "title": "ワカモレ",
                "description": "アボカド、ライム、玉ねぎ、パクチー。サルサバーの定番メニューです。",
            },
            "ko": {
                "title": "과카몰리",
                "description": "아보카도, 라임, 양파, 고수가 어우러진 살사 바의 필수 메뉴입니다.",
            },
            "vi": {
                "title": "Guacamole",
                "description": "Bơ, chanh, hành tây và ngò rí. Món sốt không thể thiếu tại các quầy salsa.",
            },
            "my": {
                "description": "ထောပတ်သီး၊ သံပရာသီး၊ ကြက်သွန်နီနှင့် နံနံပင်တို့ဖြင့် ပြုလုပ်ထားသော ဆာဆာဘား၏ အဓိကဟင်းလျာ။",
            },
        },
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
        "translations": {
            "zh": {
                "title": "墨西哥烤牛肉",
                "description": "柑橘腌制的烤侧腹牛排，逆着纹理切成薄片，鲜嫩多汁。",
            },
            "ja": {
                "title": "カルネ・アサダ",
                "description": "柑橘類でマリネした牛ハラミをグリルし、繊維に沿って薄くスライスしたメキシコ料理です。",
            },
            "ko": {
                "title": "카르네 아사다",
                "description": "감귤류에 재워 구운 소고기 플랭크 스테이크를 결 반대 방향으로 얇게 썰어낸 요리입니다.",
            },
            "vi": {
                "title": "Carne Asada",
                "description": "Thịt bò thăn được ướp với sốt cam chanh rồi nướng chín, thái lát mỏng ngược thớ thịt để giữ độ mềm.",
            },
            "my": {
                "description": "သံပရာသီးအရည်ဖြင့် နယ်ထားသော အမဲသားကို ကင်ပြီးနောက် အသားမျှင်အတိုင်း ပါးပါးလှီးထားသည့် အရသာရှိသော ဟင်းလျာ။",
            },
        },
    },
    # ---- French ----
    {
        "title": "Coq au Vin",
        "description": "Burgundy classic: chicken braised in red wine with bacon, mushrooms, and pearl onions.",
        "cuisine": "french", "language": "en", "spice_level": 0,
        "prep": 25, "cook": 75, "servings": 4, "image": _img("coq-au-vin"),
        "tags": ["braise", "weekend", "comfort"],
        # Burmese intentionally omits "title" so the card falls back to
        # "Coq au Vin" — there's no settled Burmese transliteration of
        # the dish, and the eyebrow ("ပြင်သစ်" / French) already
        # communicates the cuisine context.
        "translations": {
            "zh": {
                "title": "红酒炖鸡",
                "description": "勃艮第经典：以红酒慢炖鸡肉，搭配培根、蘑菇与珍珠洋葱。",
            },
            "ja": {
                "title": "コック・オー・ヴァン",
                "description": "ブルゴーニュ地方の定番、鶏肉を赤ワインで煮込み、ベーコン・マッシュルーム・パールオニオンを添えた一皿。",
            },
            "ko": {
                "title": "코코뱅",
                "description": "부르고뉴 클래식: 닭고기를 레드와인에 졸이고 베이컨, 버섯, 진주양파를 곁들인 요리.",
            },
            "vi": {
                "title": "Gà hầm rượu vang Coq au Vin",
                "description": "Món cổ điển vùng Bourgogne: gà hầm rượu vang đỏ với thịt xông khói, nấm và hành ngọc trai.",
            },
            "my": {
                "description": "ဘာဂန်ဒီနယ်မှ ဂန္ထဝင်ဟင်း — ကြက်သားကို ဝိုင်နီ၊ ဝက်ပေါင်ခြောက်၊ မှို နှင့် ပုလဲကြက်သွန်နီများဖြင့် ပြုတ်ထားသည်။",
            },
        },
        "ingredients": [
            {"quantity": 1.5, "unit": "kg", "name": "chicken pieces, bone-in"},
            {"quantity": 150, "unit": "g", "name": "smoked bacon lardons"},
            {"quantity": 250, "unit": "g", "name": "button mushrooms, quartered"},
            {"quantity": 200, "unit": "g", "name": "pearl onions, peeled"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, smashed"},
            {"quantity": 1, "unit": "bottle", "name": "dry red Burgundy"},
            {"quantity": 250, "unit": "ml", "name": "chicken stock"},
            {"quantity": 2, "unit": "tbsp", "name": "tomato paste"},
            {"quantity": 2, "unit": "tbsp", "name": "flour"},
            {"quantity": 2, "unit": "tbsp", "name": "butter"},
            {"quantity": 1, "unit": "bouquet", "name": "garni (thyme, bay, parsley stems)"},
            {"name": "salt, pepper, chopped parsley"},
        ],
        "steps": [
            "Season chicken with salt and pepper. Render bacon in a Dutch oven until crisp; set aside.",
            "Brown chicken in the bacon fat on all sides, in batches. Remove and reserve.",
            "Add pearl onions and mushrooms; brown lightly. Set aside.",
            "Stir in tomato paste and garlic; cook 1 minute. Dust with flour and stir.",
            "Pour in wine and stock, scraping up the fond. Return chicken and bacon, add bouquet garni.",
            "Cover and simmer gently 45 minutes until chicken is tender.",
            "Add mushrooms and pearl onions; simmer 15 minutes more.",
            "Discard bouquet garni. Stir in butter to finish the sauce. Top with parsley.",
        ],
    },
    {
        "title": "Ratatouille",
        "description": "Provencal stew of summer vegetables, gently coaxed into silky harmony.",
        "cuisine": "french", "language": "en", "spice_level": 0,
        "prep": 20, "cook": 60, "servings": 6, "image": _img("ratatouille"),
        "tags": ["stew", "summer", "vegetarian"],
        "translations": {
            "zh": {
                "title": "普罗旺斯炖菜",
                "description": "普罗旺斯夏季蔬菜慢炖菜，将番茄、茄子、西葫芦温柔地融合在一起。",
            },
            "ja": {
                "title": "ラタトゥイユ",
                "description": "プロヴァンスの夏野菜をじっくり煮込み、なめらかなハーモニーに仕上げた郷土料理。",
            },
            "ko": {
                "title": "라타투이",
                "description": "프로방스 여름 채소를 천천히 졸여 매끄럽게 어우러지게 한 시골풍 스튜.",
            },
            "vi": {
                "title": "Rau củ hầm Ratatouille",
                "description": "Món hầm rau củ mùa hè kiểu Provence, nấu chậm để các vị quyện vào nhau mượt mà.",
            },
            "my": {
                "description": "ပရိုဗန့်စ်ဒေသမှ နွေရာသီဟင်းသီးဟင်းရွက်များကို ပျော့ပျောင်းသွားသည်အထိ ဖြည်းညှင်းစွာ ပြုတ်ထားသော ဒေသိယဟင်း။",
            },
        },
        "ingredients": [
            {"quantity": 1, "name": "large eggplant, cubed"},
            {"quantity": 2, "name": "zucchini, cubed"},
            {"quantity": 1, "name": "red bell pepper, cubed"},
            {"quantity": 1, "name": "yellow bell pepper, cubed"},
            {"quantity": 4, "name": "ripe tomatoes, peeled and chopped"},
            {"quantity": 1, "name": "large onion, diced"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, sliced"},
            {"quantity": 3, "unit": "tbsp", "name": "extra virgin olive oil"},
            {"quantity": 1, "unit": "tsp", "name": "herbes de Provence"},
            {"quantity": 1, "name": "bay leaf"},
            {"name": "fresh basil, salt, pepper"},
        ],
        "steps": [
            "Salt the eggplant for 15 minutes; pat dry to draw out bitterness.",
            "In a wide pot, sweat onion in olive oil until translucent.",
            "Brown each vegetable separately in batches in more olive oil, then return all to the pot.",
            "Add garlic, herbes de Provence, bay leaf, salt, and pepper.",
            "Stir in tomatoes; cover and simmer gently 40-50 minutes until everything has melted together.",
            "Rest off heat 10 minutes. Discard bay; tear basil over the top. Serve warm or at room temperature.",
        ],
    },
    {
        "title": "Quiche Lorraine",
        "description": "Buttery shortcrust filled with bacon, eggs, and cream in the Lorraine tradition.",
        "cuisine": "french", "language": "en", "spice_level": 0,
        "prep": 30, "cook": 45, "servings": 6, "image": _img("quiche-lorraine"),
        "tags": ["baking", "brunch", "classic"],
        "translations": {
            "zh": {
                "title": "洛林咸派",
                "description": "黄油酥皮包裹培根、鸡蛋与奶油，遵循洛林地区的经典做法。",
            },
            "ja": {
                "title": "キッシュ・ロレーヌ",
                "description": "バターたっぷりのショートクラストに、ベーコン・卵・生クリームを詰めた、ロレーヌ地方の伝統的な一品。",
            },
            "ko": {
                "title": "키슈 로렌",
                "description": "버터 향 가득한 쇼트크러스트에 베이컨, 달걀, 크림을 채워 구운 로렌 지방의 전통 요리.",
            },
            "vi": {
                "title": "Bánh Quiche Lorraine",
                "description": "Vỏ bánh giòn bơ thơm phức, nhân thịt xông khói, trứng và kem béo theo công thức truyền thống vùng Lorraine.",
            },
            "my": {
                "description": "လော်ရိန်းနယ်ပြင်သစ်ဓလေ့အရ ထောပတ်ပါသော အခွံပါးပါးထဲမှာ ဝက်ပေါင်ခြောက်၊ ဥ၊ နှင့် ခရင်မ်တို့ ဖြည့်ထားသည်။",
            },
        },
        "ingredients": [
            {"quantity": 250, "unit": "g", "name": "all-purpose flour"},
            {"quantity": 125, "unit": "g", "name": "cold unsalted butter, cubed"},
            {"quantity": 1, "name": "egg yolk (for the crust)"},
            {"quantity": 3, "unit": "tbsp", "name": "ice water"},
            {"quantity": 200, "unit": "g", "name": "smoked bacon lardons"},
            {"quantity": 4, "name": "large eggs"},
            {"quantity": 250, "unit": "ml", "name": "heavy cream"},
            {"quantity": 150, "unit": "ml", "name": "whole milk"},
            {"quantity": 0.25, "unit": "tsp", "name": "nutmeg, freshly grated"},
            {"name": "salt, pepper"},
        ],
        "steps": [
            "Rub butter into flour and a pinch of salt until sandy. Mix in yolk and ice water; bring together without overworking.",
            "Wrap and chill the dough 30 minutes.",
            "Roll out and line a 24cm tart tin. Prick the base; chill 15 minutes.",
            "Blind-bake at 190 C with baking weights for 15 minutes, then 5 minutes uncovered until pale gold.",
            "Render bacon in a dry pan until lightly crisp; drain on paper towel.",
            "Whisk eggs, cream, milk, nutmeg, salt, and pepper.",
            "Scatter bacon in the crust; pour over the custard.",
            "Bake at 180 C for 30-35 minutes until just set with a slight wobble in the center. Rest 10 minutes before slicing.",
        ],
    },
]

