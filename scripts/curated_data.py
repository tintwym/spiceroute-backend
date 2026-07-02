"""Curated seed recipes for the Explore tab (3 per cuisine).

Card images use permanent Wikimedia URLs where hand-curated, otherwise
deterministic Unsplash CDN photos (`scripts/recipe_images.py`).
"""

from typing import NotRequired, TypedDict

from scripts.recipe_images import stable_food_image_url


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
    # Optional per-recipe difficulty override. When unset the seed script
    # auto-computes via `app.models.difficulty.compute_difficulty()` from
    # `prep + cook + len(steps)`. Pin this field explicitly when the
    # auto-rule gives a counterintuitive answer — typically
    # technique-heavy recipes whose short clock undersells them (e.g.
    # Baklava, where the auto-rule says MEDIUM but the user-facing
    # rules call out "highly technical pastry" as HARD).
    difficulty: NotRequired[str]
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
    # ---- v4 Phase 1 expansion ----
    # Lebanese
    "hummus": "hummus",
    "tabbouleh": "tabbouleh",
    "kibbeh-bil-sanieh": "kibbeh",
    # Turkish
    "adana-kebab": "adana,kebab",
    "lahmacun": "lahmacun",
    "baklava": "baklava",
    # Moroccan
    "chicken-tagine": "tagine,chicken",
    "lamb-couscous": "couscous,lamb",
    "harira": "harira",
    # Ethiopian
    "doro-wat": "doro,wat",
    "misir-wat": "misir,wat",
    "injera": "injera",
    # Filipino
    "chicken-adobo": "adobo,chicken",
    "sinigang-hipon": "sinigang",
    "lumpia-shanghai": "lumpia",
    # Pakistani
    "chicken-karahi": "karahi,chicken",
    "chicken-biryani": "biryani,chicken",
    "nihari": "nihari",
    # Sri Lankan
    "sri-lankan-chicken-curry": "curry,coconut",
    "egg-hoppers": "hoppers,appa",
    "sri-lankan-dhal": "dhal,curry",
    # Cambodian
    "fish-amok": "amok,fish",
    "lok-lak": "lok,lak",
    "kuy-teav": "noodle,soup",
    # ---- v4 Phase 2 expansion (36 dishes) ----
    # Greek
    "souvlaki": "souvlaki,greek",
    "moussaka": "moussaka",
    "greek-salad": "greek,salad",
    # Spanish
    "paella": "paella",
    "tortilla-espanola": "spanish,omelette",
    "patatas-bravas": "patatas,bravas",
    # Malaysian
    "nasi-lemak": "nasi,lemak",
    "char-kway-teow": "char,kway,teow",
    "laksa": "laksa",
    # German
    "wiener-schnitzel": "schnitzel",
    "sauerbraten": "sauerbraten",
    "kartoffelsalat": "potato,salad",
    # Indonesian
    "nasi-goreng": "nasi,goreng",
    "beef-rendang": "rendang",
    "gado-gado": "gado,gado",
    # Brazilian
    "feijoada": "feijoada",
    "moqueca": "moqueca",
    "pao-de-queijo": "cheese,bread",
    # Peruvian
    "lomo-saltado": "lomo,saltado",
    "ceviche": "ceviche",
    "aji-de-gallina": "aji,gallina",
    # Caribbean
    "jerk-chicken": "jerk,chicken",
    "rice-and-peas": "rice,beans",
    "ackee-saltfish": "ackee,saltfish",
    # Taiwanese
    "beef-noodle-soup": "beef,noodle",
    "three-cup-chicken": "three,cup,chicken",
    "lu-rou-fan": "rice,pork",
    # Portuguese
    "bacalhau-a-bras": "bacalhau,bras",
    "caldo-verde": "caldo,verde",
    "pastel-de-nata": "pastel,nata",
    # British
    "fish-and-chips": "fish,chips",
    "shepherds-pie": "shepherds,pie",
    "full-english-breakfast": "english,breakfast",
    # Eastern European
    "borscht": "borscht",
    "pierogi": "pierogi",
    "goulash": "goulash",
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
    # Myanmar regional — see `scripts/myanmar_food_images.py` (merged in `_img`).
    "buuz": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Bansh_Buuz_Khuushuur_1.JPG/1280px-Bansh_Buuz_Khuushuur_1.JPG",
    "khuushuur": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/MongolianKhuushuur.JPG/1280px-MongolianKhuushuur.JPG",
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
    # ---- v4 Phase 1 expansion. Every URL verified live (HTTP 200) against
    # ----  upload.wikimedia.org on 2026-06. The lookups went through the
    # ----  Wikipedia REST `summary` API for the dish's article + Commons
    # ----  file search for dishes without their own article; the URLs are
    # ----  thumb/1280px form per Wikimedia's request to downstream sites.
    # Lebanese
    "hummus": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/Lebanese_style_hummus.jpg/1280px-Lebanese_style_hummus.jpg",
    "tabbouleh": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/Tabouleh_1.JPG/1280px-Tabouleh_1.JPG",
    "kibbeh-bil-sanieh": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Kibbeh3.jpg/1280px-Kibbeh3.jpg",
    # Turkish
    "adana-kebab": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Adana_kebab.jpg/1280px-Adana_kebab.jpg",
    "lahmacun": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Lahmacun.jpg/1280px-Lahmacun.jpg",
    "baklava": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/Pistachio_Baklava_%2823102093965%29.jpg/1280px-Pistachio_Baklava_%2823102093965%29.jpg",
    # Moroccan
    "chicken-tagine": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Tajine-marocain-un-plat-varie-et-sain_%28cropped%29.jpg/1280px-Tajine-marocain-un-plat-varie-et-sain_%28cropped%29.jpg",
    "lamb-couscous": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Moroccan_cuscus%2C_from_Casablanca%2C_September_2018.jpg/1280px-Moroccan_cuscus%2C_from_Casablanca%2C_September_2018.jpg",
    "harira": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Harira.png/1280px-Harira.png",
    # Ethiopian
    "doro-wat": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Ethiopian_wat.jpg/1280px-Ethiopian_wat.jpg",
    "misir-wat": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Misir_Wot_and_Gomen_Besiga_-_Abyssinia%2C_Brighton.jpg/1280px-Misir_Wot_and_Gomen_Besiga_-_Abyssinia%2C_Brighton.jpg",
    "injera": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Injera_with_eight_kinds_of_stew.jpg/1280px-Injera_with_eight_kinds_of_stew.jpg",
    # Filipino
    "chicken-adobo": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/Adobo_DSCF4391.jpg/1280px-Adobo_DSCF4391.jpg",
    "sinigang-hipon": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/The_Best_Sinigang_Cuisine.jpg/1280px-The_Best_Sinigang_Cuisine.jpg",
    "lumpia-shanghai": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Loenpia_Semarang.JPG/1280px-Loenpia_Semarang.JPG",
    # Pakistani
    "chicken-karahi": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Punjabi_Chicken_Karahi.JPG/1280px-Punjabi_Chicken_Karahi.JPG",
    "chicken-biryani": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/%22Hyderabadi_Dum_Biryani%22.jpg/1280px-%22Hyderabadi_Dum_Biryani%22.jpg",
    "nihari": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Nalli_Nihari_India.jpg/1280px-Nalli_Nihari_India.jpg",
    # Sri Lankan
    "sri-lankan-chicken-curry": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Sri_Lankan_Rice_and_Curry.jpg/1280px-Sri_Lankan_Rice_and_Curry.jpg",
    "egg-hoppers": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Appam_-_%E0%AE%85%E0%AE%AA%E0%AF%8D%E0%AE%AA%E0%AE%AE%E0%AF%8D.jpg/1280px-Appam_-_%E0%AE%85%E0%AE%AA%E0%AF%8D%E0%AE%AA%E0%AE%AE%E0%AF%8D.jpg",
    # sri-lankan-dhal: uses regional rice-and-curry photo until a dedicated
    # parippu Commons shot is curated.
    # Cambodian
    "fish-amok": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Fish_Amok_with_Rice.jpg/1280px-Fish_Amok_with_Rice.jpg",
    "lok-lak": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Beef_Lok_Lak.jpg/1280px-Beef_Lok_Lak.jpg",
    "kuy-teav": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Katieu.jpg/1280px-Katieu.jpg",
    # ---- v4 Phase 2 expansion. All URLs verified live (HTTP 200) against
    # ----  upload.wikimedia.org via thumb/1280px requests, sourced from
    # ----  the Wikipedia REST `summary` API on the dish's English article
    # ----  (with one Commons-search override for kartoffelsalat where the
    # ----  REST API returned a movie-poster image, and another for
    # ----  Taiwanese beef noodle soup where the article picked a
    # ----  Lanzhou photo instead of the Taiwanese one).
    # Greek
    "souvlaki": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Souvlaki_in_Athens.JPG/1280px-Souvlaki_in_Athens.JPG",
    "moussaka": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/MussakasMeMelitsanesKePatates01.JPG/1280px-MussakasMeMelitsanesKePatates01.JPG",
    "greek-salad": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Greece_Food_Horiatiki.JPG/1280px-Greece_Food_Horiatiki.JPG",
    # Spanish
    "paella": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/01_Paella_Valenciana_original.jpg/1280px-01_Paella_Valenciana_original.jpg",
    "tortilla-espanola": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/Tortilla_de_patata_-_San_Sebasti%C3%A1n.jpg/1280px-Tortilla_de_patata_-_San_Sebasti%C3%A1n.jpg",
    "patatas-bravas": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/Patatas_bravas_madrid.jpg/1280px-Patatas_bravas_madrid.jpg",
    # Malaysian
    "nasi-lemak": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Nasi_Lemak_dengan_Chili_Nasi_Lemak_dan_Sotong_Pedas%2C_di_Penang_Summer_Restaurant.jpg/1280px-Nasi_Lemak_dengan_Chili_Nasi_Lemak_dan_Sotong_Pedas%2C_di_Penang_Summer_Restaurant.jpg",
    "char-kway-teow": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/Char_kway_teow.jpg/1280px-Char_kway_teow.jpg",
    "laksa": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Nyonya_Laksa.jpg/1280px-Nyonya_Laksa.jpg",
    # German
    "wiener-schnitzel": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Wiener-Schnitzel02.jpg/1280px-Wiener-Schnitzel02.jpg",
    "sauerbraten": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Heldrunger_Sauerbraten_2.JPG/1280px-Heldrunger_Sauerbraten_2.JPG",
    "kartoffelsalat": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/German_potato_salad.jpg/1280px-German_potato_salad.jpg",
    # Indonesian
    "nasi-goreng": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Nasi_Goreng_Kampung_%2811967588375%29.jpg/1280px-Nasi_Goreng_Kampung_%2811967588375%29.jpg",
    "beef-rendang": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/Rendang_daging_sapi_asli_Padang.JPG/1280px-Rendang_daging_sapi_asli_Padang.JPG",
    "gado-gado": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/Gado_gado_jakarta.jpg/1280px-Gado_gado_jakarta.jpg",
    # Brazilian
    "feijoada": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Feijoada_%C3%A0_transmontada.jpg/1280px-Feijoada_%C3%A0_transmontada.jpg",
    "moqueca": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Moqueca.jpg/1280px-Moqueca.jpg",
    "pao-de-queijo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/Cheesebread.jpg/1280px-Cheesebread.jpg",
    # Peruvian
    "lomo-saltado": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Lomo_Saltado_-_Lima%2C_Peru_Miraflores_%28Tiendecita_Blanca%29.jpg/1280px-Lomo_Saltado_-_Lima%2C_Peru_Miraflores_%28Tiendecita_Blanca%29.jpg",
    "ceviche": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Cebiche_de_corvina.JPG/1280px-Cebiche_de_corvina.JPG",
    "aji-de-gallina": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Aj%C3%AD_de_gallina.jpg/1280px-Aj%C3%AD_de_gallina.jpg",
    # Caribbean
    "jerk-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/BBQJerk_Chicken.jpg/1280px-BBQJerk_Chicken.jpg",
    "rice-and-peas": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Rice_and_Peas.jpg/1280px-Rice_and_Peas.jpg",
    "ackee-saltfish": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Ackee_and_Saltfish.jpg/1280px-Ackee_and_Saltfish.jpg",
    # Taiwanese
    "beef-noodle-soup": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Taiwanese_Beef_Noodle_Soup.jpg/1280px-Taiwanese_Beef_Noodle_Soup.jpg",
    "three-cup-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Sanbeiji.jpg/1280px-Sanbeiji.jpg",
    "lu-rou-fan": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Lurou_fan%28Taiwanese_cuisine%29.jpg/1280px-Lurou_fan%28Taiwanese_cuisine%29.jpg",
    # Portuguese
    "bacalhau-a-bras": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Bacalhau_a_Bras.jpg/1280px-Bacalhau_a_Bras.jpg",
    "caldo-verde": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Caldo_verde.jpg/1280px-Caldo_verde.jpg",
    "pastel-de-nata": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Pasteis_de_Belem.jpg/1280px-Pasteis_de_Belem.jpg",
    # British
    "fish-and-chips": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Fish_and_chips_blackpool.jpg/1280px-Fish_and_chips_blackpool.jpg",
    "shepherds-pie": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Homerton_College_-_Shepherd%27s_pie_%28cropped%29.jpg/1280px-Homerton_College_-_Shepherd%27s_pie_%28cropped%29.jpg",
    "full-english-breakfast": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Full_English_breakfast_%28cropped%29.jpg/1280px-Full_English_breakfast_%28cropped%29.jpg",
    # Eastern European
    "borscht": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Borscht_served.jpg/1280px-Borscht_served.jpg",
    "pierogi": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/Pierogi_z_mas%C5%82em_-_2023.03.31.jpg/1280px-Pierogi_z_mas%C5%82em_-_2023.03.31.jpg",
    "goulash": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Gulyas080.jpg/1280px-Gulyas080.jpg",
    # ---- v8 expansion Wikimedia (culinary audit backfill) ----
    "beggar-s-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Beggar%27s_Chicken_by_Hangzhou%27s_%22Mountain_Beyond_Mountain%22_Restaurant.jpg/1280px-Beggar%27s_Chicken_by_Hangzhou%27s_%22Mountain_Beyond_Mountain%22_Restaurant.jpg",
    "biang-biang-noodles": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Biang_Biang_Mian.jpg/1280px-Biang_Biang_Mian.jpg",
    "bigos": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Bigos_%281%29.jpg/1280px-Bigos_%281%29.jpg",
    "boeuf-bourguignon": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Beef_bourguignon_NYT.jpg/1280px-Beef_bourguignon_NYT.jpg",
    "buddha-jumps-over-the-wall": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Buddha_soup_boul.jpg/1280px-Buddha_soup_boul.jpg",
    "bulgogi": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Bulgogi_2.jpg/1280px-Bulgogi_2.jpg",
    "bun-cha": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/B%C3%BAn_ch%E1%BA%A3_Vietnamese_food.jpg/1280px-B%C3%BAn_ch%E1%BA%A3_Vietnamese_food.jpg",
    "butter-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Butter_Chicken_%26_Butter_Naan_-_Home_-_Chandigarh_-_India_-_0006.jpg/1280px-Butter_Chicken_%26_Butter_Naan_-_Home_-_Chandigarh_-_India_-_0006.jpg",
    "chapli-kebab": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Chapli_Kebab.jpg/1280px-Chapli_Kebab.jpg",
    "char-siu": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/Charsiu.jpg/1280px-Charsiu.jpg",
    "char-siu-bao": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Char_siu_bao.jpg/1280px-Char_siu_bao.jpg",
    "chicken-enchiladas": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Enchilada_Rice_Beans.jpg/1280px-Enchilada_Rice_Beans.jpg",
    "chicken-shawarma": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/%D0%A8%D0%B0%D1%83%D1%80%D0%BC%D0%B0_6.jpg/1280px-%D0%A8%D0%B0%D1%83%D1%80%D0%BC%D0%B0_6.jpg",
    "chow-mein": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Homemade_Chow_mein_with_shrimps_and_meat_with_a_choy_and_Choung.jpg/1280px-Homemade_Chow_mein_with_shrimps_and_meat_with_a_choy_and_Choung.jpg",
    "com-tam": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/C%C6%A1m_T%E1%BA%A5m%2C_Da_Nang%2C_Vietnam.jpg/1280px-C%C6%A1m_T%E1%BA%A5m%2C_Da_Nang%2C_Vietnam.jpg",
    "couscous-royale": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Moroccan_cuscus%2C_from_Casablanca%2C_September_2018.jpg/1280px-Moroccan_cuscus%2C_from_Casablanca%2C_September_2018.jpg",
    "croque-monsieur": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Croque_monsieur.jpg/1280px-Croque_monsieur.jpg",
    "crossing-the-bridge-noodles": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bd/Crossing_the_Bridge_Rice_Noodles_full_ingredients_in_Mengzi_%2820200126132053%29.jpg/1280px-Crossing_the_Bridge_Rice_Noodles_full_ingredients_in_Mengzi_%2820200126132053%29.jpg",
    "dan-dan-noodles": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Dan-dan_noodles%2C_Shanghai.jpg/1280px-Dan-dan_noodles%2C_Shanghai.jpg",
    "dezhou-braised-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Single_Dezhou_braised_chicken_wrapped_in_paper_%2820170115132902%29.jpg/1280px-Single_Dezhou_braised_chicken_wrapped_in_paper_%2820170115132902%29.jpg",
    "di-san-xian": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Disanxian.jpg/1280px-Disanxian.jpg",
    "dongpo-pork": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fd/BCfood12.JPG/1280px-BCfood12.JPG",
    "fattoush": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Fattoush_mixed-salad.jpg/1280px-Fattoush_mixed-salad.jpg",
    "general-tso-s-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Flickr_preppybyday_4665999863--General_Tso%27s_Chicken.jpg/1280px-Flickr_preppybyday_4665999863--General_Tso%27s_Chicken.jpg",
    "goya-champuru": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Goya_Champuru_at_Yumenoya.jpg/1280px-Goya_Champuru_at_Yumenoya.jpg",
    "hainanese-chicken-rice": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Hainanese_Chicken_Rice.jpg/1280px-Hainanese_Chicken_Rice.jpg",
    "hairy-tofu": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/%E6%96%B9%E9%91%AB%E7%8E%89%E6%AF%9B%E8%B1%86%E8%85%90_2.jpg/1280px-%E6%96%B9%E9%91%AB%E7%8E%89%E6%AF%9B%E8%B1%86%E8%85%90_2.jpg",
    "hakka-stuffed-tofu": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/Hakka_yong_tau_foo_with_noodles.jpg/1280px-Hakka_yong_tau_foo_with_noodles.jpg",
    "har-gow": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Steamed_prawn_dumplings.jpg/1280px-Steamed_prawn_dumplings.jpg",
    "hong-kong-egg-tart": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/HK_SSP_%E9%95%B7%E6%B2%99%E7%81%A3_Cheung_Sha_Wan_%E6%B7%B1%E7%9B%9B%E8%B7%AF_Sham_Shing_Road_%E6%B3%93%E6%99%AF%E6%BB%99%E5%95%86%E5%A0%B4_Banyan_Mall_shop_%E8%9B%8B%E6%92%BB%E7%8E%8B_King_Bakery_Studio_December_2019_SS2_egg_tarts.jpg/1280px-HK_SSP_%E9%95%B7%E6%B2%99%E7%81%A3_Cheung_Sha_Wan_%E6%B7%B1%E7%9B%9B%E8%B7%AF_Sham_Shing_Road_%E6%B3%93%E6%99%AF%E6%BB%99%E5%95%86%E5%A0%B4_Banyan_Mall_shop_%E8%9B%8B%E6%92%BB%E7%8E%8B_King_Bakery_Studio_December_2019_SS2_egg_tarts.jpg",
    "iskender-kebab": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/%C4%B0skender_Kebap.jpg/1280px-%C4%B0skender_Kebap.jpg",
    "jianbing": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/%E7%85%8E%E9%A5%BC%E9%A6%83%E5%AD%90%E5%88%B6%E4%BD%9C%E8%BF%87%E7%A8%8B5.jpg/1280px-%E7%85%8E%E9%A5%BC%E9%A6%83%E5%AD%90%E5%88%B6%E4%BD%9C%E8%BF%87%E7%A8%8B5.jpg",
    "jingjiang-rousi": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/%E4%BA%AC%E9%85%B1%E8%82%89%E4%B8%9D.jpg/1280px-%E4%BA%AC%E9%85%B1%E8%82%89%E4%B8%9D.jpg",
    "kottu-roti": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Chicken_Kottu.jpg/1280px-Chicken_Kottu.jpg",
    "kung-pao-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Kung-pao-shanghai.jpg/1280px-Kung-pao-shanghai.jpg",
    "lamb-paomo": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Pita_Bread_Soaked_in_Lamb_Soup.jpg/1280px-Pita_Bread_Soaked_in_Lamb_Soup.jpg",
    "lei-cha": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Lei_cha.jpg/1280px-Lei_cha.jpg",
    "luosifen": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/Luosifen_at_Guangya%2C_Liuzhou_%2820190420141814%29.jpg/1280px-Luosifen_at_Guangya%2C_Liuzhou_%2820190420141814%29.jpg",
    "mac-and-cheese": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Original_Mac_n_Cheese_.jpg/1280px-Original_Mac_n_Cheese_.jpg",
    "massaman-curry": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Kaeng_matsaman_kai.JPG/1280px-Kaeng_matsaman_kai.JPG",
    "menemen": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Menemen%2C_%C4%B0zmir%2C_Turkey.jpg/1280px-Menemen%2C_%C4%B0zmir%2C_Turkey.jpg",
    "minchi": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Minchi_e_bacalhaus.jpg/1280px-Minchi_e_bacalhaus.jpg",
    "ohn-no-khao-sw": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/Ohn_No_Khao_Swe_at_Sapphire_Asian_Cuisine_%2810988302274%29.jpg/1280px-Ohn_No_Khao_Swe_at_Sapphire_Asian_Cuisine_%2810988302274%29.jpg",
    "oyster-omelette": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Billyfoodoysteromelette.jpg/1280px-Billyfoodoysteromelette.jpg",
    "pad-thai": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Phat_Thai_kung_Chang_Khien_street_stall.jpg/1280px-Phat_Thai_kung_Chang_Khien_street_stall.jpg",
    "pancit-canton": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Pancit_Ilonggo_Style_-_12110747826.jpg/1280px-Pancit_Ilonggo_Style_-_12110747826.jpg",
    "peking-duck": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Peking_Duck%2C_2014_%2802%29.jpg/1280px-Peking_Duck%2C_2014_%2802%29.jpg",
    "pork-chop-bun": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Porkchopbun.jpg/1280px-Porkchopbun.jpg",
    "rafute": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Okinawan_Rafute.jpg/1280px-Okinawan_Rafute.jpg",
    "red-braised-pork-belly": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/%E7%B4%85%E7%87%92%E8%82%89_Braised_pork_in_brown_sauce.jpg/1280px-%E7%B4%85%E7%87%92%E8%82%89_Braised_pork_in_brown_sauce.jpg",
    "roujiamo": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Roujiamo.jpg/1280px-Roujiamo.jpg",
    "seekh-kebab": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Pakistani_Food_Beef_Kabobs.jpg/1280px-Pakistani_Food_Beef_Kabobs.jpg",
    "sha-balep": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Tibetan_snack_Syabhaley_in_Nepal.jpg/1280px-Tibetan_snack_Syabhaley_in_Nepal.jpg",
    "sichuan-mapo-tofu": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Chen_Mapo_Tofu.jpg/1280px-Chen_Mapo_Tofu.jpg",
    "siwawa": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/%E4%B8%9D%E5%A8%83%E5%A8%83_%2828664736712%29.jpg/1280px-%E4%B8%9D%E5%A8%83%E5%A8%83_%2828664736712%29.jpg",
    "squirrel-fish": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Suzhou_Squirrel_fish_%E6%9D%BE%E9%BC%A0%E9%B1%96%E9%AD%9A_-_img_02.jpg/1280px-Suzhou_Squirrel_fish_%E6%9D%BE%E9%BC%A0%E9%B1%96%E9%AD%9A_-_img_02.jpg",
    "stinky-tofu": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Stinkender_Tofu_1.JPG/1280px-Stinkender_Tofu_1.JPG",
    "sundubu-jjigae": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/02/Sundubu-jjigae.jpg/1280px-Sundubu-jjigae.jpg",
    "taco-rice": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Taco_Rice_%28cropped%29.jpg/1280px-Taco_Rice_%28cropped%29.jpg",
    "thukpa": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Thukpa%2C_Tibetan_noodle_in_Osaka%2C_Japan.jpg/1280px-Thukpa%2C_Tibetan_noodle_in_Osaka%2C_Japan.jpg",
    "tibetan-momo": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Momo_nepal.jpg/1280px-Momo_nepal.jpg",
    "tonkatsu": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/%22Amai-Yuwaku%22_Special_Loin_Pork_Cutlet1.jpg/1280px-%22Amai-Yuwaku%22_Special_Loin_Pork_Cutlet1.jpg",
    "tsuivan": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Cujwan.JPG/1280px-Cujwan.JPG",
    "vegetable-samosas": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Samosas%2C_snack_food_at_Wikipedia%27s_16th_Birthday_celebration_in_Chittagong_%2801%29.jpg/1280px-Samosas%2C_snack_food_at_Wikipedia%27s_16th_Birthday_celebration_in_Chittagong_%2801%29.jpg",
    "wenchang-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Wenchang_Chicken_1.JPG/1280px-Wenchang_Chicken_1.JPG",
    "xiaolongbao": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/A_Xiaolongbao_from_The_Modern_Shanghai.jpg/1280px-A_Xiaolongbao_from_The_Modern_Shanghai.jpg",
    "yangzhou-fried-rice": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Chinese_fried_rice_by_stu_spivack_in_Cleveland%2C_OH.jpg/1280px-Chinese_fried_rice_by_stu_spivack_in_Cleveland%2C_OH.jpg",
    "zaalouk": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Zaalouk-01.JPG/1280px-Zaalouk-01.JPG",
    "zhajiangmian": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Billyzhajiang1.jpg/1280px-Billyzhajiang1.jpg",
    "zongzi": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Zongzi.jpg/1280px-Zongzi.jpg",
    # ---- v9 expansion: replace generic Unsplash pool photos ----
    "african-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/African_Piri_Piri_Chicken.jpg/1280px-African_Piri_Piri_Chicken.jpg",
    "bamboo-shoot-stew": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/I-Toq_Si_%2820141106190320%29.JPG/1280px-I-Toq_Si_%2820141106190320%29.JPG",
    "bbq-baby-back-ribs": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Spareribs_20160506_182617113.jpg/1280px-Spareribs_20160506_182617113.jpg",
    "beer-fish": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Suzhou_Squirrel_fish_%E6%9D%BE%E9%BC%A0%E9%B1%96%E9%AD%9A_-_img_02.jpg/1280px-Suzhou_Squirrel_fish_%E6%9D%BE%E9%BC%A0%E9%B1%96%E9%AD%9A_-_img_02.jpg",
    "braised-goose": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/Loumeidish.jpg/1280px-Loumeidish.jpg",
    "braised-lion-meatballs": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/%E7%8B%AE%E5%AD%90%E6%A5%BC%E7%8B%AE%E5%AD%90%E5%A4%B4.jpg/1280px-%E7%8B%AE%E5%AD%90%E6%A5%BC%E7%8B%AE%E5%AD%90%E5%A4%B4.jpg",
    "burmese-chicken-curry": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Mohnga.jpg/1280px-Mohnga.jpg",
    "chairman-maos-pork": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/%E7%B4%85%E7%87%92%E8%82%89_Braised_pork_in_brown_sauce.jpg/1280px-%E7%B4%85%E7%87%92%E8%82%89_Braised_pork_in_brown_sauce.jpg",
    "chicken-teriyaki": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Teriyaki_003.jpg/1280px-Teriyaki_003.jpg",
    "clay-pot-rice": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/32/Cured_Meat_Claypot_Rice_at_The_Soup_Kitchen_%2820200718171540%29.jpg/1280px-Cured_Meat_Claypot_Rice_at_The_Soup_Kitchen_%2820200718171540%29.jpg",
    "clay-pot-soup": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Xiamen-Waguan_weitang-%E7%93%A6%E7%BD%90%E7%85%A8%E6%B1%A4.jpg/1280px-Xiamen-Waguan_weitang-%E7%93%A6%E7%BD%90%E7%85%A8%E6%B1%A4.jpg",
    "coconut-rice": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Nasi_Liwet_Solo.jpg/1280px-Nasi_Liwet_Solo.jpg",
    "crystal-dumplings": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Steamed_prawn_dumplings.jpg/1280px-Steamed_prawn_dumplings.jpg",
    "dongbei-dumplings": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/%E5%8F%B0%E7%81%A3%E5%8D%97%E6%8A%95%E8%8D%89%E5%B1%AF%E6%B0%B4%E9%A4%83Nantou%2C_Taiwan_Caotun_dumplings.jpg/1280px-%E5%8F%B0%E7%81%A3%E5%8D%97%E6%8A%95%E8%8D%89%E5%B1%AF%E6%B0%B4%E9%A4%83Nantou%2C_Taiwan_Caotun_dumplings.jpg",
    "erkuai": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/%E6%98%86%E6%98%8E%E8%8B%B1%E5%87%A4%E7%83%A7%E9%A5%B5%E5%9D%97.jpg/1280px-%E6%98%86%E6%98%8E%E8%8B%B1%E5%87%A4%E7%83%A7%E9%A5%B5%E5%9D%97.jpg",
    "fish-ambul-thiyal": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Sri_Lankan_Rice_and_Curry.jpg/1280px-Sri_Lankan_Rice_and_Curry.jpg",
    "glutinous-rice-rolls": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/Cha_siu_choeng.jpg/1280px-Cha_siu_choeng.jpg",
    "guobaorou": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Guobaorou_a0.jpg/1280px-Guobaorou_a0.jpg",
    "kare-kare": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/Mac_MG_5939.jpg/1280px-Mac_MG_5939.jpg",
    "laghman": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Dalian_Liaoning_China_Noodlemaker-01.jpg/1280px-Dalian_Liaoning_China_Noodlemaker-01.jpg",
    "lasagna-bolognese": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/Lasagna_bolognese.jpg/1280px-Lasagna_bolognese.jpg",
    "lion-head-meatballs": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/%E7%8B%AE%E5%AD%90%E6%A5%BC%E7%8B%AE%E5%AD%90%E5%A4%B4.jpg/1280px-%E7%8B%AE%E5%AD%90%E6%A5%BC%E7%8B%AE%E5%AD%90%E5%A4%B4.jpg",
    "manchurian-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Chicken_Manchurian_%28Hyderabad_Style%29_%2811960049916%29.jpg/1280px-Chicken_Manchurian_%28Hyderabad_Style%29_%2811960049916%29.jpg",
    "manchurian-meatballs": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Chicken_Manchurian_%28Hyderabad_Style%29_%2811960049916%29.jpg/1280px-Chicken_Manchurian_%28Hyderabad_Style%29_%2811960049916%29.jpg",
    "nanchang-mixed-noodles": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Dan-dan_noodles%2C_Shanghai.jpg/1280px-Dan-dan_noodles%2C_Shanghai.jpg",
    "polo": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Afghan_Palo.jpg/1280px-Afghan_Palo.jpg",
    "pozole-rojo": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Green_pozole%2C_dressed_%2829161841908%29_%28cropped%29.jpg/1280px-Green_pozole%2C_dressed_%2829161841908%29_%28cropped%29.jpg",
    "red-wine-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Sanbeiji.jpg/1280px-Sanbeiji.jpg",
    "risotto-alla-milanese": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Risotto_with_speck_and_goat_cheese_%286101067436%29.jpg/1280px-Risotto_with_speck_and_goat_cheese_%286101067436%29.jpg",
    "salt-baked-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Wenchang_Chicken_1.JPG/1280px-Wenchang_Chicken_1.JPG",
    "samsa": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/Ouzb%C3%A9kistan-Samsas.jpg/1280px-Ouzb%C3%A9kistan-Samsas.jpg",
    "sauerkraut-with-pork": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Bigos_%281%29.jpg/1280px-Bigos_%281%29.jpg",
    "shiro-wat": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Taita_and_shiro.jpg/1280px-Taita_and_shiro.jpg",
    "sour-fish-soup": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Fish_Amok_with_Rice.jpg/1280px-Fish_Amok_with_Rice.jpg",
    "sri-lankan-dhal": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Sri_Lankan_Rice_and_Curry.jpg/1280px-Sri_Lankan_Rice_and_Curry.jpg",
    "steam-pot-chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Beggar%27s_Chicken_by_Hangzhou%27s_%22Mountain_Beyond_Mountain%22_Restaurant.jpg/1280px-Beggar%27s_Chicken_by_Hangzhou%27s_%22Mountain_Beyond_Mountain%22_Restaurant.jpg",
    "steamed-fish-head": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Steamed_Fish_Head_with_Diced_Chili_%2820150726122046%29.jpg/1280px-Steamed_Fish_Head_with_Diced_Chili_%2820150726122046%29.jpg",
    "steamed-pork-ribs": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/%E7%B2%89%E8%92%B8%E8%82%89.jpg/1280px-%E7%B2%89%E8%92%B8%E8%82%89.jpg",
    "stir-fried-pork-liver": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/Charsiu.jpg/1280px-Charsiu.jpg",
    "suan-cai-stew": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Bigos_%281%29.jpg/1280px-Bigos_%281%29.jpg",
    "sweet-sour-carp": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Suzhou_Squirrel_fish_%E6%9D%BE%E9%BC%A0%E9%B1%96%E9%AD%9A_-_img_02.jpg/1280px-Suzhou_Squirrel_fish_%E6%9D%BE%E9%BC%A0%E9%B1%96%E9%AD%9A_-_img_02.jpg",
    "teochew-oyster-omelette": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Billyfoodoysteromelette.jpg/1280px-Billyfoodoysteromelette.jpg",
    "tibs": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Injera_with_eight_kinds_of_stew.jpg/1280px-Injera_with_eight_kinds_of_stew.jpg",
    "west-lake-fish": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/West_Lake_Fish_in_Vinegar_Gravy_Feb_2026.jpg/1280px-West_Lake_Fish_in_Vinegar_Gravy_Feb_2026.jpg",
    "wonton-noodle-soup": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/HK_SW_%E4%B8%8A%E7%92%B0_Sheung_Wan_%E7%9A%87%E5%90%8E%E5%A4%A7%E9%81%93%E4%B8%AD_303_Queen%27s_Road_Central_%E6%AC%8A%E8%A8%98%E9%9B%B2%E5%90%9E%E9%BA%B5_Wonton_noodle_soup_shop_June_2020_SS2_10.jpg/1280px-HK_SW_%E4%B8%8A%E7%92%B0_Sheung_Wan_%E7%9A%87%E5%90%8E%E5%A4%A7%E9%81%93%E4%B8%AD_303_Queen%27s_Road_Central_%E6%AC%8A%E8%A8%98%E9%9B%B2%E5%90%9E%E9%BA%B5_Wonton_noodle_soup_shop_June_2020_SS2_10.jpg",

}


# Generator slugs in expansion modules that differ from title-derived slugs.
_WIKIMEDIA_SLUG_ALIASES: dict[str, str] = {
    "rendang": "beef-rendang",
    "samosas": "vegetable-samosas",
    "lasagna": "lasagna-bolognese",
    "risotto-milanese": "risotto-alla-milanese",
    "bbq-ribs": "bbq-baby-back-ribs",
    "enchiladas": "chicken-enchiladas",
    "pozole": "pozole-rojo",
    "sauerkraut-pork": "sauerkraut-with-pork",
    "ohn-no-khao-swe": "ohn-no-khao-sw",
    "burmese-curry": "burmese-chicken-curry",
    "general-tsos-chicken": "general-tso-s-chicken",
    "momo": "tibetan-momo",
    "egg-tart": "hong-kong-egg-tart",
    "sichuan-mapo-tofu": "mapo-tofu",
    "mapo-tofu-sichuan": "mapo-tofu",
    "beggars-chicken": "beggar-s-chicken",
    "buddha-jumps-wall": "buddha-jumps-over-the-wall",
    "crossing-bridge-noodles": "crossing-the-bridge-noodles",
    "hainan-chicken-rice": "hainanese-chicken-rice",
    "hair-tofu": "hairy-tofu",
    "pancit": "pancit-canton",
    "red-braised-pork": "red-braised-pork-belly",
    "shawarma": "chicken-shawarma",
    "snail-rice-noodles": "luosifen",
    "sticky-rice-dumplings": "zongzi",
    "stuffed-tofu": "hakka-stuffed-tofu",
    "bacalhau-bras": "bacalhau-a-bras",
    "coconut-rice": "coconut-rice",
    "polo": "polo",
    "braised-goose": "braised-goose",
    "clay-pot-soup": "clay-pot-soup",
    "glutinous-rice-rolls": "glutinous-rice-rolls",
    "red-wine-chicken": "red-wine-chicken",
    "steam-pot-chicken": "steam-pot-chicken",
    "teochew-oyster-omelette": "teochew-oyster-omelette",
}


def _img(slug: str) -> str:
    """Build a stable food image URL for a recipe.

    - Wikimedia slugs in `_WIKIMEDIA_IMAGE_BY_SLUG` win (hand-curated).
    - Myanmar regional slugs use verified Burmese Commons photos.
    - Everything else maps deterministically to a permanent Unsplash CDN
      photo so cards never depend on the flaky LoremFlickr redirector.
    """
    from scripts.myanmar_food_images import MYANMAR_WIKIMEDIA_BY_SLUG

    slug = _WIKIMEDIA_SLUG_ALIASES.get(slug, slug)
    if slug in _WIKIMEDIA_IMAGE_BY_SLUG:
        return _WIKIMEDIA_IMAGE_BY_SLUG[slug]
    if slug in MYANMAR_WIKIMEDIA_BY_SLUG:
        return MYANMAR_WIKIMEDIA_BY_SLUG[slug]
    return stable_food_image_url(slug)


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
                "title": "Canh Kimchi Jjigae",
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
                "title": "韩式炸鸡",
                "description": "经过两次油炸至薄脆酥香，再裹上甜辣的韩式调味酱（양념）。",
            },
            "ja": {
                "title": "ヤンニョムチキン",
                "description": "二度揚げでガラスのようにサクサクに仕上げ、甘辛いヤンニョムソースをまとわせた韓国フライドチキン。",
            },
            "ko": {
                "title": "양념치킨",
                "description": "두 번 튀겨 유리처럼 바삭한 식감을 살리고, 달콤매콤한 양념 소스에 버무린 한국식 후라이드 치킨.",
            },
            "vi": {
                "title": "Gà Rán Hàn Quốc Sốt Yangnyeom",
                "description": "Gà chiên hai lần giòn rụm như thủy tinh, áo lên lớp sốt yangnyeom cay ngọt đặc trưng.",
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
                "title": "玉子盖饭",
                "description": "甜咸交融的日式高汤煮蛋，柔滑如奶冻般铺在热米饭上，配上葱花。",
            },
            "ja": {
                "title": "玉子丼",
                "description": "ふんわりとろとろの卵を、甘辛い出汁あんと一緒にご飯にのせた優しい味わいの丼物。",
            },
            "ko": {
                "title": "다마고동 (계란덮밥)",
                "description": "달콤짭짤한 다시 양념을 머금은 부드러운 계란을 따끈한 밥 위에 얹은 일본식 덮밥.",
            },
            "vi": {
                "title": "Cơm trứng ốp la sốt dashi",
                "description": "Trứng ốp la mềm, mịn trên cơm với sốt dashi ngọt và mặn",
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
                "title": "味噌烤鲑鱼",
                "description": "甜咸交融的味噌酱汁裹住鲑鱼，外层焦香带糯、内里恰到火候。",
            },
            "ja": {
                "title": "鮭の味噌漬け焼き（西京焼き風）",
                "description": "甘じょっぱい味噌だれを纏わせ、表面はとろりと香ばしく、中はしっとりと焼き上げた鮭。",
            },
            "ko": {
                "title": "미소된장 연어 구이",
                "description": "달짝지근하면서 짭조름한 미소 양념이 연어 표면을 윤기 나게 코팅하고, 속살은 촉촉하게 익은 한 그릇.",
            },
            "vi": {
                "title": "Cá Hồi Sốt Miso",
                "description": "Lớp sốt miso mặn ngọt phủ ngoài bóng đẹp, bên trong cá hồi mềm mọng vừa chín tới.",
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
                "title": "冷荞麦面（笊籬蕎麥）",
                "description": "荞麦面冰镇后，蘸取鲜美的鲣鱼酱油（つゆ）食用，是日本夏日经典。",
            },
            "ja": {
                "title": "ざるそば",
                "description": "冷たく締めた手打ち蕎麦を、出汁の効いたつゆにつけていただく、夏の風物詩。",
            },
            "ko": {
                "title": "자루소바",
                "description": "차게 식힌 메밀국수를 감칠맛 나는 쯔유 소스에 찍어 먹는 일본식 여름 별미.",
            },
            "vi": {
                "title": "Mì Soba Lạnh Với Nước Chấm",
                "description": "Mì kiều mạch được phục vụ lạnh với nước chấm tsuyu đậm đà.",
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
                "title": "麻婆豆腐",
                "description": "经典川菜：嫩滑豆腐配以麻辣豆瓣酱，花椒的麻香与辣椒的火辣交织成绝妙风味。",
            },
            "ja": {
                "title": "麻婆豆腐 (マーボードウフ)",
                "description": "四川料理の定番。絹ごし豆腐を花椒のしびれる辛さと豆板醤の旨辛ソースで仕上げた一品。",
            },
            "ko": {
                "title": "마파두부",
                "description": "사천 요리의 대표 메뉴. 두반장의 매콤한 맛과 산초의 알싸한 향이 어우러진 부드러운 두부 요리.",
            },
            "vi": {
                "title": "Đậu hũ Mapo",
                "description": "Món ăn Sichuan kinh điển: đậu hũ mềm mịn trong nước sốt ớt-bean cay tê",
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
                "title": "蛋花汤",
                "description": "丝滑蛋花，漂浮于清澈姜味汤中。",
            },
            "ja": {
                "title": "卵とじスープ",
                "description": "なめらかな卵が、澄んだ生姜香るスープに優しく広がる。",
            },
            "ko": {
                "title": "계란탕",
                "description": "부드러운 계란이 맑은 생강 향 육수에 실크처럼 퍼져있는 맛.",
            },
            "vi": {
                "title": "Súp Trứng",
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
                "title": "西兰花炒牛肉",
                "description": "嫩滑牛肉与爽脆西兰花同炒，裹上油亮的酱油芡汁，简单经典。",
            },
            "ja": {
                "title": "牛肉とブロッコリーの炒め物",
                "description": "柔らかい牛肉と歯ごたえの良いブロッコリーを、艶やかな醤油ベースのタレで炒め合わせた中華の定番。",
            },
            "ko": {
                "title": "소고기 브로콜리 볶음",
                "description": "부드러운 소고기와 아삭한 브로콜리를 윤기 나는 간장 소스에 함께 볶아낸 중화풍 요리.",
            },
            "vi": {
                "title": "Bò Xào Bông Cải Xanh",
                "description": "Thịt bò mềm xào cùng bông cải xanh giòn ngọt, áo lên lớp sốt xì dầu bóng đẹp.",
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
                "title": "缅甸鱼汤粉",
                "description": "缅甸国菜：香茅鱼汤搭配米粉，风味独特。",
            },
            "ja": {
                "title": "モヒンガー",
                "description": "ミャンマーの国民食：レモングラス風味の魚のスープに米麺を添えて。",
            },
            "ko": {
                "title": "모힝가",
                "description": "미얀마의 국민 요리: 레몬그라스 생선 육수에 쌀국수를 곁들인 맛있는 한 그릇.",
            },
            "vi": {
                "title": "Mohinga (Bún Cá Miến Điện)",
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
                "title": "缅式茶叶沙拉",
                "description": "拉佩托（Lahpet thoke）：腌制茶叶搭配酥脆豆类、花生和青柠，缅甸经典开胃菜。",
            },
            "ja": {
                "title": "ラペットゥッ（茶葉のサラダ）",
                "description": "ラペットゥッ：発酵させた茶葉に、カリカリの豆、ピーナッツ、ライムを和えたミャンマーの定番サラダ。",
            },
            "ko": {
                "title": "라펫똑 (미얀마 찻잎 샐러드)",
                "description": "라펫똑: 절인 찻잎에 바삭한 콩, 땅콩, 라임을 곁들인 미얀마식 전통 샐러드.",
            },
            "vi": {
                "title": "Salad Lá Trà Miến Điện (Lahpet Thoke)",
                "description": "Lahpet thoke: lá trà muối trộn với các loại đậu giòn, đậu phộng và chanh — món khai vị kinh điển của Myanmar.",
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
                "title": "掸邦米线",
                "description": "掸式米线配以微辣番茄猪肉酱，是缅甸北部的家常风味。",
            },
            "ja": {
                "title": "シャンヌードル",
                "description": "ミャンマー・シャン州風の米麺に、ほんのりスパイスの効いたトマトと豚肉のソースを合わせた一杯。",
            },
            "ko": {
                "title": "샨 누들",
                "description": "샨족 스타일의 쌀국수에 살짝 매콤한 토마토-돼지고기 소스를 곁들인 미얀마식 면 요리.",
            },
            "vi": {
                "title": "Mỳ Shan",
                "description": "Bún gạo kiểu Shan ăn cùng sốt cà chua thịt heo nêm gia vị nhẹ — đặc sản miền Bắc Myanmar.",
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
                "title": "泰式打抛鸡（罗勒炒鸡）",
                "description": "泰国街头经典：鸡肉与圣罗勒、辣椒同炒，香辣下饭。",
            },
            "ja": {
                "title": "ガパオ・ガイ（鶏ひき肉のホーリーバジル炒め）",
                "description": "タイの屋台で愛される定番。鶏ひき肉をホーリーバジルと唐辛子で香り高く炒めた一皿。",
            },
            "ko": {
                "title": "팟 끄라파오 까이 (홀리바질 닭고기 볶음)",
                "description": "태국 길거리 음식의 대표 메뉴. 닭고기를 홀리바질과 고추로 향긋하고 매콤하게 볶아낸 요리.",
            },
            "vi": {
                "title": "Pad Krapow Gai (Gà Xào Húng Quế)",
                "description": "Món ăn đường phố kinh điển của Thái Lan: thịt gà xào cùng húng quế thánh và ớt cay nồng.",
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
                "title": "Súp Tom Yum Tôm",
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
                "title": "泰式青木瓜沙拉",
                "description": "泰式青木瓜沙拉，又称宋丹，将青木瓜捣碎，与青柠、鱼露、花生和辣椒完美融合，口感火辣，清爽开胃。",
            },
            "ja": {
                "title": "ソムタム",
                "description": "ソムタムは、青パパイヤを叩き潰し、ライム、ナンプラー、ピーナッツ、そして燃えるような辛さを加えた、タイを代表するサラダです。",
            },
            "ko": {
                "title": "쏨땀",
                "description": "쏨땀은 풋파파야를 으깨 라임, 피시 소스, 땅콩을 넣고 매콤한 불맛을 더해 만든 태국식 샐러드입니다.",
            },
            "vi": {
                "title": "Gỏi đu đủ",
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
                "description": "北方风味越南牛肉河粉，汤头清澈芳香。",
            },
            "ja": {
                "title": "フォー・ボー",
                "description": "透明で香り高いスープが特徴の、ベトナム北部風牛肉麺。",
            },
            "ko": {
                "title": "베트남 쇠고기 쌀국수",
                "description": "맑고 향긋한 육수가 일품인 베트남 북부식 쇠고기 쌀국수.",
            },
            "vi": {
                "title": "Phở Bò",
                "description": "Món phở bò kiểu miền Bắc Việt Nam với nước dùng trong và thơm lừng.",
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
                "title": "越式烤肉法棍",
                "description": "将香茅烤猪肉夹入香脆法棍中，搭配腌菜和新鲜香草。",
            },
            "ja": {
                "title": "焼き豚バインミー",
                "description": "レモングラス香る豚焼き肉をパリパリのバゲットに挟み、漬物とハーブを添えました。",
            },
            "ko": {
                "title": "구운 돼지고기 반미",
                "description": "바삭한 바게트 속에 레몬그라스 향의 돼지고기 구이와 절인 채소, 허브를 넣었습니다.",
            },
            "vi": {
                "title": "Bánh Mì Thịt Nướng",
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
                "title": "Đậu Lăng Hầm Tadka",
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
                "title": "Cà Ri Aloo Gobi",
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
                "description": "一道用大蒜、辣椒、欧芹和优质橄榄油制作的经典意面，食材皆来自厨房常备。",
            },
            "ja": {
                "title": "ペペロンチーノ",
                "description": "ニンニク、唐辛子、パセリ、上質なオリーブオイルで作る、常備食材で手軽に楽しめるパスタです。",
            },
            "ko": {
                "title": "알리오 올리오",
                "description": "마늘, 고추, 파슬리, 그리고 훌륭한 올리브 오일로 만드는, 주방에 있는 재료로 즐기는 파스타입니다.",
            },
            "vi": {
                "title": "Mì Ý Tỏi Ớt",
                "description": "Món mì Ý đơn giản từ các nguyên liệu có sẵn trong bếp, với tỏi, ớt, ngò tây và dầu ô liu hảo hạng.",
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
                "description": "香煎肉饼，融化美式芝士，黄油烤面包。",
            },
            "ja": {
                "title": "定番チーズバーガー",
                "description": "香ばしいスマッシュパティ、とろけるアメリカンチーズ、バターで焼いたバンズ。",
            },
            "ko": {
                "title": "클래식 치즈버거",
                "description": "육즙 가득한 스매시 패티, 녹아내린 아메리칸 치즈, 버터에 구운 번.",
            },
            "vi": {
                "title": "Bánh mì kẹp phô mai cổ điển",
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
                "title": "经典巧克力曲奇",
                "description": "边缘酥脆，内心软糯，令人争相品尝。",
            },
            "ja": {
                "title": "定番チョコチップクッキー",
                "description": "周りはサクサク、中はしっとりもちもち。誰もが夢中になる美味しさです。",
            },
            "ko": {
                "title": "클래식 초콜릿 칩 쿠키",
                "description": "바삭한 가장자리, 쫀득한 속. 모두가 서로 먹으려 하는 맛.",
            },
            "vi": {
                "title": "Bánh quy sô-cô-la chip cổ điển",
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
                "title": "廷加鸡肉玉米饼",
                "description": "烟熏奇波特番茄鸡丝，盛于温热玉米饼。",
            },
            "ja": {
                "title": "チキンティンガタコス",
                "description": "スモーキーなチポトレトマト風味のほぐし鶏肉を、温かいコーントルティーヤで。",
            },
            "ko": {
                "title": "치킨 팅가 타코",
                "description": "훈연 향 치폴레 토마토 양념의 찢은 닭고기를 따뜻한 콘 또띠아에.",
            },
            "vi": {
                "title": "Gà Tinga Taco",
                "description": "Gà xé vị khói sốt cà chua chipotle, ăn kèm bánh ngô ấm nóng.",
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
                "title": "Sốt Bơ Guacamole",
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
                "title": "Bò Nướng Carne Asada",
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
                "title": "洛林乳蛋饼",
                "description": "黄油酥皮馅料内填有培根、鸡蛋和奶油，按照洛林传统制作",
            },
            "ja": {
                "title": "キッシュ・ロレーヌ",
                "description": "ロレーヌ伝統のバター入りのショートパイ生地にベーコン、卵、クリームが入っています",
            },
            "ko": {
                "title": "키슈 로렌",
                "description": "로렌 전통 방식으로 베이컨, 계란, 크림을 넣은 버터 쇼트 크러스트",
            },
            "vi": {
                "title": "Bánh Quiche Lorraine",
                "description": "Vỏ bánh ngắn giòn với bơ, chứa thịt xông khói, trứng và kem theo truyền thống Lorraine",
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
    # ====================================================================
    # v4 Phase 1 expansion: 24 recipes for 8 new cuisines.
    # Same shape as the recipes above: hand-curated Wikimedia URL via
    # `_img(slug)`, 4-locale translations (zh/ja/ko/vi), and an
    # `_EXTRA_TAGS_BY_TITLE` row in seed_curated_recipes.py to wire the
    # Explore course/dietary filters.
    # ====================================================================
    # ---- Lebanese ----
    {
        "title": "Hummus",
        "description": "Silky chickpea-tahini dip swirled with olive oil, lemon, and warm cumin.",
        "cuisine": "lebanese", "language": "en", "spice_level": 0,
        "prep": 15, "cook": 0, "servings": 6, "image": _img("hummus"),
        "tags": ["dip", "mezze", "make-ahead"],
        "ingredients": [
            {"quantity": 250, "unit": "g", "name": "cooked chickpeas (or 1 can, drained and rinsed)"},
            {"quantity": 80, "unit": "g", "name": "tahini, well stirred"},
            {"quantity": 3, "unit": "tbsp", "name": "lemon juice, plus more to taste"},
            {"quantity": 2, "unit": "cloves", "name": "garlic, peeled"},
            {"quantity": 0.5, "unit": "tsp", "name": "ground cumin"},
            {"quantity": 0.5, "unit": "tsp", "name": "salt"},
            {"quantity": 60, "unit": "ml", "name": "ice water"},
            {"quantity": 2, "unit": "tbsp", "name": "extra-virgin olive oil, for finishing"},
            {"name": "paprika or sumac, for garnish"},
        ],
        "steps": [
            "Blend tahini and lemon juice in a food processor for 60 seconds until pale and fluffy.",
            "Add garlic, salt, and cumin. Pulse to combine.",
            "Add chickpeas and process 2 minutes, scraping the bowl twice.",
            "With the motor running, stream in ice water until the hummus turns silky and pale.",
            "Taste, correct lemon and salt, and spread into a shallow bowl with a swoosh.",
            "Drizzle with olive oil and dust with paprika before serving with warm pita.",
        ],
        "translations": {
            "zh": {
                "title": "鹰嘴豆泥",
                "description": "丝滑的鹰嘴豆芝麻酱泥，淋上橄榄油、柠檬和温润的孜然。",
            },
            "ja": {
                "title": "フムス",
                "description": "ひよこ豆とタヒニのなめらかなディップに、オリーブオイル、レモン、ほんのりとしたクミンを絡めて。",
            },
            "ko": {
                "title": "후무스",
                "description": "병아리콩과 타히니로 만든 부드러운 딥에 올리브 오일, 레몬, 따뜻한 쿠민을 두른 한 그릇.",
            },
            "vi": {
                "title": "Sốt Hummus",
                "description": "Sốt đậu gà nghiền cùng tahini mịn mượt, rưới dầu ô-liu, chanh và chút thì là Ai Cập ấm áp.",
            },
        },
    },
    {
        "title": "Tabbouleh",
        "description": "Bright parsley-bulgur salad with tomato, mint, and a snap of lemon.",
        "cuisine": "lebanese", "language": "en", "spice_level": 0,
        "prep": 25, "cook": 5, "servings": 4, "image": _img("tabbouleh"),
        "tags": ["salad", "mezze", "make-ahead"],
        "ingredients": [
            {"quantity": 60, "unit": "g", "name": "fine bulgur"},
            {"quantity": 4, "unit": "bunches", "name": "flat-leaf parsley, leaves only, finely chopped"},
            {"quantity": 1, "unit": "small bunch", "name": "fresh mint, leaves only, finely chopped"},
            {"quantity": 3, "name": "ripe tomatoes, diced small"},
            {"quantity": 4, "name": "spring onions, thinly sliced"},
            {"quantity": 60, "unit": "ml", "name": "lemon juice"},
            {"quantity": 60, "unit": "ml", "name": "extra-virgin olive oil"},
            {"quantity": 0.5, "unit": "tsp", "name": "salt"},
            {"name": "freshly ground black pepper"},
        ],
        "steps": [
            "Soak bulgur in 80 ml warm water for 15 minutes until tender; squeeze out excess water.",
            "Dice the tomatoes over the parsley so the juices season the herbs.",
            "Wash and dry the parsley and mint thoroughly before chopping — water dilutes the dressing.",
            "Combine bulgur, parsley, mint, tomatoes, and spring onion in a wide bowl.",
            "Whisk lemon juice, olive oil, salt, and pepper, and pour over the salad.",
            "Toss gently and rest 10 minutes before serving so the bulgur drinks the dressing.",
        ],
        "translations": {
            "zh": {
                "title": "塔布勒沙拉",
                "description": "清爽的欧芹碎麦沙拉，搭配番茄、薄荷，并带有一丝柠檬的清新。",
            },
            "ja": {
                "title": "タブレサラダ",
                "description": "爽やかなパセリとブルグルのサラダ。トマト、ミント、そしてレモンのキリッとした風味が特徴です。",
            },
            "ko": {
                "title": "타불레 샐러드",
                "description": "상큼한 파슬리-불굴 샐러드에 토마토, 민트, 그리고 레몬의 신선한 풍미가 더해졌습니다.",
            },
            "vi": {
                "title": "Salad Tabbouleh",
            },
        },
    },
    {
        "title": "Kibbeh bil Sanieh",
        "description": "Layered bulgur and spiced lamb baked into a golden Lebanese tray.",
        "cuisine": "lebanese", "language": "en", "spice_level": 1,
        "prep": 40, "cook": 45, "servings": 6, "image": _img("kibbeh-bil-sanieh"),
        "tags": ["main course", "comfort", "make-ahead"],
        "ingredients": [
            {"quantity": 300, "unit": "g", "name": "fine bulgur, rinsed and drained"},
            {"quantity": 500, "unit": "g", "name": "lean lamb (or beef), trimmed"},
            {"quantity": 1, "name": "small onion, quartered"},
            {"quantity": 1, "unit": "tsp", "name": "Lebanese seven-spice (baharat)"},
            {"quantity": 0.5, "unit": "tsp", "name": "ground cinnamon"},
            {"quantity": 0.25, "unit": "tsp", "name": "ground allspice"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 400, "unit": "g", "name": "ground lamb (for the filling)"},
            {"quantity": 1, "name": "large onion, finely chopped"},
            {"quantity": 80, "unit": "g", "name": "pine nuts"},
            {"quantity": 3, "unit": "tbsp", "name": "extra-virgin olive oil"},
        ],
        "steps": [
            "Soak bulgur 20 minutes in cold water; squeeze dry.",
            "Pulse lamb chunks, quartered onion, baharat, cinnamon, allspice, and salt in a processor with the bulgur until smooth — this is the kibbeh shell.",
            "Brown ground lamb with chopped onion and a pinch of salt in 2 tbsp olive oil until dry; toast the pine nuts and stir in.",
            "Press half the kibbeh shell into a buttered 28cm round pan, spread the filling, then top with the rest of the shell, smoothing the surface.",
            "Score into diamonds with a wet knife and drizzle with the remaining olive oil.",
            "Bake at 200 C for 35-40 minutes until the surface is deep golden; rest 10 minutes before cutting.",
        ],
        "translations": {
            "zh": {
                "title": "烤盘基贝",
                "description": "黎巴嫩传统烤盘料理：布格麦与香料羊肉层层堆叠，烤至金黄。",
            },
            "ja": {
                "title": "キッベ・ビル・サニエ",
                "description": "ブルグルとスパイスを効かせた羊肉を層に重ね、香ばしく焼き上げたレバノンの郷土料理。",
            },
            "ko": {
                "title": "키베 빌 사니예",
                "description": "불구르와 향신료를 입힌 양고기를 층층이 쌓아 노릇하게 구워내는 레바논 가정식.",
            },
            "vi": {
                "title": "Kibbeh nướng khay",
                "description": "Món bánh lúa mì bulgur và thịt cừu tẩm gia vị xếp lớp, nướng vàng theo lối Liban truyền thống.",
            },
        },
    },
    # ---- Turkish ----
    {
        "title": "Adana Kebab",
        "description": "Hand-minced lamb skewers seasoned with red pepper and sumac, grilled hot.",
        "cuisine": "turkish", "language": "en", "spice_level": 2,
        "prep": 30, "cook": 12, "servings": 4, "image": _img("adana-kebab"),
        "tags": ["main course", "grill", "weekend"],
        "ingredients": [
            {"quantity": 700, "unit": "g", "name": "lamb shoulder, hand-chopped or coarsely ground"},
            {"quantity": 150, "unit": "g", "name": "lamb tail fat (or beef suet)"},
            {"quantity": 2, "unit": "tbsp", "name": "Turkish red pepper paste (biber salçası)"},
            {"quantity": 2, "unit": "tsp", "name": "Aleppo pepper flakes"},
            {"quantity": 1, "unit": "tsp", "name": "sumac, plus more for serving"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 0.5, "unit": "tsp", "name": "ground cumin"},
            {"quantity": 4, "name": "garlic cloves, grated"},
            {"name": "flat skewers and lavash to serve"},
        ],
        "steps": [
            "Chop the lamb and fat together with a heavy knife on a board until they bind into a sticky paste.",
            "Knead in pepper paste, Aleppo pepper, sumac, salt, cumin, and garlic for 5 minutes; chill 30 minutes.",
            "Wet your hands and mold the mixture in long ribbons onto flat skewers, pressing firmly so it grips.",
            "Heat a charcoal grill until the coals glow white-grey, or use a heavy ridged pan over high heat.",
            "Grill 3 minutes per side, turning twice, until the surface is deeply charred and the inside is just cooked.",
            "Rest the skewers on warm lavash, dust with extra sumac, and serve with grilled tomatoes and onions.",
        ],
        "translations": {
            "zh": {
                "title": "阿达纳烤肉串",
                "description": "手剁羔羊肉串以红辣椒与漆树粉调味，明火炙烤至焦香四溢。",
            },
            "ja": {
                "title": "アダナ・ケバブ",
                "description": "手で叩いた仔羊肉に赤唐辛子とスマックを効かせ、強火でしっかり焼き上げる串焼き。",
            },
            "ko": {
                "title": "아다나 케밥",
                "description": "다진 양고기에 붉은 고추와 수막을 듬뿍 넣어 강한 불에 구워내는 터키식 꼬치구이.",
            },
            "vi": {
                "title": "Xiên cừu Adana",
                "description": "Thịt cừu băm tay tẩm ớt đỏ và sumac, nướng than nóng cho cháy cạnh thơm lừng.",
            },
        },
    },
    {
        "title": "Lahmacun",
        "description": "Thin Turkish flatbreads topped with spiced minced lamb, parsley, and lemon.",
        "cuisine": "turkish", "language": "en", "spice_level": 1,
        "prep": 90, "cook": 20, "servings": 4, "image": _img("lahmacun"),
        "tags": ["main course", "flatbread", "weekend"],
        "ingredients": [
            {"quantity": 300, "unit": "g", "name": "bread flour"},
            {"quantity": 180, "unit": "ml", "name": "warm water"},
            {"quantity": 1, "unit": "tsp", "name": "instant yeast"},
            {"quantity": 1, "unit": "tsp", "name": "salt (for dough)"},
            {"quantity": 300, "unit": "g", "name": "lean minced lamb"},
            {"quantity": 1, "name": "small onion, very finely chopped"},
            {"quantity": 1, "name": "ripe tomato, finely chopped"},
            {"quantity": 1, "unit": "tbsp", "name": "Turkish red pepper paste"},
            {"quantity": 2, "unit": "tsp", "name": "Aleppo pepper flakes"},
            {"quantity": 1, "unit": "small bunch", "name": "flat-leaf parsley, chopped"},
            {"quantity": 1, "name": "lemon, cut into wedges"},
        ],
        "steps": [
            "Combine flour, water, yeast, and salt; knead 8 minutes until smooth. Cover and rise 1 hour.",
            "Mash lamb, onion, tomato, pepper paste, Aleppo pepper, half the parsley, salt, and a glug of oil into a wet paste.",
            "Divide dough into 8 balls. Roll each as thin as a CD on a floured surface — almost see-through.",
            "Smear a thin layer of the lamb mixture over each disc, edge to edge.",
            "Slide onto a hot pizza stone or upside-down baking sheet at 250 C and bake 4-5 minutes until the rim is just blistered.",
            "Top with remaining parsley, squeeze with lemon, and roll up to eat warm.",
        ],
        "translations": {
            "zh": {
                "title": "土耳其肉饼",
                "description": "薄如纸的土耳其薄饼上铺香料羊肉碎，撒上欧芹和柠檬汁。",
            },
            "ja": {
                "title": "ラフマジュン",
                "description": "薄く伸ばした生地にスパイスたっぷりの仔羊肉をのせ、パセリとレモンを添える、トルコの薄焼きピザ。",
            },
            "ko": {
                "title": "라흐마준",
                "description": "얇게 민 반죽 위에 향신료 양념한 양고기를 펴 바른 터키식 플랫브레드. 파슬리와 레몬을 곁들여 먹는다.",
            },
            "vi": {
                "title": "Bánh dẹt Lahmacun",
                "description": "Bánh dẹt Thổ Nhĩ Kỳ phết thịt cừu tẩm gia vị, rắc ngò tây và vắt chanh tươi.",
            },
        },
    },
    {
        "title": "Baklava",
        "description": "Layers of crisp phyllo and pistachio bound with warm rosewater syrup.",
        "cuisine": "turkish", "language": "en", "spice_level": 0,
        "prep": 30, "cook": 50, "servings": 12, "image": _img("baklava"),
        "tags": ["dessert", "celebration", "make-ahead"],
        "ingredients": [
            {"quantity": 1, "unit": "packet", "name": "phyllo pastry (about 450 g), thawed"},
            {"quantity": 250, "unit": "g", "name": "unsalted butter, clarified"},
            {"quantity": 350, "unit": "g", "name": "raw pistachios, finely chopped"},
            {"quantity": 50, "unit": "g", "name": "caster sugar (for the nuts)"},
            {"quantity": 0.5, "unit": "tsp", "name": "ground cardamom"},
            {"quantity": 400, "unit": "g", "name": "granulated sugar (for the syrup)"},
            {"quantity": 200, "unit": "ml", "name": "water"},
            {"quantity": 2, "unit": "tbsp", "name": "lemon juice"},
            {"quantity": 1, "unit": "tsp", "name": "rosewater"},
        ],
        "steps": [
            "Make the syrup: simmer sugar, water, and lemon juice 10 minutes; off the heat stir in rosewater. Cool completely.",
            "Mix chopped pistachios with caster sugar and cardamom.",
            "Brush a 30x20 cm tin with butter. Layer 8 sheets of phyllo, brushing butter between each.",
            "Scatter half the pistachios, layer 6 more buttered sheets, scatter remaining pistachios, then finish with 8 more buttered sheets.",
            "Score into diamonds with a sharp knife, all the way to the bottom.",
            "Bake at 170 C for 45-50 minutes until deep golden; immediately pour the cold syrup over the hot baklava and rest 6 hours before serving.",
        ],
        "translations": {
            "zh": {
                "title": "果仁蜜饼",
                "description": "层层酥皮夹满开心果碎，浇上温热的玫瑰糖浆。",
            },
            "ja": {
                "title": "バクラヴァ",
                "description": "サクサクのフィロ生地にピスタチオを重ね、ローズウォーターのシロップをかけた中東の伝統菓子。",
            },
            "ko": {
                "title": "바클라바",
                "description": "겹겹이 쌓은 필로 도우 사이에 피스타치오를 채우고, 따뜻한 장미수 시럽을 부어낸 중동의 전통 디저트.",
            },
            "vi": {
                "title": "Bánh Baklava",
                "description": "Bánh phyllo giòn xếp lớp với hồ trăn nghiền, tưới si-rô hoa hồng còn ấm.",
            },
        },
    },
    # ---- Moroccan ----
    {
        "title": "Chicken Tagine with Preserved Lemon and Olives",
        "description": "Slow-braised chicken with saffron, ginger, preserved lemon, and green olives.",
        "cuisine": "moroccan", "language": "en", "spice_level": 1,
        "prep": 20, "cook": 70, "servings": 4, "image": _img("chicken-tagine"),
        "tags": ["main course", "braise", "weekend"],
        "ingredients": [
            {"quantity": 8, "name": "bone-in chicken thighs"},
            {"quantity": 2, "name": "onions, sliced into half-moons"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, grated"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger, grated"},
            {"quantity": 1, "unit": "pinch", "name": "saffron threads"},
            {"quantity": 1, "unit": "tsp", "name": "ground cumin"},
            {"quantity": 1, "unit": "tsp", "name": "sweet paprika"},
            {"quantity": 0.5, "unit": "tsp", "name": "turmeric"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 2, "name": "preserved lemons, pulp discarded, rind sliced"},
            {"quantity": 100, "unit": "g", "name": "cracked green olives"},
            {"quantity": 1, "unit": "small bunch", "name": "fresh cilantro, chopped"},
            {"quantity": 3, "unit": "tbsp", "name": "olive oil"},
        ],
        "steps": [
            "Pat chicken dry and rub with cumin, paprika, turmeric, salt, garlic, and ginger.",
            "Heat olive oil in a tagine or heavy casserole over medium heat; brown chicken on the skin side 6 minutes.",
            "Add onions and a splash of water; cook until soft, 8 minutes.",
            "Bloom saffron in 2 tbsp warm water and pour over chicken with another 300 ml water.",
            "Cover and simmer gently 45 minutes, turning chicken halfway through.",
            "Stir in preserved lemon, olives, and half the cilantro; simmer uncovered 10 minutes to reduce.",
            "Scatter remaining cilantro and serve with crusty bread or couscous.",
        ],
        "translations": {
            "zh": {
                "title": "腌柠檬橄榄塔吉鸡",
                "description": "鸡腿与藏红花、姜、腌柠檬和绿橄榄共同慢炖，香气浓郁。",
            },
            "ja": {
                "title": "鶏のタジン 塩漬けレモンとオリーブ煮",
                "description": "サフラン、生姜、塩漬けレモン、グリーンオリーブと鶏腿肉をじっくり煮込んだモロッコの煮込み料理。",
            },
            "ko": {
                "title": "치킨 타진 (절임 레몬·올리브)",
                "description": "사프란과 생강, 절임 레몬, 그린 올리브를 넣고 닭다리살을 은근히 졸여낸 모로코식 찜요리.",
            },
            "vi": {
                "title": "Gà hầm Tagine chanh muối ô-liu",
                "description": "Đùi gà hầm chậm cùng nghệ tây, gừng, chanh muối Maroc và ô-liu xanh thơm lừng.",
            },
        },
    },
    {
        "title": "Moroccan Lamb Couscous",
        "description": "Friday couscous with seven vegetables piled on tender lamb shoulder.",
        "cuisine": "moroccan", "language": "en", "spice_level": 1,
        "prep": 30, "cook": 120, "servings": 6, "image": _img("lamb-couscous"),
        "tags": ["main course", "celebration", "make-ahead"],
        "ingredients": [
            {"quantity": 1, "unit": "kg", "name": "lamb shoulder, cut into large cubes"},
            {"quantity": 2, "name": "onions, chopped"},
            {"quantity": 2, "unit": "tbsp", "name": "olive oil"},
            {"quantity": 1, "unit": "tsp", "name": "turmeric"},
            {"quantity": 1, "unit": "tsp", "name": "ground ginger"},
            {"quantity": 1, "unit": "tsp", "name": "ras el hanout"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 2, "name": "carrots, halved lengthwise"},
            {"quantity": 2, "name": "turnips, peeled and quartered"},
            {"quantity": 1, "name": "small cabbage, cut into wedges"},
            {"quantity": 2, "name": "zucchini, halved"},
            {"quantity": 200, "unit": "g", "name": "pumpkin or butternut, in chunks"},
            {"quantity": 1, "unit": "can", "name": "chickpeas, drained"},
            {"quantity": 400, "unit": "g", "name": "medium couscous"},
            {"quantity": 30, "unit": "g", "name": "unsalted butter"},
            {"quantity": 1, "unit": "small bunch", "name": "fresh cilantro, tied"},
        ],
        "steps": [
            "Sear lamb in olive oil in a large pot until browned all over.",
            "Add onions and spices; cook 5 minutes until fragrant.",
            "Pour in 1.5 L water with the cilantro bunch; simmer covered for 60 minutes.",
            "Add carrots and turnips; simmer 20 minutes. Add cabbage, zucchini, pumpkin, and chickpeas; simmer 20 minutes more until everything is tender.",
            "Meanwhile, dampen couscous with water and 1 tsp salt; steam over the broth (or in a steamer) for 15 minutes; rest, fluff with butter, steam 10 minutes more.",
            "Pile couscous on a wide platter, crown with lamb and vegetables, and ladle broth over the top.",
        ],
        "translations": {
            "zh": {
                "title": "摩洛哥羊肉古斯古斯",
                "description": "星期五的古斯古斯，七种蔬菜堆叠在鲜嫩羊肩肉上。",
            },
            "ja": {
                "title": "モロッコ風ラム肉クスクス",
                "description": "柔らかいラム肉の肩ロースに、7種類の野菜をたっぷり乗せた金曜日のクスクス。",
            },
            "ko": {
                "title": "모로코 양고기 쿠스쿠스",
                "description": "부드러운 양어깨살 위에 일곱 가지 채소가 듬뿍 올라간 금요일의 쿠스쿠스.",
            },
            "vi": {
                "title": "Couscous cừu kiểu Maroc",
            },
        },
    },
    {
        "title": "Harira",
        "description": "Ramadan tomato-lentil-chickpea soup finished with lemon, cilantro, and a swirl of flour.",
        "cuisine": "moroccan", "language": "en", "spice_level": 1,
        "prep": 20, "cook": 75, "servings": 6, "image": _img("harira"),
        "tags": ["soup", "comfort", "make-ahead"],
        "ingredients": [
            {"quantity": 250, "unit": "g", "name": "lamb or beef, diced small"},
            {"quantity": 1, "unit": "tbsp", "name": "olive oil"},
            {"quantity": 1, "name": "onion, finely chopped"},
            {"quantity": 2, "unit": "stalks", "name": "celery, finely chopped"},
            {"quantity": 1, "unit": "tsp", "name": "ground ginger"},
            {"quantity": 1, "unit": "tsp", "name": "ground turmeric"},
            {"quantity": 1, "unit": "tsp", "name": "ground cinnamon"},
            {"quantity": 1, "unit": "tsp", "name": "ras el hanout"},
            {"quantity": 1, "unit": "can", "name": "chopped tomatoes"},
            {"quantity": 2, "unit": "tbsp", "name": "tomato paste"},
            {"quantity": 150, "unit": "g", "name": "brown or green lentils, rinsed"},
            {"quantity": 1, "unit": "can", "name": "chickpeas, drained"},
            {"quantity": 80, "unit": "g", "name": "broken vermicelli pasta"},
            {"quantity": 2, "unit": "tbsp", "name": "all-purpose flour"},
            {"quantity": 1, "unit": "small bunch", "name": "cilantro and parsley, chopped"},
            {"quantity": 1, "name": "lemon, cut in wedges"},
        ],
        "steps": [
            "Brown meat in olive oil. Add onion and celery; soften 5 minutes.",
            "Stir in ginger, turmeric, cinnamon, ras el hanout, tomatoes, tomato paste, and 1.5 L water.",
            "Add lentils and simmer 40 minutes until tender.",
            "Add chickpeas and broken vermicelli; simmer 8 minutes more.",
            "Whisk flour with 150 ml cold water; pour into the soup in a thin stream, stirring constantly, and simmer 5 minutes until it thickens slightly.",
            "Stir in chopped herbs, taste for salt, and serve with lemon wedges and dates on the side.",
        ],
        "translations": {
            "zh": {
                "title": "哈利拉汤",
                "description": "斋月期间享用的番茄扁豆鹰嘴豆汤，以柠檬、香菜提味，并以面粉勾芡，口感浓郁。",
            },
            "ja": {
                "title": "ハリラスープ",
                "description": "ラマダンで親しまれる、トマト、レンズ豆、ひよこ豆のスープ。レモンとコリアンダーの香りを添え、小麦粉でとろみをつけた一品です。",
            },
            "ko": {
                "title": "하리라",
                "description": "라마단 기간에 즐겨 찾는 토마토, 렌틸콩, 병아리콩 수프. 레몬과 고수로 상큼함을 더하고 밀가루로 부드러운 농도를 냈습니다.",
            },
            "vi": {
                "title": "Súp Harira",
            },
        },
    },
    # ---- Ethiopian ----
    {
        "title": "Doro Wat",
        "description": "Slow-cooked chicken stew built on caramelized onions, berbere, and spiced butter.",
        "cuisine": "ethiopian", "language": "en", "spice_level": 3,
        "prep": 30, "cook": 100, "servings": 4, "image": _img("doro-wat"),
        "tags": ["main course", "celebration", "make-ahead"],
        "ingredients": [
            {"quantity": 4, "name": "large onions, very finely chopped"},
            {"quantity": 60, "unit": "g", "name": "niter kibbeh (Ethiopian spiced clarified butter)"},
            {"quantity": 4, "unit": "tbsp", "name": "berbere spice blend"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, grated"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger, grated"},
            {"quantity": 8, "name": "bone-in chicken thighs, skin removed"},
            {"quantity": 1, "name": "lemon, juiced"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 4, "name": "hard-boiled eggs, peeled and scored"},
            {"quantity": 250, "unit": "ml", "name": "water or chicken stock"},
        ],
        "steps": [
            "Toss chicken with lemon juice and salt; rest 15 minutes.",
            "In a heavy pot, dry-cook onions over medium heat for 25 minutes, stirring often, until they collapse into a dark sticky base — no fat yet.",
            "Stir in niter kibbeh, berbere, garlic, and ginger; cook 5 minutes until the paste deepens in color.",
            "Add chicken and turn to coat in the sauce; add water and simmer covered 45 minutes.",
            "Add eggs, baste with sauce, and simmer 15 minutes more uncovered to thicken.",
            "Serve over injera with a side of gomen (collards) for the full meal.",
        ],
        "translations": {
            "zh": {
                "title": "多罗瓦特",
                "description": "埃塞俄比亚国菜：洋葱、贝贝瑞辣椒粉与香料黄油慢炖出的鸡肉浓汤。",
            },
            "ja": {
                "title": "ドロワット",
                "description": "玉ねぎを飴色に炒め、ベルベレと香味バターでじっくり煮込むエチオピアの国民的鶏煮込み。",
            },
            "ko": {
                "title": "도로 와트",
                "description": "양파를 진하게 볶고 베르베레와 향신 버터로 닭을 끓여내는 에티오피아의 대표 요리.",
            },
            "vi": {
                "title": "Gà hầm Doro Wat",
                "description": "Món quốc hồn Ethiopia: gà hầm trên nền hành caramen, ớt berbere và bơ tinh ướp gia vị.",
            },
        },
    },
    {
        "title": "Misir Wat",
        "description": "Berbere-spiced red lentil stew, deep and silky from slow-cooked onions.",
        "cuisine": "ethiopian", "language": "en", "spice_level": 2,
        "prep": 10, "cook": 45, "servings": 4, "image": _img("misir-wat"),
        "tags": ["main course", "comfort", "make-ahead"],
        "ingredients": [
            {"quantity": 250, "unit": "g", "name": "red lentils, rinsed"},
            {"quantity": 2, "name": "large onions, very finely chopped"},
            {"quantity": 4, "unit": "tbsp", "name": "berbere spice blend"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, grated"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger, grated"},
            {"quantity": 2, "unit": "tbsp", "name": "neutral oil or niter kibbeh"},
            {"quantity": 2, "unit": "tbsp", "name": "tomato paste"},
            {"quantity": 800, "unit": "ml", "name": "water"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
        ],
        "steps": [
            "Dry-cook the onions in a heavy pot over medium heat for 15 minutes, stirring often, until they soften and turn jammy.",
            "Add oil, garlic, ginger, and berbere; cook 3 minutes until the spice darkens.",
            "Stir in tomato paste and let it sizzle briefly.",
            "Add lentils, water, and salt; bring to a gentle simmer.",
            "Cook uncovered 25-30 minutes, stirring occasionally, until the lentils break down into a velvety stew.",
            "Taste for salt and serve over injera with extra niter kibbeh on top, if you like.",
        ],
        "translations": {
            "zh": {
                "title": "米西尔瓦特红扁豆炖菜",
                "description": "柏柏尔香料红扁豆炖菜，慢炖洋葱带来醇厚丝滑的口感。",
            },
            "ja": {
                "title": "ミシルワット",
                "description": "ベルベレスパイスで風味付けされた赤レンズ豆のシチュー。時間をかけて煮込んだ玉ねぎが、奥深く滑らかな舌触りをもたらします。",
            },
            "ko": {
                "title": "미시르 왓",
                "description": "베르베레 향신료로 양념한 붉은 렌틸콩 스튜. 천천히 익힌 양파가 깊고 부드러운 풍미를 선사합니다.",
            },
            "vi": {
                "title": "Món hầm đậu lăng đỏ Ethiopia",
                "description": "Món hầm đậu lăng đỏ đậm đà gia vị Berbere, có độ sánh mịn và hương vị sâu lắng từ hành tây được nấu chậm.",
            },
        },
    },
    {
        "title": "Injera",
        "description": "Sourdough teff flatbread with a signature spongy crumb and tangy snap.",
        "cuisine": "ethiopian", "language": "en", "spice_level": 0,
        "prep": 20, "cook": 30, "servings": 8, "image": _img("injera"),
        "tags": ["bread", "ferment", "make-ahead"],
        "ingredients": [
            {"quantity": 400, "unit": "g", "name": "teff flour (ideally ivory teff)"},
            {"quantity": 100, "unit": "g", "name": "all-purpose flour (optional, for blended-style injera)"},
            {"quantity": 1, "unit": "L", "name": "warm water"},
            {"quantity": 1, "unit": "tsp", "name": "active sourdough starter or 0.5 tsp dry yeast"},
            {"quantity": 0.5, "unit": "tsp", "name": "salt"},
            {"name": "neutral oil for the pan"},
        ],
        "steps": [
            "Whisk teff flour, all-purpose flour (if using), warm water, and starter into a smooth, pourable batter.",
            "Cover loosely and rest at room temperature 36-48 hours until bubbly and pleasantly sour-smelling.",
            "Skim off any darker liquid, stir in salt, and adjust with water to a single-cream consistency.",
            "Heat a wide non-stick pan or mitad over medium-high; wipe with a light film of oil.",
            "Pour a ladle of batter from the outside in, spiraling toward the center; cover immediately and steam 2-3 minutes.",
            "Lift onto a tea towel as soon as the surface dries and the bubbles set. Stack and cool fully before rolling.",
        ],
        "translations": {
            "zh": {
                "title": "英杰拉",
                "description": "以苔麸自然发酵的埃塞俄比亚薄饼，海绵般松软，带着微微酸香。",
            },
            "ja": {
                "title": "インジェラ",
                "description": "テフ粉を自然発酵させて焼く、エチオピアのスポンジ状クレープ。ほのかな酸味が特徴。",
            },
            "ko": {
                "title": "인제라",
                "description": "테프 가루를 발효시켜 부쳐 내는 에티오피아의 스펀지처럼 폭신한 신맛 플랫브레드.",
            },
            "vi": {
                "title": "Bánh dẹt Injera",
                "description": "Bánh dẹt lên men từ bột teff đặc trưng của Ethiopia, xốp như bọt biển và chua nhẹ thanh thoát.",
            },
        },
    },
    # ---- Filipino ----
    {
        "title": "Chicken Adobo",
        "description": "Soy-vinegar braised chicken with garlic, bay, and a heavy hand of black pepper.",
        "cuisine": "filipino", "language": "en", "spice_level": 0,
        "prep": 10, "cook": 45, "servings": 4, "image": _img("chicken-adobo"),
        "tags": ["main course", "weeknight", "make-ahead"],
        "ingredients": [
            {"quantity": 1, "unit": "kg", "name": "bone-in chicken thighs and drumsticks"},
            {"quantity": 120, "unit": "ml", "name": "soy sauce"},
            {"quantity": 120, "unit": "ml", "name": "white cane vinegar (or apple cider vinegar)"},
            {"quantity": 250, "unit": "ml", "name": "water"},
            {"quantity": 1, "unit": "head", "name": "garlic, cloves smashed"},
            {"quantity": 3, "name": "bay leaves"},
            {"quantity": 1, "unit": "tsp", "name": "whole black peppercorns, lightly crushed"},
            {"quantity": 1, "unit": "tbsp", "name": "brown sugar (optional, to balance)"},
            {"quantity": 1, "unit": "tbsp", "name": "neutral oil"},
        ],
        "steps": [
            "Combine chicken, soy sauce, vinegar, garlic, bay, peppercorns, and water in a pot. Marinate 30 minutes if you have time.",
            "Bring to a simmer uncovered — do NOT stir for the first 5 minutes (this lets the vinegar's raw edge cook off).",
            "Cover and simmer gently 30 minutes until the chicken is tender.",
            "Lift chicken out. Reduce the sauce over higher heat 10 minutes until syrupy; stir in sugar if using.",
            "Sear chicken pieces in a separate hot pan with the oil to crisp the skin, 4 minutes.",
            "Return chicken to the sauce, turn to glaze, and serve over rice.",
        ],
        "translations": {
            "zh": {
                "title": "菲式酱醋鸡",
                "description": "酱油与醋慢炖的菲律宾经典鸡肉，蒜香、月桂叶与黑胡椒交织。",
            },
            "ja": {
                "title": "チキンアドボ",
                "description": "醤油と酢でじっくり煮込むフィリピンの定番。にんにくとローリエ、黒胡椒をたっぷりと。",
            },
            "ko": {
                "title": "치킨 아도보",
                "description": "간장과 식초로 푹 졸여낸 필리핀의 대표 음식. 마늘과 월계수 잎, 통후추를 듬뿍 넣는다.",
            },
            "vi": {
                "title": "Gà kho Adobo",
                "description": "Gà kho theo lối Philippines với nước tương, giấm, tỏi, lá nguyệt quế và tiêu đen rang giã.",
            },
        },
    },
    {
        "title": "Sinigang na Hipon",
        "description": "Sour shrimp soup with tamarind, kangkong, and tomato — the Filipino comfort bowl.",
        "cuisine": "filipino", "language": "en", "spice_level": 1,
        "prep": 15, "cook": 25, "servings": 4, "image": _img("sinigang-hipon"),
        "tags": ["soup", "main course", "weeknight"],
        "ingredients": [
            {"quantity": 500, "unit": "g", "name": "head-on shrimp, deveined"},
            {"quantity": 2, "name": "ripe tomatoes, quartered"},
            {"quantity": 1, "name": "small onion, quartered"},
            {"quantity": 1, "name": "daikon radish, sliced into thick rounds"},
            {"quantity": 4, "name": "long beans (sitaw), cut into 5-cm lengths"},
            {"quantity": 1, "unit": "bunch", "name": "water spinach (kangkong), trimmed"},
            {"quantity": 1, "name": "long green chili (siling pansigang)"},
            {"quantity": 1, "unit": "packet", "name": "sinigang sa sampalok mix (40 g) or 100 ml fresh tamarind juice"},
            {"quantity": 1.5, "unit": "L", "name": "water"},
            {"quantity": 1, "unit": "tbsp", "name": "fish sauce (patis)"},
            {"name": "steamed rice, to serve"},
        ],
        "steps": [
            "Bring water, tomatoes, and onion to a simmer in a tall pot; cook 10 minutes until the tomato softens completely.",
            "Add daikon and simmer 5 minutes more.",
            "Stir in tamarind mix (or fresh tamarind), fish sauce, and the whole green chili.",
            "Drop in the long beans and shrimp; simmer just until the shrimp turn pink, 3-4 minutes.",
            "Off heat, plunge in the kangkong and cover for 1 minute so it wilts but stays bright.",
            "Taste — the broth should be assertively sour and lightly salty. Ladle over rice in deep bowls.",
        ],
        "translations": {
            "zh": {
                "title": "菲律宾酸虾汤",
                "description": "这道酸爽的虾汤，以罗望子、空心菜和番茄烹制而成，是菲律宾的暖心家常美味。",
            },
            "ja": {
                "title": "エビのシニガン",
                "description": "タマリンド、空芯菜、トマトが効いた酸味豊かなエビスープ。フィリピンの心安らぐ一杯です。",
            },
            "ko": {
                "title": "새우 시니강",
                "description": "타마린드, 공심채, 토마토로 맛을 낸 새콤한 새우 수프 — 필리핀의 따뜻한 위로가 되는 한 그릇입니다.",
            },
            "vi": {
                "title": "Súp tôm chua Sinigang",
            },
        },
    },
    {
        "title": "Lumpiang Shanghai",
        "description": "Skinny, crispy Filipino pork spring rolls served with sweet chili.",
        "cuisine": "filipino", "language": "en", "spice_level": 0,
        "prep": 35, "cook": 20, "servings": 6, "image": _img("lumpia-shanghai"),
        "tags": ["appetizer", "party", "make-ahead"],
        "ingredients": [
            {"quantity": 500, "unit": "g", "name": "ground pork (about 80/20)"},
            {"quantity": 1, "name": "small carrot, finely grated"},
            {"quantity": 1, "name": "small onion, very finely chopped"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, grated"},
            {"quantity": 2, "name": "spring onions, finely sliced"},
            {"quantity": 1, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 1, "unit": "tsp", "name": "sesame oil"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 0.5, "unit": "tsp", "name": "black pepper"},
            {"quantity": 1, "name": "egg"},
            {"quantity": 30, "name": "lumpia (spring roll) wrappers, thawed"},
            {"name": "neutral oil for frying"},
            {"name": "sweet chili sauce, to serve"},
        ],
        "steps": [
            "Knead pork, carrot, onion, garlic, spring onion, soy, sesame oil, salt, pepper, and egg until sticky.",
            "Place a wrapper in front of you like a diamond. Spoon 2 tsp filling into a thin pencil along the bottom edge.",
            "Fold the bottom corner over the filling, tuck the sides in, and roll tightly. Seal the tip with a dab of water.",
            "Heat 3 cm oil in a wide pan to 170 C. Fry rolls in small batches 4-5 minutes, turning, until deep golden and crisp.",
            "Drain on a wire rack (paper towels make them soggy). Cut on the bias for the photo-ready angle.",
            "Serve hot with sweet chili sauce; uncooked rolls freeze beautifully — fry straight from frozen, add 2 minutes.",
        ],
        "translations": {
            "zh": {
                "title": "上海春卷（菲律宾式）",
                "description": "细长酥脆的菲式猪肉春卷，蘸甜辣酱一口一个停不下来。",
            },
            "ja": {
                "title": "ルンピア・シャンハイ",
                "description": "豚ひき肉を細く包んでカリッと揚げた、フィリピンの定番春巻き。スイートチリを添えて。",
            },
            "ko": {
                "title": "룸피아 상하이",
                "description": "필리핀식 가느다란 돼지고기 춘권. 스위트칠리 소스에 찍어 먹는 모임의 단골 메뉴.",
            },
            "vi": {
                "title": "Chả giò Lumpia Shanghai",
                "description": "Chả giò Philippines mảnh và giòn rụm nhân thịt heo, chấm tương ớt ngọt.",
            },
        },
    },
    # ---- Pakistani ----
    {
        "title": "Chicken Karahi",
        "description": "Wok-cooked chicken with ginger, tomato, and crushed green chilies — fast and fiery.",
        "cuisine": "pakistani", "language": "en", "spice_level": 2,
        "prep": 15, "cook": 35, "servings": 4, "image": _img("chicken-karahi"),
        "tags": ["main course", "weeknight", "fast"],
        "ingredients": [
            {"quantity": 1, "unit": "kg", "name": "bone-in chicken, cut into curry pieces"},
            {"quantity": 60, "unit": "ml", "name": "neutral oil or ghee"},
            {"quantity": 1, "unit": "tbsp", "name": "ginger-garlic paste"},
            {"quantity": 6, "name": "ripe tomatoes, roughly chopped"},
            {"quantity": 4, "name": "long green chilies, slit lengthwise"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 1, "unit": "tsp", "name": "red chili powder"},
            {"quantity": 1, "unit": "tsp", "name": "coriander seeds, crushed"},
            {"quantity": 1, "unit": "tsp", "name": "cumin seeds, toasted and crushed"},
            {"quantity": 1, "unit": "tsp", "name": "garam masala"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger, julienned (to finish)"},
            {"quantity": 1, "unit": "small bunch", "name": "fresh cilantro, chopped"},
        ],
        "steps": [
            "Heat oil in a karahi or wide wok until shimmering; add chicken and sear 6 minutes until lightly golden.",
            "Stir in ginger-garlic paste, salt, and red chili; cook 2 minutes.",
            "Add tomatoes and slit chilies; cover and simmer 12 minutes until tomatoes break down completely.",
            "Uncover and stir-fry over high heat 8 minutes, smashing tomato pieces, until oil separates and the gravy clings.",
            "Sprinkle in coriander, cumin, and garam masala; cook 2 minutes.",
            "Garnish with julienned ginger and cilantro. Serve straight from the pan with naan.",
        ],
        "translations": {
            "zh": {
                "title": "巴基斯坦卡拉希鸡",
                "description": "铁锅快炒鸡块，姜香、番茄与青椒辣味交织，火辣过瘾。",
            },
            "ja": {
                "title": "チキン・カラヒ",
                "description": "鉄鍋で一気に仕上げる、生姜・トマト・青唐辛子のパキスタン風スパイシーチキン。",
            },
            "ko": {
                "title": "치킨 카라히",
                "description": "철 웍에 빠르게 볶아낸 파키스탄식 매콤 치킨. 생강과 토마토, 청양고추가 화끈하게 어우러진다.",
            },
            "vi": {
                "title": "Gà chảo Karahi",
                "description": "Gà xào chảo gang nóng cùng gừng, cà chua và ớt xanh, đậm vị và cay nồng kiểu Pakistan.",
            },
        },
    },
    {
        "title": "Chicken Biryani",
        "description": "Layered basmati with marinated chicken, saffron, and crispy fried onions.",
        "cuisine": "pakistani", "language": "en", "spice_level": 2,
        "prep": 40, "cook": 65, "servings": 6, "image": _img("chicken-biryani"),
        "tags": ["main course", "celebration", "make-ahead"],
        "ingredients": [
            {"quantity": 1, "unit": "kg", "name": "bone-in chicken, cut into curry pieces"},
            {"quantity": 250, "unit": "g", "name": "thick yogurt"},
            {"quantity": 2, "unit": "tbsp", "name": "ginger-garlic paste"},
            {"quantity": 2, "unit": "tbsp", "name": "biryani masala"},
            {"quantity": 1, "unit": "tsp", "name": "red chili powder"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 0.5, "unit": "tsp", "name": "turmeric"},
            {"quantity": 4, "name": "large onions, thinly sliced"},
            {"quantity": 120, "unit": "ml", "name": "neutral oil"},
            {"quantity": 500, "unit": "g", "name": "aged basmati rice, soaked 30 minutes"},
            {"quantity": 4, "name": "green cardamom pods"},
            {"quantity": 1, "unit": "stick", "name": "cinnamon"},
            {"quantity": 3, "name": "cloves"},
            {"quantity": 1, "name": "bay leaf"},
            {"quantity": 1, "unit": "pinch", "name": "saffron, steeped in 3 tbsp warm milk"},
            {"quantity": 1, "unit": "small bunch", "name": "fresh mint and cilantro, chopped"},
        ],
        "steps": [
            "Marinate chicken with yogurt, ginger-garlic, biryani masala, chili, salt, and turmeric. Rest 30 minutes (overnight is better).",
            "Fry onions in oil over medium until deep brown and crisp, 15 minutes; drain on paper towels — these are your birista.",
            "In the same pot, brown the marinated chicken 5 minutes; cover and simmer in its own juices 15 minutes.",
            "Boil 2.5 L water with the whole spices and 1 tbsp salt; cook drained rice 6 minutes until 70% done, then drain.",
            "Layer over the chicken: half the rice, half the birista, half the herbs; repeat. Spoon saffron milk on top.",
            "Seal with a tight lid and cook on lowest heat 25 minutes (dum). Rest 10 minutes, then fluff gently from the side.",
        ],
        "translations": {
            "zh": {
                "title": "鸡肉比尔亚尼",
                "description": "层层叠加的香米饭与腌制鸡肉，藏红花香气与酥脆炸洋葱点缀其间。",
            },
            "ja": {
                "title": "チキンビリヤニ",
                "description": "マリネしたチキンとバスマティライスを重ね、サフランとフライドオニオンで香りを引き立てる炊き込みご飯。",
            },
            "ko": {
                "title": "치킨 비르야니",
                "description": "양념한 닭과 바스마티 쌀을 켜켜이 쌓고 사프란과 바삭한 튀긴 양파로 향을 더한 인도·파키스탄식 영양밥.",
            },
            "vi": {
                "title": "Cơm Biryani gà",
                "description": "Cơm basmati xếp lớp với gà ướp, nghệ tây và hành phi giòn rụm theo lối Pakistan/Ấn Độ.",
            },
        },
    },
    {
        "title": "Nihari",
        "description": "Slow-cooked beef shank stew thickened with toasted flour and finished with ginger and chili.",
        "cuisine": "pakistani", "language": "en", "spice_level": 2,
        "prep": 20, "cook": 240, "servings": 6, "image": _img("nihari"),
        "tags": ["main course", "celebration", "make-ahead"],
        "ingredients": [
            {"quantity": 1.2, "unit": "kg", "name": "beef shank, cut into 5-cm pieces (with marrow bones)"},
            {"quantity": 100, "unit": "ml", "name": "ghee or neutral oil"},
            {"quantity": 2, "name": "onions, thinly sliced"},
            {"quantity": 2, "unit": "tbsp", "name": "ginger-garlic paste"},
            {"quantity": 2, "unit": "tbsp", "name": "nihari masala (or 1 tbsp coriander + 1 tsp fennel + 1 tsp pepper + 1 tsp dry ginger)"},
            {"quantity": 1, "unit": "tsp", "name": "red chili powder"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 60, "unit": "g", "name": "whole-wheat flour"},
            {"quantity": 2, "unit": "L", "name": "water"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger, julienned (to finish)"},
            {"quantity": 2, "name": "green chilies, slit (to finish)"},
            {"quantity": 1, "name": "lemon, cut in wedges"},
        ],
        "steps": [
            "Fry sliced onions in ghee until deep golden; lift half out for garnish.",
            "Stir ginger-garlic paste into the remaining onions, then add beef and sear 8 minutes.",
            "Stir in nihari masala, chili, and salt; cook 2 minutes.",
            "Pour in water, bring to a simmer, cover and cook on the lowest possible flame for 3-4 hours, until the meat falls apart.",
            "Whisk flour with 200 ml cold water until lump-free; stream it into the pot, stirring constantly, and simmer 20 minutes more to thicken.",
            "Top each bowl with fried onions, ginger julienne, green chilies, and a squeeze of lemon. Serve with naan.",
        ],
        "translations": {
            "zh": {
                "title": "尼哈里炖牛肉",
                "description": "慢炖牛腱子肉，以烤面粉勾芡增稠，最后撒上姜丝和辣椒点缀。",
            },
            "ja": {
                "title": "ニハリ",
                "description": "じっくり煮込んだ牛すね肉のシチュー。炒った小麦粉でとろみをつけ、生姜と唐辛子で風味豊かに仕上げます。",
            },
            "ko": {
                "title": "니하리",
                "description": "오랜 시간 푹 끓여 부드러워진 소 사태살 스튜에, 볶은 밀가루로 농도를 맞추고 생강과 고추로 풍미를 더해 마무리합니다.",
            },
            "vi": {
                "title": "Nihari Bò hầm",
                "description": "Món bắp bò hầm nhừ, được làm sánh mịn với bột mì rang, và điểm xuyết gừng cùng ớt tươi để tăng thêm hương vị.",
            },
        },
    },
    # ---- Sri Lankan ----
    {
        "title": "Sri Lankan Chicken Curry",
        "description": "Coconut chicken curry darkened with roasted Sri Lankan curry powder and pandan.",
        "cuisine": "sri_lankan", "language": "en", "spice_level": 2,
        "prep": 15, "cook": 45, "servings": 4, "image": _img("sri-lankan-chicken-curry"),
        "tags": ["main course", "weeknight", "make-ahead"],
        "ingredients": [
            {"quantity": 1, "unit": "kg", "name": "bone-in chicken thighs and drumsticks"},
            {"quantity": 2, "unit": "tbsp", "name": "roasted Sri Lankan curry powder"},
            {"quantity": 1, "unit": "tsp", "name": "ground turmeric"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 2, "unit": "tbsp", "name": "coconut oil"},
            {"quantity": 1, "name": "onion, finely chopped"},
            {"quantity": 6, "unit": "cloves", "name": "garlic, sliced"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger, julienned"},
            {"quantity": 2, "name": "green chilies, slit"},
            {"quantity": 1, "name": "small piece pandan leaf (or 1 bay leaf)"},
            {"quantity": 1, "unit": "sprig", "name": "fresh curry leaves"},
            {"quantity": 1, "unit": "stick", "name": "cinnamon"},
            {"quantity": 400, "unit": "ml", "name": "coconut milk"},
            {"quantity": 1, "unit": "tbsp", "name": "tamarind concentrate (or lime juice)"},
        ],
        "steps": [
            "Toss chicken with curry powder, turmeric, and salt. Rest 15 minutes.",
            "Heat coconut oil in a heavy pot; pop curry leaves, pandan, and cinnamon 30 seconds.",
            "Add onion, garlic, ginger, and chilies; cook 5 minutes until soft and fragrant.",
            "Slide in the chicken and brown 5 minutes, turning to coat in the spice.",
            "Pour in coconut milk and 200 ml water; simmer covered 25 minutes until the chicken is tender.",
            "Stir in tamarind, simmer uncovered 5 minutes to reduce, and serve with rice or hoppers.",
        ],
        "translations": {
            "zh": {
                "title": "斯里兰卡咖喱鸡",
                "description": "椰香咖喱鸡，以烘烤过的斯里兰卡咖喱粉和斑斓叶增添风味与色泽。",
            },
            "ja": {
                "title": "スリランカ風チキンカレー",
                "description": "ココナッツ香るチキンカレー。ローストしたスリランカカレー粉とパンダンリーフで深みのある色と風味に仕上げました。",
            },
            "ko": {
                "title": "스리랑카 치킨 카레",
                "description": "구운 스리랑카 카레 가루와 판단 잎으로 깊은 맛과 색을 더한 코코넛 치킨 카레.",
            },
            "vi": {
                "title": "Cà ri gà Sri Lanka",
            },
        },
    },
    {
        "title": "Egg Hoppers",
        "description": "Bowl-shaped fermented rice-coconut pancake with a soft sunny egg at the bottom.",
        "cuisine": "sri_lankan", "language": "en", "spice_level": 0,
        "prep": 15, "cook": 25, "servings": 4, "image": _img("egg-hoppers"),
        "tags": ["breakfast", "ferment", "weekend"],
        "ingredients": [
            {"quantity": 250, "unit": "g", "name": "raw rice flour"},
            {"quantity": 30, "unit": "g", "name": "cooked white rice"},
            {"quantity": 250, "unit": "ml", "name": "coconut milk"},
            {"quantity": 200, "unit": "ml", "name": "soda water or thin coconut water"},
            {"quantity": 1, "unit": "tsp", "name": "instant yeast"},
            {"quantity": 1, "unit": "tsp", "name": "sugar"},
            {"quantity": 0.5, "unit": "tsp", "name": "salt"},
            {"quantity": 4, "name": "eggs"},
            {"name": "neutral oil for the pan"},
            {"name": "lunu miris (chili-onion sambol), to serve"},
        ],
        "steps": [
            "Blend rice flour, cooked rice, coconut milk, soda water, yeast, sugar, and salt into a smooth, single-cream batter.",
            "Cover and rest overnight at room temperature (8-10 hours), or 4 hours in a warm spot.",
            "Stir batter; if too thick, loosen with a splash of coconut water.",
            "Heat a small wok-shaped pan over medium; wipe with oil. Pour a ladle of batter and immediately swirl it up the sides to coat in a thin bowl.",
            "Crack an egg into the center, cover, and cook 3 minutes until the egg white sets but the yolk stays soft.",
            "Run a thin spatula around the edge and lift out in one piece. Serve hot with lunu miris.",
        ],
        "translations": {
            "zh": {
                "title": "斯里兰卡蛋窝薄饼",
                "description": "发酵米浆椰浆煎成碗形薄饼，中央卧一颗溏心蛋。",
            },
            "ja": {
                "title": "エッグホッパー",
                "description": "発酵させた米粉とココナッツミルクでお椀型に焼く、卵を落とした朝食用パンケーキ。",
            },
            "ko": {
                "title": "에그 호퍼",
                "description": "발효 쌀가루와 코코넛 밀크로 그릇 모양으로 부쳐 가운데 반숙 달걀을 얹은 스리랑카 아침 식사.",
            },
            "vi": {
                "title": "Bánh tô trứng Hopper",
                "description": "Bánh nước cốt dừa lên men đổ hình bát, đập một quả trứng lòng đào giữa bát.",
            },
        },
    },
    {
        "title": "Sri Lankan Dhal Curry",
        "description": "Coconut-milk red lentil curry tempered with curry leaves, mustard seeds, and pandan.",
        "cuisine": "sri_lankan", "language": "en", "spice_level": 1,
        "prep": 10, "cook": 25, "servings": 4, "image": _img("sri-lankan-dhal"),
        "tags": ["main course", "side dish", "weeknight"],
        "ingredients": [
            {"quantity": 200, "unit": "g", "name": "red lentils, rinsed"},
            {"quantity": 1, "unit": "tsp", "name": "ground turmeric"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 600, "unit": "ml", "name": "water"},
            {"quantity": 250, "unit": "ml", "name": "coconut milk"},
            {"quantity": 2, "unit": "tbsp", "name": "coconut oil"},
            {"quantity": 1, "unit": "tsp", "name": "black mustard seeds"},
            {"quantity": 1, "unit": "sprig", "name": "fresh curry leaves"},
            {"quantity": 1, "name": "small piece pandan leaf (optional)"},
            {"quantity": 1, "name": "small onion, sliced"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, sliced"},
            {"quantity": 1, "name": "long green chili, slit"},
        ],
        "steps": [
            "Simmer lentils with turmeric, salt, and water 15 minutes until soft and broken down.",
            "Stir in coconut milk and warm through 3 minutes; do not boil hard or it will split.",
            "Heat coconut oil in a small pan; add mustard seeds and let them pop.",
            "Add curry leaves, pandan, onion, garlic, and green chili; fry 4 minutes until the onion is golden.",
            "Pour the tempering over the dhal, stir once, and cover for 2 minutes so the flavors marry.",
            "Serve over rice with a spoonful of pol sambol on top, if you have it.",
        ],
        "translations": {
            "zh": {
                "title": "斯里兰卡扁豆咖喱",
                "description": "椰奶红扁豆咖喱，用咖喱叶、芥末籽和班兰叶爆香。",
            },
            "ja": {
                "title": "スリランカダールカレー",
                "description": "ココナッツミルク仕立ての赤レンズ豆カレー。カレーリーフ、マスタードシード、パンダンで香りを引き立てました。",
            },
            "ko": {
                "title": "스리랑카 달 카레",
                "description": "코코넛 밀크로 만든 붉은 렌틸콩 카레에 카레 잎, 겨자씨, 판단으로 향을 더했습니다.",
            },
            "vi": {
                "title": "Cà ri đậu lăng Sri Lanka",
            },
        },
    },
    # ---- Cambodian ----
    {
        "title": "Fish Amok",
        "description": "Coconut-curry fish mousse steamed in banana leaves, perfumed with kroeung.",
        "cuisine": "cambodian", "language": "en", "spice_level": 1,
        "prep": 30, "cook": 35, "servings": 4, "image": _img("fish-amok"),
        "tags": ["main course", "celebration", "steam"],
        "ingredients": [
            {"quantity": 600, "unit": "g", "name": "firm white fish fillets (catfish, snapper, cod), cut into 2-cm chunks"},
            {"quantity": 3, "unit": "stalks", "name": "lemongrass, white parts only, very finely sliced"},
            {"quantity": 4, "name": "kaffir lime leaves, stems removed"},
            {"quantity": 1, "unit": "thumb", "name": "fresh galangal, peeled"},
            {"quantity": 3, "name": "shallots, peeled"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, peeled"},
            {"quantity": 1, "unit": "tsp", "name": "ground turmeric"},
            {"quantity": 1, "name": "red chili, deseeded (more to taste)"},
            {"quantity": 400, "unit": "ml", "name": "thick coconut milk"},
            {"quantity": 2, "unit": "tbsp", "name": "fish sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "palm sugar (or brown sugar)"},
            {"quantity": 1, "name": "egg, lightly beaten"},
            {"quantity": 2, "unit": "cups", "name": "young spinach or noni leaves"},
            {"name": "banana leaves for cups, lightly wilted over a flame"},
        ],
        "steps": [
            "Pound or blend lemongrass, lime leaves, galangal, shallots, garlic, turmeric, and chili into a smooth kroeung paste.",
            "Stir half the coconut milk into the paste in a wide pan and simmer 5 minutes to bloom the spice.",
            "Season with fish sauce and palm sugar; off heat, fold in the remaining coconut milk and beaten egg.",
            "Toss fish gently in the curry mixture to coat without breaking.",
            "Line small bowls or banana-leaf cups with the spinach, fill with the fish mixture, and steam 20-25 minutes until set and pillowy.",
            "Finish with a swirl of thick coconut cream and a few extra lime-leaf shreds. Serve with jasmine rice.",
        ],
        "translations": {
            "zh": {
                "title": "柬埔寨蕉叶蒸鱼咖喱",
                "description": "椰浆咖喱鱼慕斯，包入蕉叶蒸至嫩滑，香茅与高良姜香气扑鼻。",
            },
            "ja": {
                "title": "フィッシュアモック",
                "description": "クロエングペーストとココナッツミルクで作る、バナナの葉で蒸し上げるカンボジアの繊細な魚のムース。",
            },
            "ko": {
                "title": "피쉬 아목",
                "description": "크로엉 페이스트와 코코넛 밀크로 만든 생선 무스를 바나나잎에 담아 부드럽게 쪄낸 캄보디아 대표 요리.",
            },
            "vi": {
                "title": "Cá hấp Amok",
                "description": "Mousse cá kiểu Campuchia hấp trong lá chuối, dậy hương kroeung và nước cốt dừa.",
            },
        },
    },
    {
        "title": "Lok Lak",
        "description": "Wok-seared beef cubes with a peppery lime dipping sauce — Phnom Penh's diner classic.",
        "cuisine": "cambodian", "language": "en", "spice_level": 1,
        "prep": 20, "cook": 10, "servings": 4, "image": _img("lok-lak"),
        "tags": ["main course", "weeknight", "fast"],
        "ingredients": [
            {"quantity": 500, "unit": "g", "name": "beef sirloin or tenderloin, cut into 2-cm cubes"},
            {"quantity": 2, "unit": "tbsp", "name": "oyster sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "light soy sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "fish sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "palm sugar"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, grated"},
            {"quantity": 2, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 1, "name": "small red onion, sliced into rings"},
            {"quantity": 2, "name": "tomatoes, cut into wedges"},
            {"quantity": 1, "name": "head lettuce, leaves separated"},
            {"quantity": 1, "unit": "tsp", "name": "freshly ground Kampot black pepper"},
            {"quantity": 1, "name": "lime"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"name": "4 fried eggs, to serve"},
            {"name": "steamed jasmine rice"},
        ],
        "steps": [
            "Marinate beef in oyster sauce, soy, fish sauce, palm sugar, and garlic for 15 minutes.",
            "Whisk lime juice, salt, and black pepper into a small dipping sauce — assertively peppery is the goal.",
            "Heat a wok over high heat until smoking; add oil and sear beef in two batches, 90 seconds each, leaving the interior just pink.",
            "Add onion and tomato in the last 30 seconds for a quick toss.",
            "Pile beef over lettuce leaves on individual plates with rice and a fried egg alongside.",
            "Pour the dipping sauce into ramekins so each diner can dunk every bite.",
        ],
        "translations": {
            "zh": {
                "title": "洛拉克牛肉",
                "description": "锅炒牛肉块，搭配胡椒青柠蘸酱，金边餐馆的经典美味。",
            },
            "ja": {
                "title": "ロックラック",
                "description": "中華鍋で香ばしく炒めた牛肉の角切りを、胡椒とライムのつけダレでいただく、プノンペン定番の食堂料理。",
            },
            "ko": {
                "title": "록락",
                "description": "웍에 구워낸 소고기 큐브에 후추 라임 디핑 소스를 곁들인, 프놈펜의 대표적인 식당 클래식.",
            },
            "vi": {
                "title": "Bò lúc lắc Campuchia",
            },
        },
    },
    {
        "title": "Kuy Teav",
        "description": "Clear pork-and-prawn noodle soup — the morning bowl of Phnom Penh.",
        "cuisine": "cambodian", "language": "en", "spice_level": 0,
        "prep": 20, "cook": 90, "servings": 4, "image": _img("kuy-teav"),
        "tags": ["soup", "breakfast", "weeknight"],
        "ingredients": [
            {"quantity": 1, "unit": "kg", "name": "pork bones (a mix of trotters and neck)"},
            {"quantity": 300, "unit": "g", "name": "pork shoulder"},
            {"quantity": 1, "name": "onion, halved and charred"},
            {"quantity": 2, "name": "dried squid (optional, classic touch)"},
            {"quantity": 1, "unit": "tbsp", "name": "rock sugar"},
            {"quantity": 2, "unit": "tbsp", "name": "fish sauce"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 300, "unit": "g", "name": "dried rice noodles, soaked"},
            {"quantity": 200, "unit": "g", "name": "shrimp, peeled and deveined"},
            {"quantity": 150, "unit": "g", "name": "minced pork (for topping)"},
            {"quantity": 2, "unit": "tbsp", "name": "fried garlic in oil (with the oil)"},
            {"quantity": 4, "name": "spring onions, sliced"},
            {"quantity": 1, "unit": "small bunch", "name": "cilantro and fresh chives, chopped"},
            {"quantity": 200, "unit": "g", "name": "bean sprouts (to serve)"},
            {"quantity": 1, "name": "lime, cut in wedges"},
        ],
        "steps": [
            "Blanch pork bones 3 minutes in boiling water, drain, and rinse to clean the broth.",
            "Simmer bones, pork shoulder, charred onion, and dried squid in 3 L water with the lid ajar for 70 minutes, skimming.",
            "Lift out pork shoulder; cool and slice thinly. Strain the broth and season with rock sugar, fish sauce, and salt.",
            "Quickly poach shrimp and minced pork in the strained broth; lift out and reserve.",
            "Soften noodles in boiling water 20 seconds, divide between bowls, and top with shrimp, sliced pork, minced pork, fried garlic with oil, and herbs.",
            "Ladle hot broth to cover and serve with bean sprouts and lime on the side for each diner to finish their own bowl.",
        ],
        "translations": {
            "zh": {
                "title": "金边粿条汤",
                "description": "柬埔寨清晨第一碗：清亮的猪骨汤底，搭配鲜虾、猪肉与柔滑米粉。",
            },
            "ja": {
                "title": "クイティウ（プノンペン米麺スープ）",
                "description": "豚骨を長時間煮出した澄んだスープに、エビと豚肉、米麺をたっぷり。プノンペンの朝の一杯。",
            },
            "ko": {
                "title": "꾸이떠우 (프놈펜식 쌀국수)",
                "description": "돼지뼈를 오래 우려낸 맑은 국물에 새우와 돼지고기, 부드러운 쌀국수를 가득 담은 프놈펜의 아침 한 그릇.",
            },
            "vi": {
                "title": "Hủ tiếu Nam Vang",
                "description": "Hủ tiếu kiểu Phnom Penh: nước dùng heo trong vắt, tôm thịt đầy đặn, sợi mềm mượt — món sáng quen thuộc của người Campuchia.",
            },
        },
    },
    # ====================================================================
    # v4 Phase 2 expansion: 36 recipes for 12 more cuisines (5 catalog
    # gaps + 7 newly-added cuisines from the catalog expansion).
    # ====================================================================
    # ---- Greek ----
    {
        "title": "Pork Souvlaki",
        "description": "Lemon-oregano pork skewers char-grilled and rolled into pita with tzatziki.",
        "cuisine": "greek", "language": "en", "spice_level": 0,
        "prep": 25, "cook": 12, "servings": 4, "image": _img("souvlaki"),
        "tags": ["main course", "grill", "weeknight"],
        "ingredients": [
            {"quantity": 700, "unit": "g", "name": "pork shoulder, cut into 3-cm cubes"},
            {"quantity": 4, "unit": "tbsp", "name": "extra-virgin olive oil"},
            {"quantity": 3, "unit": "tbsp", "name": "lemon juice"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, grated"},
            {"quantity": 2, "unit": "tsp", "name": "dried oregano"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 0.5, "unit": "tsp", "name": "black pepper"},
            {"quantity": 4, "name": "warm pita breads"},
            {"quantity": 250, "unit": "g", "name": "tzatziki, to serve"},
            {"quantity": 1, "name": "red onion, sliced; tomato wedges"},
        ],
        "steps": [
            "Whisk olive oil, lemon juice, garlic, oregano, salt, and pepper.",
            "Toss pork cubes in the marinade and rest at least 30 minutes (overnight is better).",
            "Thread onto soaked wooden skewers, packing the cubes tightly.",
            "Grill over hot coals (or in a ridged pan) 3 minutes per side, turning twice, until charred and just cooked through.",
            "Rest skewers on warm pita 2 minutes so the bread soaks up the juices.",
            "Slide pork off the skewers and roll into pita with tzatziki, red onion, and tomato.",
        ],
        "translations": {
            "zh": {
                "title": "希腊烤肉串",
                "description": "柠檬牛至腌渍的猪肉串，炭火炙烤后裹入皮塔饼，淋上酸奶酱。",
            },
            "ja": {
                "title": "スブラキ（豚肉）",
                "description": "レモンとオレガノでマリネした豚肉を炭火で焼き、ピタパンに巻いてザジキを添えるギリシャの定番。",
            },
            "ko": {
                "title": "수블라키 (돼지고기)",
                "description": "레몬과 오레가노로 절인 돼지고기를 숯불에 구워 따뜻한 피타에 싸 차지키와 함께 즐기는 그리스 꼬치구이.",
            },
            "vi": {
                "title": "Xiên heo Souvlaki",
                "description": "Thịt heo ướp chanh và oregano nướng than, cuộn trong bánh pita với sốt tzatziki kiểu Hy Lạp.",
            },
        },
    },
    {
        "title": "Moussaka",
        "description": "Layered eggplant, spiced lamb, and creamy béchamel — Greece's Sunday lunch.",
        "cuisine": "greek", "language": "en", "spice_level": 1,
        "prep": 45, "cook": 75, "servings": 8, "image": _img("moussaka"),
        "tags": ["main course", "celebration", "make-ahead"],
        "ingredients": [
            {"quantity": 3, "name": "large eggplants, sliced 1 cm thick"},
            {"quantity": 2, "name": "large potatoes, sliced 0.5 cm thick"},
            {"quantity": 80, "unit": "ml", "name": "olive oil, plus more for brushing"},
            {"quantity": 700, "unit": "g", "name": "ground lamb (or beef)"},
            {"quantity": 1, "name": "large onion, finely chopped"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 2, "unit": "tbsp", "name": "tomato paste"},
            {"quantity": 1, "unit": "can", "name": "chopped tomatoes (400 g)"},
            {"quantity": 1, "unit": "tsp", "name": "ground cinnamon"},
            {"quantity": 0.5, "unit": "tsp", "name": "ground allspice"},
            {"quantity": 60, "unit": "g", "name": "butter (for béchamel)"},
            {"quantity": 60, "unit": "g", "name": "flour"},
            {"quantity": 700, "unit": "ml", "name": "warm whole milk"},
            {"quantity": 2, "name": "eggs, beaten"},
            {"quantity": 60, "unit": "g", "name": "kefalotyri or pecorino, grated"},
            {"name": "salt, pepper, freshly grated nutmeg"},
        ],
        "steps": [
            "Salt the eggplant slices and rest 20 minutes; pat dry. Brush with oil and roast at 220 C for 20 minutes.",
            "Boil potato slices 8 minutes until just tender; drain.",
            "Brown lamb in olive oil; add onion and garlic, cook 5 minutes. Stir in tomato paste, tomatoes, cinnamon, allspice, salt; simmer 25 minutes until thick.",
            "Make béchamel: melt butter, whisk in flour 1 minute, then stream in milk and cook to a thick sauce. Off heat, beat in eggs, half the cheese, salt, pepper, and nutmeg.",
            "Layer in a 30x22 cm dish: potato slices, half the eggplant, all the meat, remaining eggplant. Pour béchamel over, scatter remaining cheese.",
            "Bake at 180 C for 50-55 minutes until the top is deeply golden. Rest 30 minutes (do not skip — it slices clean only when set).",
        ],
        "translations": {
            "zh": {
                "title": "慕萨卡",
                "description": "层叠的茄子、香料羊肉和白酱烘焙",
            },
            "ja": {
                "title": "ムサカ",
                "description": "重ねたナス、香り高いラムとベシャメル焼き",
            },
            "ko": {
                "title": "무사카",
                "description": "층층이 쌓은 가지, 향신료 양고기와 베샤멜 구이",
            },
            "vi": {
                "title": "Mousaka kiểu Hy Lạp",
                "description": "Bánh trứng cà tím, cừu tẩm gia vị và sốt trắng nướng",
            },
        },
    },
    {
        "title": "Greek Salad",
        "description": "Tomato, cucumber, feta, and olives in olive oil and oregano — horiatiki, no lettuce.",
        "cuisine": "greek", "language": "en", "spice_level": 0,
        "prep": 15, "cook": 0, "servings": 4, "image": _img("greek-salad"),
        "tags": ["salad", "side dish", "quick"],
        "ingredients": [
            {"quantity": 4, "name": "ripe tomatoes, cut into wedges"},
            {"quantity": 1, "name": "cucumber, peeled in stripes and sliced"},
            {"quantity": 1, "name": "small red onion, thinly sliced"},
            {"quantity": 1, "name": "green bell pepper, cut into rings"},
            {"quantity": 200, "unit": "g", "name": "Greek feta, in one thick slab"},
            {"quantity": 100, "unit": "g", "name": "Kalamata olives"},
            {"quantity": 4, "unit": "tbsp", "name": "extra-virgin olive oil"},
            {"quantity": 1, "unit": "tbsp", "name": "red wine vinegar (optional)"},
            {"quantity": 1, "unit": "tsp", "name": "dried oregano"},
            {"name": "salt, pepper"},
        ],
        "steps": [
            "Salt the tomatoes lightly in a wide bowl and let them release juice 5 minutes.",
            "Add cucumber, red onion, and green pepper.",
            "Drizzle olive oil and vinegar over the vegetables; toss gently to coat — do not mash.",
            "Mound everything into a serving bowl.",
            "Lay the feta slab on top whole (do not crumble — it's the table centerpiece).",
            "Scatter olives, sprinkle oregano and pepper, and serve with crusty bread to mop the juices.",
        ],
        "translations": {
            "zh": {
                "title": "希腊沙拉",
                "description": "以番茄、黄瓜、羊乳酪和橄榄为主，淋上橄榄油和牛至调味——这道经典的希腊乡村沙拉不含生菜。",
            },
            "ja": {
                "title": "ホリアティキ（ギリシャ風サラダ）",
            },
            "ko": {
                "title": "그리스 호리아티키 샐러드",
                "description": "토마토, 오이, 페타 치즈, 칼라마타 올리브에 올리브 오일과 오레가노를 두른 양상추 없는 정통 샐러드.",
            },
            "vi": {
                "title": "Salad Hy Lạp Horiatiki",
            },
        },
    },
    # ---- Spanish ----
    {
        "title": "Paella Valenciana",
        "description": "Saffron rice with chicken, rabbit, green beans, and a coveted socarrat crust.",
        "cuisine": "spanish", "language": "en", "spice_level": 0,
        "prep": 25, "cook": 45, "servings": 6, "image": _img("paella"),
        "tags": ["main course", "celebration", "weekend"],
        "ingredients": [
            {"quantity": 4, "unit": "tbsp", "name": "olive oil"},
            {"quantity": 6, "name": "chicken thighs, bone-in"},
            {"quantity": 6, "name": "rabbit pieces (or 6 more chicken thighs)"},
            {"quantity": 200, "unit": "g", "name": "flat green beans (bajoqueta), trimmed"},
            {"quantity": 150, "unit": "g", "name": "garrofó (lima beans), cooked"},
            {"quantity": 2, "name": "ripe tomatoes, grated"},
            {"quantity": 1, "unit": "tsp", "name": "sweet paprika"},
            {"quantity": 1, "unit": "pinch", "name": "saffron threads"},
            {"quantity": 400, "unit": "g", "name": "bomba or Calasparra rice"},
            {"quantity": 1.2, "unit": "L", "name": "hot chicken stock"},
            {"quantity": 1, "unit": "sprig", "name": "fresh rosemary"},
            {"quantity": 1, "name": "lemon, cut in wedges"},
            {"name": "salt"},
        ],
        "steps": [
            "Heat oil in a 38-cm paella pan over medium-high; brown chicken and rabbit 8 minutes per side, season with salt, push to the rim.",
            "Add green beans and garrofó; sauté 4 minutes.",
            "Make a clearing in the center, add grated tomato and paprika, and cook 2 minutes until darkened.",
            "Toast the rice in the sofrito 1 minute, then pour in hot stock with bloomed saffron. Distribute rice evenly and DO NOT STIR after this point.",
            "Boil hard 10 minutes, then reduce to a low simmer for 8 more minutes; add rosemary on top.",
            "Crank heat for the last 90 seconds to form the socarrat (listen for crackle, smell for caramel). Rest 5 minutes covered with a towel before serving with lemon.",
        ],
        "translations": {
            "zh": {
                "title": "瓦伦西亚海鲜饭",
                "description": "藏红花米饭混合鸡肉、兔肉与扁豆，锅底煎出焦香的『socarrat』脆壳。",
            },
            "ja": {
                "title": "パエリア・バレンシアーナ",
                "description": "サフランライスに鶏肉と兎肉、平さやインゲンをのせ、底にできるおこげ「ソカラート」を楽しむバレンシア地方の伝統料理。",
            },
            "ko": {
                "title": "발렌시아 파에야",
                "description": "사프란을 입힌 쌀과 닭, 토끼고기, 깍지콩을 함께 익히고 바닥의 누룽지(소카랏)를 살려 짓는 발렌시아 전통 요리.",
            },
            "vi": {
                "title": "Cơm Paella Valencia",
                "description": "Cơm nghệ tây với gà, thỏ và đậu xanh dẹt, tạo lớp cháy giòn 'socarrat' đặc trưng dưới đáy chảo.",
            },
        },
    },
    {
        "title": "Tortilla Española",
        "description": "Slow-cooked potato and onion omelette — the Spanish bar staple eaten room-temperature.",
        "cuisine": "spanish", "language": "en", "spice_level": 0,
        "prep": 15, "cook": 35, "servings": 4, "image": _img("tortilla-espanola"),
        "tags": ["main course", "weeknight", "make-ahead"],
        "ingredients": [
            {"quantity": 600, "unit": "g", "name": "waxy potatoes, peeled, sliced 3 mm"},
            {"quantity": 2, "name": "yellow onions, thinly sliced"},
            {"quantity": 250, "unit": "ml", "name": "extra-virgin olive oil"},
            {"quantity": 6, "name": "large eggs"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
        ],
        "steps": [
            "In a 24-cm non-stick pan, gently confit potatoes and onions in the olive oil over low heat for 25-30 minutes — they should poach, not fry, until silky and just collapsing.",
            "Drain, reserving the oil, and lightly season the potatoes with half the salt.",
            "Beat eggs with the remaining salt; fold in the warm potatoes and onions and rest 5 minutes (this lets the egg soak in).",
            "Heat 2 tbsp of the reserved oil in the pan. Pour in the egg mixture and cook over medium-low 4 minutes, pulling edges in.",
            "Slide onto a flat plate, invert the pan over it, and flip back into the pan. Cook 3 more minutes for a creamy center, longer for set.",
            "Slide onto a board and rest 10 minutes; serve in wedges at room temperature with crusty bread.",
        ],
        "translations": {
            "zh": {
                "title": "西班牙土豆蛋饼",
                "description": "土豆与洋葱以橄榄油慢煎入味，再与鸡蛋同煎，是西班牙酒馆的常温经典。",
            },
            "ja": {
                "title": "トルティージャ・エスパニョーラ",
                "description": "じゃがいもと玉ねぎをオリーブオイルでじっくり火入れし、卵と合わせて焼く、スペインのバル定番。常温で味わいます。",
            },
            "ko": {
                "title": "토르티야 에스파뇰라",
                "description": "감자와 양파를 올리브 오일에 천천히 익히고 달걀과 함께 부쳐낸 스페인 바의 대표 안주. 미지근하게 즐긴다.",
            },
            "vi": {
                "title": "Trứng chiên khoai Tây Ban Nha",
                "description": "Khoai tây và hành tây được áp dầu ô-liu thật chậm rồi ốp với trứng — món bar truyền thống của người Tây Ban Nha, ăn lúc nguội.",
            },
        },
    },
    {
        "title": "Patatas Bravas",
        "description": "Crispy potato cubes drowned in smoky brava sauce and a swoosh of garlic aioli.",
        "cuisine": "spanish", "language": "en", "spice_level": 1,
        "prep": 15, "cook": 35, "servings": 4, "image": _img("patatas-bravas"),
        "tags": ["appetizer", "snack", "weekend"],
        "ingredients": [
            {"quantity": 1, "unit": "kg", "name": "starchy potatoes, peeled, cut into 3-cm cubes"},
            {"quantity": 500, "unit": "ml", "name": "olive oil for shallow frying"},
            {"quantity": 2, "unit": "tbsp", "name": "olive oil (for sauce)"},
            {"quantity": 1, "name": "small onion, finely chopped"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, sliced"},
            {"quantity": 2, "unit": "tsp", "name": "smoked paprika (pimentón)"},
            {"quantity": 0.5, "unit": "tsp", "name": "cayenne or hot paprika"},
            {"quantity": 1, "unit": "tbsp", "name": "tomato paste"},
            {"quantity": 2, "unit": "tbsp", "name": "sherry vinegar"},
            {"quantity": 250, "unit": "ml", "name": "chicken or vegetable stock"},
            {"quantity": 4, "unit": "tbsp", "name": "garlic aioli, to serve"},
            {"name": "flaky sea salt"},
        ],
        "steps": [
            "Boil potato cubes in salted water 6 minutes until edges are just fluffy; drain and dry on a tray for 15 minutes.",
            "Make brava sauce: sweat onion in 2 tbsp olive oil until soft, add garlic, both paprikas, and tomato paste; cook 2 minutes.",
            "Pour in vinegar and stock; simmer 10 minutes. Blend smooth and season; pass through a sieve for restaurant texture.",
            "Heat oil to 180 C in a wide pan. Fry potatoes in batches 5-6 minutes until deep golden and crisp.",
            "Drain on a wire rack and salt immediately.",
            "Pile on a warm plate, spoon brava over, and finish with aioli zigzags.",
        ],
        "translations": {
            "zh": {
                "title": "西班牙辣味土豆",
                "description": "香脆土豆块淋上烟熏辣味酱，再配上蒜香蛋黄酱。",
            },
            "ja": {
                "title": "パタタスブラバス",
                "description": "カリカリのポテトキューブに、スモーキーなブラバソースをたっぷりとかけ、ガーリックアイオリを添えました。",
            },
            "ko": {
                "title": "파타타스 브라바스",
                "description": "바삭한 감자 큐브에 스모키한 브라바 소스를 듬뿍 뿌리고, 마늘 아이올리를 곁들인 요리.",
            },
            "vi": {
                "title": "Khoai tây sốt Bravas",
                "description": "Những viên khoai tây giòn rụm đẫm sốt brava khói và kèm theo một lớp sốt aioli tỏi.",
            },
        },
    },
    # ---- Malaysian ----
    {
        "title": "Nasi Lemak",
        "description": "Coconut rice plated with sambal, fried anchovies, peanuts, cucumber, and a soft-boiled egg.",
        "cuisine": "malaysian", "language": "en", "spice_level": 2,
        "prep": 30, "cook": 35, "servings": 4, "image": _img("nasi-lemak"),
        "tags": ["breakfast", "main course", "weekend"],
        "ingredients": [
            {"quantity": 400, "unit": "g", "name": "jasmine rice, rinsed"},
            {"quantity": 400, "unit": "ml", "name": "coconut milk"},
            {"quantity": 100, "unit": "ml", "name": "water"},
            {"quantity": 1, "name": "small piece pandan leaf, tied in a knot"},
            {"quantity": 1, "unit": "thumb", "name": "ginger, smashed"},
            {"quantity": 1, "unit": "tsp", "name": "salt (for rice)"},
            {"quantity": 50, "unit": "g", "name": "dried anchovies (ikan bilis), rinsed and patted dry"},
            {"quantity": 60, "unit": "g", "name": "raw skinned peanuts"},
            {"quantity": 8, "name": "dried red chilies, soaked and seeded"},
            {"quantity": 4, "name": "shallots, chopped"},
            {"quantity": 2, "unit": "cloves", "name": "garlic"},
            {"quantity": 1, "unit": "tbsp", "name": "belacan (shrimp paste), toasted"},
            {"quantity": 2, "unit": "tbsp", "name": "tamarind concentrate"},
            {"quantity": 2, "unit": "tbsp", "name": "sugar"},
            {"quantity": 4, "name": "eggs, soft-boiled (6.5 minutes)"},
            {"quantity": 1, "name": "cucumber, sliced"},
        ],
        "steps": [
            "Cook rice with coconut milk, water, pandan, ginger, and salt in a rice cooker (or 18 minutes covered on the stove).",
            "Deep-fry anchovies in 1 cm hot oil 90 seconds until shatter-crisp; drain. Fry peanuts 2 minutes in the same oil; drain.",
            "Blend chilies, shallots, garlic, and belacan into a paste; fry in 3 tbsp oil over medium-low 15 minutes, stirring, until deep red and the oil splits.",
            "Stir tamarind, sugar, and 1 tsp salt into the sambal; cook 3 minutes more to a thick jam.",
            "Plate a mound of coconut rice, half the cucumber, peanuts, anchovies, a halved egg, and a generous spoon of sambal.",
            "Eat by mixing a little of everything in each bite — the contrast is the whole point.",
        ],
        "translations": {
            "zh": {
                "title": "椰香饭",
                "description": "椰香饭配以辣酱、炸小鱼、花生、黄瓜和半熟蛋",
            },
            "ja": {
                "title": "ナシレマック",
                "description": "ココナッツライスにサンバル、揚げアンチョビ、ピーナッツ、キュウリ、半熟タマゴをのせたマレーシア料理",
            },
            "ko": {
                "title": "나시레막",
                "description": "코코넛밥에 삼발, 튀긴 멸치, 땅콩, 오이, 반숙란을 얹은 말레이시아 요리",
            },
            "vi": {
                "title": "Cơm Lemak",
                "description": "Cơm dừa ăn kèm với sốt sambal, cá cơm chiên, lạc, dưa chuột và trứng luộc",
            },
        },
    },
    {
        "title": "Char Kway Teow",
        "description": "Smoky wok-fried flat rice noodles with prawns, lap cheong, egg, and bean sprouts.",
        "cuisine": "malaysian", "language": "en", "spice_level": 2,
        "prep": 20, "cook": 10, "servings": 2, "image": _img("char-kway-teow"),
        "tags": ["main course", "weeknight", "fast"],
        "ingredients": [
            {"quantity": 350, "unit": "g", "name": "fresh flat rice noodles (kway teow), loosened"},
            {"quantity": 2, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 1, "unit": "tbsp", "name": "garlic, minced"},
            {"quantity": 1, "name": "Chinese sausage (lap cheong), thinly sliced"},
            {"quantity": 8, "name": "medium prawns, peeled"},
            {"quantity": 2, "name": "eggs"},
            {"quantity": 1, "unit": "tbsp", "name": "thick dark soy sauce"},
            {"quantity": 2, "unit": "tsp", "name": "light soy sauce"},
            {"quantity": 1, "unit": "tsp", "name": "sambal oelek"},
            {"quantity": 1, "unit": "tsp", "name": "sugar"},
            {"quantity": 100, "unit": "g", "name": "bean sprouts"},
            {"quantity": 2, "name": "garlic chives, cut in 5-cm lengths"},
        ],
        "steps": [
            "Pre-mix the sauces and sugar in a small bowl — speed matters in a wok.",
            "Heat the wok until smoking; add oil and immediately fry lap cheong and garlic 30 seconds.",
            "Add prawns; toss 30 seconds until just pink.",
            "Push to one side; crack in eggs and scramble briefly.",
            "Add noodles and pour sauce over; toss with two spatulas in lifting motions for 60 seconds to develop wok hei.",
            "Toss in bean sprouts and chives for 20 seconds — they should stay crisp. Plate immediately.",
        ],
        "translations": {
            "zh": {
                "title": "马来西亚炒粿条",
                "description": "镬气十足的炒粿条，配虾仁、腊肠、鸡蛋与豆芽。",
            },
            "ja": {
                "title": "チャークイティオ",
                "description": "強火で炒め上げる平打ち米麺に、エビ・中華ソーセージ・卵・もやしを合わせるマレーシアの屋台炒め麺。",
            },
            "ko": {
                "title": "차 콰이 테오",
                "description": "강불에서 빠르게 볶아낸 납작한 쌀국수에 새우와 중국 소시지, 달걀과 숙주를 더한 말레이시아 노점 음식.",
            },
            "vi": {
                "title": "Phở xào Char Kway Teow",
                "description": "Phở dẹt xào lửa lớn với tôm, lạp xưởng, trứng và giá — món xào Mã Lai đậm vị 'wok hei'.",
            },
        },
    },
    {
        "title": "Curry Laksa",
        "description": "Spicy coconut-curry noodle soup with prawns, tofu puffs, and bean sprouts.",
        "cuisine": "malaysian", "language": "en", "spice_level": 3,
        "prep": 25, "cook": 30, "servings": 4, "image": _img("laksa"),
        "tags": ["soup", "main course", "dinner"],
        "ingredients": [
            {"quantity": 6, "name": "dried red chilies, soaked"},
            {"quantity": 4, "name": "shallots, peeled"},
            {"quantity": 3, "unit": "cloves", "name": "garlic"},
            {"quantity": 2, "unit": "stalks", "name": "lemongrass, white part, sliced"},
            {"quantity": 1, "unit": "thumb", "name": "galangal"},
            {"quantity": 1, "unit": "thumb", "name": "fresh turmeric (or 1 tsp ground)"},
            {"quantity": 6, "name": "candlenuts (or macadamia nuts)"},
            {"quantity": 1, "unit": "tbsp", "name": "belacan (shrimp paste), toasted"},
            {"quantity": 3, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 600, "unit": "ml", "name": "chicken or seafood stock"},
            {"quantity": 400, "unit": "ml", "name": "coconut milk"},
            {"quantity": 1, "unit": "tbsp", "name": "palm sugar"},
            {"quantity": 1, "unit": "tbsp", "name": "fish sauce"},
            {"quantity": 12, "name": "medium prawns, peeled"},
            {"quantity": 6, "name": "fried tofu puffs, halved"},
            {"quantity": 300, "unit": "g", "name": "fresh egg noodles + 200 g rice vermicelli, cooked"},
            {"quantity": 100, "unit": "g", "name": "bean sprouts"},
            {"quantity": 2, "name": "limes, cut in wedges"},
        ],
        "steps": [
            "Blend the spice paste (rempah) — chilies, shallots, garlic, lemongrass, galangal, turmeric, candlenuts, and belacan — with a splash of water.",
            "Fry the rempah in oil over medium 12 minutes, stirring, until deep red and aromatic and the oil splits.",
            "Pour in stock, simmer 8 minutes, then add coconut milk, palm sugar, and fish sauce; warm through (do not boil hard).",
            "Add prawns and tofu puffs; cook 2-3 minutes until prawns are just pink.",
            "Divide noodles and vermicelli between bowls; top with prawns, tofu, and bean sprouts.",
            "Ladle hot laksa broth over and serve with lime wedges and extra sambal on the side.",
        ],
        "translations": {
            "zh": {
                "title": "咖喱叻沙",
                "description": "椰浆咖喱面汤，盖上虾、油豆腐与豆芽，热辣浓郁。",
            },
            "ja": {
                "title": "カレーラクサ",
                "description": "ココナッツミルクの濃厚カレースープに麺とエビ、揚げ豆腐ともやしをたっぷり。マレーシアを代表する一杯。",
            },
            "ko": {
                "title": "커리 락사",
                "description": "코코넛 카레 국물에 면, 새우, 튀긴 두부와 숙주를 듬뿍 담은 말레이시아의 매콤한 국수.",
            },
            "vi": {
                "title": "Mì Laksa cà ri",
                "description": "Mì nước cốt dừa cà ri Mã Lai cay nồng, ăn cùng tôm, đậu hũ chiên phồng và giá đỗ.",
            },
        },
    },
    # ---- German ----
    {
        "title": "Wiener Schnitzel",
        "description": "Pounded veal cutlet, breaded in toasted crumbs and pan-fried in butter to a wave-crisp coat.",
        "cuisine": "german", "language": "en", "spice_level": 0,
        "prep": 15, "cook": 12, "servings": 4, "image": _img("wiener-schnitzel"),
        "tags": ["main course", "weeknight", "weekend"],
        "ingredients": [
            {"quantity": 4, "name": "veal cutlets, 120 g each, pounded to 4 mm thick"},
            {"quantity": 100, "unit": "g", "name": "all-purpose flour"},
            {"quantity": 2, "name": "eggs, beaten with 1 tbsp milk"},
            {"quantity": 150, "unit": "g", "name": "fine dried breadcrumbs (toasted lightly)"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 0.5, "unit": "tsp", "name": "white pepper"},
            {"quantity": 80, "unit": "g", "name": "clarified butter"},
            {"quantity": 60, "unit": "ml", "name": "neutral oil"},
            {"quantity": 1, "name": "lemon, cut in wedges"},
            {"name": "lingonberry jam and parsley, to serve"},
        ],
        "steps": [
            "Season cutlets on both sides with salt and white pepper.",
            "Set up three plates: flour, beaten egg, breadcrumbs. Dredge each cutlet in flour, dip in egg, then press lightly into breadcrumbs.",
            "Lay the breaded cutlets on a tray without stacking and rest 5 minutes.",
            "Heat butter and oil 1 cm deep in a wide pan until shimmering (170 C).",
            "Slide in one cutlet at a time and immediately swirl the pan so the hot fat washes over the top — this is what creates the puffy 'soufflé' bubbles.",
            "Fry 90 seconds per side until golden; drain on a wire rack and serve immediately with lemon, lingonberry, and parsley.",
        ],
        "translations": {
            "zh": {
                "title": "维也纳炸牛排",
                "description": "敲薄的小牛排裹上烤过的面包屑，黄油煎至金黄起泡，奥地利与德国南部的国民美食。",
            },
            "ja": {
                "title": "ヴィーナー・シュニッツェル",
                "description": "薄く叩いた仔牛肉にパン粉をまとわせ、バターで揚げ焼きしてふっくらと衣を立たせる、オーストリア・南ドイツの名物。",
            },
            "ko": {
                "title": "비너 슈니첼",
                "description": "얇게 두드린 송아지 고기에 빵가루를 입혀 버터에 노릇하게 부쳐 튀김 옷을 부풀린 오스트리아·남독일 명물.",
            },
            "vi": {
                "title": "Cốt-lết bê chiên Wiener Schnitzel",
                "description": "Cốt-lết bê đập mỏng, áo vụn bánh mì rang và áp chảo bơ cho lớp vỏ vàng phồng — món Đức/Áo cổ điển.",
            },
        },
    },
    {
        "title": "Sauerbraten",
        "description": "Beef pot roast marinated in vinegar and wine, slow-braised with a gingersnap-thickened gravy.",
        "cuisine": "german", "language": "en", "spice_level": 0,
        "prep": 30, "cook": 180, "servings": 6, "image": _img("sauerbraten"),
        "tags": ["main course", "celebration", "make-ahead"],
        "ingredients": [
            {"quantity": 1.5, "unit": "kg", "name": "beef chuck or rump roast"},
            {"quantity": 500, "unit": "ml", "name": "red wine vinegar"},
            {"quantity": 500, "unit": "ml", "name": "dry red wine"},
            {"quantity": 500, "unit": "ml", "name": "water"},
            {"quantity": 2, "name": "onions, sliced"},
            {"quantity": 2, "name": "carrots, sliced"},
            {"quantity": 2, "unit": "stalks", "name": "celery, sliced"},
            {"quantity": 2, "name": "bay leaves"},
            {"quantity": 10, "name": "whole cloves"},
            {"quantity": 10, "name": "juniper berries (optional)"},
            {"quantity": 1, "unit": "tbsp", "name": "salt"},
            {"quantity": 3, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 80, "unit": "g", "name": "gingersnap cookies (lebkuchen), crushed"},
            {"quantity": 2, "unit": "tbsp", "name": "raisins"},
        ],
        "steps": [
            "Combine vinegar, wine, water, vegetables, spices, and salt; bring to a boil, cool, then pour over the beef in a non-reactive container. Refrigerate 3 days, turning daily.",
            "Lift the beef out; pat dry. Strain the marinade and reserve the liquid and vegetables separately.",
            "Brown the beef in oil in a heavy pot on all sides, 8 minutes.",
            "Add the strained vegetables and 1 L of the marinade; cover and braise at 150 C for 2.5 hours, until fork-tender.",
            "Lift beef out; strain the cooking liquid into a saucepan. Whisk in crushed gingersnaps and raisins; simmer 5 minutes until silky.",
            "Slice the beef across the grain and ladle gravy over. Traditional sides: red cabbage and potato dumplings (kartoffelklöße).",
        ],
        "translations": {
            "zh": {
                "title": "德式醋焖牛肉",
                "description": "牛肉先以醋与红酒腌制三日，再慢炖至软嫩，用姜饼屑收汁，是德国节庆主菜。",
            },
            "ja": {
                "title": "ザワーブラーテン",
                "description": "牛肉を酢と赤ワインで3日マリネしてから煮込み、ジンジャークッキーで濃度をつけた、ドイツの祝祭料理。",
            },
            "ko": {
                "title": "자우어브라텐",
                "description": "쇠고기를 식초와 와인에 3일 절였다가 푹 끓이고, 진저쿠키로 농도를 맞춘 독일의 잔치 요리.",
            },
            "vi": {
                "title": "Bò hầm Sauerbraten",
                "description": "Thịt bò ướp giấm và vang đỏ ba ngày rồi hầm chậm, sánh nước sốt bằng bánh quy gừng — món lễ hội của người Đức.",
            },
        },
    },
    {
        "title": "Kartoffelsalat",
        "description": "Warm German potato salad with smoky bacon, broth, and a sharp mustard-vinegar dressing.",
        "cuisine": "german", "language": "en", "spice_level": 0,
        "prep": 15, "cook": 25, "servings": 6, "image": _img("kartoffelsalat"),
        "tags": ["salad", "side dish", "make-ahead"],
        "ingredients": [
            {"quantity": 1, "unit": "kg", "name": "waxy potatoes, scrubbed (skins on)"},
            {"quantity": 200, "unit": "g", "name": "smoked bacon lardons"},
            {"quantity": 1, "name": "small onion, finely chopped"},
            {"quantity": 250, "unit": "ml", "name": "hot chicken or vegetable stock"},
            {"quantity": 5, "unit": "tbsp", "name": "white wine vinegar"},
            {"quantity": 2, "unit": "tbsp", "name": "whole-grain mustard"},
            {"quantity": 3, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 1, "unit": "tsp", "name": "sugar"},
            {"quantity": 1, "unit": "small bunch", "name": "fresh chives, snipped"},
            {"name": "salt, pepper"},
        ],
        "steps": [
            "Boil potatoes whole in salted water 20 minutes until tender but not falling apart; drain and let steam-dry 5 minutes.",
            "Peel while still warm (use a paring knife and a tea towel), then slice into 5-mm coins straight into a wide bowl.",
            "Render bacon in a dry pan until crisp; lift out, reserving fat. Sweat onion in the bacon fat until translucent.",
            "Whisk hot stock, vinegar, mustard, oil, sugar, salt, and pepper; pour over the warm potatoes and toss gently.",
            "Fold in bacon and onion; let rest 15 minutes so the potatoes drink the dressing.",
            "Scatter chives and serve warm or at room temperature alongside sausages.",
        ],
        "translations": {
            "zh": {
                "title": "德式温热土豆沙拉",
                "description": "温热的德式土豆沙拉，加入烟熏培根、高汤与酸辣芥末醋汁。",
            },
            "ja": {
                "title": "カルトッフェルザラート（ドイツ風ポテトサラダ）",
                "description": "燻製ベーコンとブロス、ピリッとしたマスタード酢で和える、温かいうちにいただくドイツ南部のポテトサラダ。",
            },
            "ko": {
                "title": "카르토펠잘라트",
                "description": "훈제 베이컨과 육수, 톡 쏘는 머스터드 식초로 따뜻하게 버무리는 독일식 감자 샐러드.",
            },
            "vi": {
                "title": "Salad khoai tây Đức",
                "description": "Salad khoai tây ấm kiểu Đức với thịt xông khói, nước dùng nóng và sốt giấm mù tạt nồng.",
            },
        },
    },
    # ---- Indonesian ----
    {
        "title": "Nasi Goreng",
        "description": "Spicy Indonesian fried rice with sweet kecap manis, chili, shrimp, and a fried egg crown.",
        "cuisine": "indonesian", "language": "en", "spice_level": 2,
        "prep": 15, "cook": 12, "servings": 2, "image": _img("nasi-goreng"),
        "tags": ["main course", "weeknight", "fast"],
        "ingredients": [
            {"quantity": 3, "unit": "cups", "name": "cold leftover jasmine rice"},
            {"quantity": 2, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 3, "name": "shallots, thinly sliced"},
            {"quantity": 2, "name": "bird's eye chilies, finely chopped"},
            {"quantity": 1, "unit": "tbsp", "name": "shrimp paste (terasi), toasted"},
            {"quantity": 150, "unit": "g", "name": "small peeled shrimp"},
            {"quantity": 100, "unit": "g", "name": "chicken thigh, diced"},
            {"quantity": 3, "unit": "tbsp", "name": "kecap manis (sweet soy)"},
            {"quantity": 1, "unit": "tbsp", "name": "light soy sauce"},
            {"quantity": 1, "unit": "tsp", "name": "sambal oelek"},
            {"quantity": 2, "name": "eggs (for frying), plus 2 more for the topping"},
            {"quantity": 1, "name": "cucumber, sliced; sliced tomato"},
            {"name": "fried shallots, lime wedges, prawn crackers, to serve"},
        ],
        "steps": [
            "Pound or blend garlic, shallots, chilies, and shrimp paste into a coarse spice paste.",
            "Heat oil in a wok over high; fry the spice paste 90 seconds until fragrant.",
            "Add chicken; stir-fry 2 minutes. Push aside, scramble 2 eggs in the empty space, then incorporate.",
            "Add shrimp and rice, breaking up any clumps with the back of a spatula.",
            "Pour in kecap manis, light soy, and sambal; toss for 3 minutes over high heat until each grain is glazed and the edges caramelize.",
            "Fry the remaining eggs sunny-side up. Plate the rice, top with eggs, and serve with cucumber, tomato, fried shallots, lime, and prawn crackers.",
        ],
        "translations": {
            "zh": {
                "title": "印度尼西亚炒饭",
                "description": "印度尼西亚风味的炒饭,配有甜酱和鸡蛋",
            },
            "ja": {
                "title": "アスタカムース",
                "description": "アスタカムースはディコーターにきる",
            },
            "ko": {
                "title": "총주백엘세요",
                "description": "총주백엘세요 주엘세요 었세요 사장엘세요",
            },
            "vi": {
                "title": "Cm Chien G",
                "description": "Cm chien cay phong cch Indonesia v i kecap manis, ớt, tm, v trng rán",
            },
        },
    },
    {
        "title": "Beef Rendang",
        "description": "Padang-style beef simmered in coconut milk and spice paste until the sauce darkens and clings.",
        "cuisine": "indonesian", "language": "en", "spice_level": 3,
        "prep": 25, "cook": 180, "servings": 6, "image": _img("beef-rendang"),
        "tags": ["main course", "celebration", "make-ahead"],
        "ingredients": [
            {"quantity": 1.2, "unit": "kg", "name": "beef chuck, cut into 4-cm cubes"},
            {"quantity": 8, "name": "dried red chilies, soaked"},
            {"quantity": 6, "name": "shallots, peeled"},
            {"quantity": 5, "unit": "cloves", "name": "garlic"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger"},
            {"quantity": 1, "unit": "thumb", "name": "fresh galangal"},
            {"quantity": 3, "unit": "stalks", "name": "lemongrass, white part, smashed"},
            {"quantity": 4, "name": "kaffir lime leaves, torn"},
            {"quantity": 1, "name": "turmeric leaf (optional but classic), tied in a knot"},
            {"quantity": 1, "unit": "tsp", "name": "ground turmeric"},
            {"quantity": 1, "unit": "tsp", "name": "ground coriander"},
            {"quantity": 800, "unit": "ml", "name": "coconut milk"},
            {"quantity": 100, "unit": "ml", "name": "coconut cream"},
            {"quantity": 60, "unit": "g", "name": "toasted desiccated coconut, ground (kerisik)"},
            {"quantity": 1, "unit": "tbsp", "name": "palm sugar"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
        ],
        "steps": [
            "Blend chilies, shallots, garlic, ginger, galangal, ground turmeric, and coriander into a smooth spice paste.",
            "In a wide heavy pot, combine beef, spice paste, lemongrass, lime leaves, turmeric leaf, coconut milk, coconut cream, palm sugar, and salt.",
            "Bring to a gentle simmer and cook uncovered 90 minutes, stirring every 15 minutes — the liquid will be soupy and pale.",
            "Continue simmering 60-90 minutes more, stirring more often as it thickens, until the coconut milk reduces and 'splits' — you'll see oil pooling.",
            "Stir in the kerisik (toasted ground coconut) and cook a final 20 minutes, stirring constantly, until the sauce is dark, dry, and clinging to the meat.",
            "Rest off heat 15 minutes — rendang is famously better the next day. Serve with steamed rice and a vegetable side.",
        ],
        "translations": {
            "zh": {
                "title": "牛肉仁当",
                "description": "用椰奶和香料酱慢煮巴当风格的牛肉，直到酱汁变暗并且粘在肉上",
            },
            "ja": {
                "title": "レンダン",
                "description": "パダン風の牛肉をココナッツミルクとスパイスペーストで煮込んで、ソースが濃厚になる",
            },
            "ko": {
                "title": "렌당",
                "description": "파당식의 쇠고기를 코코넛 밀크와 스파이스 페스트에 조리하여 소스가 진하고 달라붙을 때까지",
            },
            "vi": {
                "title": "Thịt bò Rendang",
                "description": "Thịt bò Padang được nấu trong sữa dừa và hỗn hợp gia vị cho đến khi nước sốt đặc và bám vào thịt",
            },
        },
    },
    {
        "title": "Gado-Gado",
        "description": "Mixed vegetable, tofu, and egg salad drowned in chunky peanut sauce.",
        "cuisine": "indonesian", "language": "en", "spice_level": 1,
        "prep": 25, "cook": 20, "servings": 4, "image": _img("gado-gado"),
        "tags": ["salad", "main course", "lunch"],
        "ingredients": [
            {"quantity": 200, "unit": "g", "name": "long beans (or green beans), cut in 5-cm lengths"},
            {"quantity": 200, "unit": "g", "name": "bean sprouts"},
            {"quantity": 200, "unit": "g", "name": "spinach or kangkong"},
            {"quantity": 2, "name": "potatoes, boiled and sliced"},
            {"quantity": 4, "name": "hard-boiled eggs, halved"},
            {"quantity": 250, "unit": "g", "name": "firm tofu, cubed and shallow-fried"},
            {"quantity": 1, "name": "cucumber, sliced"},
            {"quantity": 200, "unit": "g", "name": "natural peanut butter (or 250 g roasted peanuts, ground)"},
            {"quantity": 2, "unit": "cloves", "name": "garlic, grated"},
            {"quantity": 2, "name": "bird's eye chilies, chopped (more to taste)"},
            {"quantity": 2, "unit": "tbsp", "name": "kecap manis"},
            {"quantity": 1, "unit": "tbsp", "name": "tamarind concentrate"},
            {"quantity": 1, "unit": "tbsp", "name": "palm sugar"},
            {"quantity": 150, "unit": "ml", "name": "warm water (to thin the sauce)"},
            {"name": "shrimp crackers (krupuk), fried shallots, to serve"},
        ],
        "steps": [
            "Blanch long beans 2 minutes, bean sprouts 30 seconds, and spinach 30 seconds in separate batches; shock in iced water and drain.",
            "Whisk peanut butter, garlic, chilies, kecap manis, tamarind, and palm sugar; thin with warm water to a slow-pouring consistency.",
            "Taste the sauce — it should be salty-sweet-spicy-tangy in equal measure. Adjust with more kecap or tamarind.",
            "Arrange potatoes, blanched vegetables, cucumber, tofu, and eggs in groups on a platter.",
            "Pour the peanut sauce generously over the top (do not toss — the visual is part of the dish).",
            "Crown with shrimp crackers and fried shallots, and serve at room temperature.",
        ],
        "translations": {
            "zh": {
                "title": "印尼花生酱蔬菜沙拉",
                "description": "印尼经典凉拌：豆角、豆芽、菠菜、土豆、豆腐与水煮蛋，淋上香辣花生酱。",
            },
            "ja": {
                "title": "ガドガド",
                "description": "茹で野菜、揚げ豆腐、ゆで卵、じゃがいもにピーナッツソースをたっぷりかける、インドネシアの定番サラダ。",
            },
            "ko": {
                "title": "가도가도",
                "description": "데친 채소와 튀긴 두부, 삶은 달걀, 감자에 진한 땅콩 소스를 듬뿍 끼얹은 인도네시아 대표 샐러드.",
            },
            "vi": {
                "title": "Salad Gado-Gado",
                "description": "Salad rau luộc, đậu hũ chiên, trứng luộc và khoai tây rưới sốt đậu phộng cay đậm kiểu Indonesia.",
            },
        },
    },
    # ---- Brazilian ----
    {
        "title": "Feijoada",
        "description": "Black bean and smoked-pork stew served with rice, orange slices, and farofa.",
        "cuisine": "brazilian", "language": "en", "spice_level": 1,
        "prep": 30, "cook": 180, "servings": 8, "image": _img("feijoada"),
        "tags": ["main course", "celebration", "make-ahead"],
        "ingredients": [
            {"quantity": 500, "unit": "g", "name": "dried black beans, soaked overnight"},
            {"quantity": 300, "unit": "g", "name": "smoked pork ribs"},
            {"quantity": 300, "unit": "g", "name": "linguiça (or smoked Polish sausage), sliced"},
            {"quantity": 200, "unit": "g", "name": "smoked bacon slab, cubed"},
            {"quantity": 300, "unit": "g", "name": "pork shoulder, cubed"},
            {"quantity": 1, "name": "large onion, chopped"},
            {"quantity": 6, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 2, "name": "bay leaves"},
            {"quantity": 1, "unit": "tsp", "name": "ground cumin"},
            {"quantity": 2, "unit": "tbsp", "name": "olive oil"},
            {"quantity": 1, "name": "small bunch collards, finely shredded (couve)"},
            {"quantity": 2, "name": "oranges, peeled and sliced"},
            {"name": "cooked white rice and farofa, to serve"},
        ],
        "steps": [
            "Drain soaked beans; cover with fresh water in a heavy pot with the smoked pork ribs and bacon. Simmer 90 minutes until beans are soft and the broth is dark.",
            "In a wide pan, brown linguiça and pork shoulder in olive oil; lift out.",
            "In the same pan, sweat onion until soft, then add garlic, bay, and cumin 1 minute.",
            "Stir the sofrito and browned meats into the bean pot; simmer covered 45 minutes more, adding water if needed.",
            "Sauté shredded collards 2 minutes in a hot pan with garlic and olive oil — they stay bright green and slightly crunchy.",
            "Serve feijoada over rice with collards, orange slices, and a sprinkle of farofa to soak up the broth.",
        ],
        "translations": {
            "zh": {
                "title": "菲若达",
                "description": "黑豆炖烟熏猪肉和香肠",
            },
            "ja": {
                "title": "フィジョアーダ",
                "description": "黒豆と煙熏豚肉、ソーセージのシチュー",
            },
            "ko": {
                "title": "페이조아다",
                "description": "흰콩과 훈제돼지고기, 소시지의 스튜",
            },
            "vi": {
                "title": "Món đậu đen Brazil",
                "description": "Món hầm đậu đen với thịt lợn hun khói và xúc xích",
            },
        },
    },
    {
        "title": "Moqueca de Peixe",
        "description": "Bahian coconut fish stew with palm oil, peppers, and cilantro — bright and golden.",
        "cuisine": "brazilian", "language": "en", "spice_level": 1,
        "prep": 20, "cook": 25, "servings": 4, "image": _img("moqueca"),
        "tags": ["main course", "weeknight", "weekend"],
        "ingredients": [
            {"quantity": 700, "unit": "g", "name": "firm white fish (snapper, grouper), cut into 4-cm chunks"},
            {"quantity": 3, "unit": "tbsp", "name": "lime juice"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, grated"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 2, "unit": "tbsp", "name": "dendê (palm) oil"},
            {"quantity": 2, "unit": "tbsp", "name": "olive oil"},
            {"quantity": 1, "name": "large onion, sliced into rings"},
            {"quantity": 2, "name": "bell peppers (red and yellow), sliced into rings"},
            {"quantity": 3, "name": "tomatoes, sliced into rings"},
            {"quantity": 400, "unit": "ml", "name": "coconut milk"},
            {"quantity": 1, "unit": "small bunch", "name": "fresh cilantro, chopped"},
            {"quantity": 1, "name": "lime, cut in wedges"},
            {"name": "cooked white rice, to serve"},
        ],
        "steps": [
            "Marinate fish chunks in lime juice, garlic, and salt for 15 minutes.",
            "Warm dendê and olive oils together in a wide clay or heavy pot.",
            "Layer in concentric rings: onion, peppers, tomato, fish — do not stir.",
            "Pour coconut milk over and simmer covered 12-15 minutes, just until the fish flakes (do not overcook — Bahian style stays delicate).",
            "Scatter cilantro and rest off heat 3 minutes for the flavors to settle.",
            "Spoon over rice in shallow bowls and finish with lime wedges.",
        ],
        "translations": {
            "zh": {
                "title": "巴伊亚椰浆炖鱼",
                "description": "巴西巴伊亚州的椰浆炖鱼，加入棕榈油、彩椒与香菜，色泽金黄、味道明亮。",
            },
            "ja": {
                "title": "モケッカ・デ・ペイシェ",
                "description": "ココナッツミルクとパームオイル、パプリカ、パクチーで仕上げる、ブラジル・バイーア州の魚介煮込み。",
            },
            "ko": {
                "title": "모케카 데 페이쉬",
                "description": "코코넛 밀크와 야자유, 파프리카, 고수로 끓여낸 브라질 바이아 지방의 환한 황금빛 생선 스튜.",
            },
            "vi": {
                "title": "Cá hầm Moqueca",
                "description": "Cá hầm nước cốt dừa kiểu Bahia với dầu cọ dendê, ớt chuông và ngò tươi — vàng óng và thanh thoát.",
            },
        },
    },
    {
        "title": "Pão de Queijo",
        "description": "Cloud-light Brazilian cheese puffs with a crisp shell and a stretchy tapioca interior.",
        "cuisine": "brazilian", "language": "en", "spice_level": 0,
        "prep": 15, "cook": 25, "servings": 6, "image": _img("pao-de-queijo"),
        "tags": ["snack", "breakfast", "weekend"],
        "ingredients": [
            {"quantity": 250, "unit": "g", "name": "sour tapioca starch (polvilho azedo)"},
            {"quantity": 50, "unit": "g", "name": "sweet tapioca starch (polvilho doce, or more sour)"},
            {"quantity": 250, "unit": "ml", "name": "whole milk"},
            {"quantity": 100, "unit": "ml", "name": "neutral oil"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 2, "name": "large eggs"},
            {"quantity": 150, "unit": "g", "name": "queijo Minas or aged white cheddar, grated"},
            {"quantity": 50, "unit": "g", "name": "Parmesan, grated"},
        ],
        "steps": [
            "Bring milk, oil, and salt to a simmer in a saucepan.",
            "Pour the hot liquid over both tapioca starches in a mixing bowl; stir with a wooden spoon — it will look lumpy and dry.",
            "Let cool 10 minutes until just warm.",
            "Beat in eggs one at a time, then mix in both cheeses until you have a soft, sticky dough.",
            "With wet hands, roll into 4-cm balls and place on a parchment-lined tray 3 cm apart.",
            "Bake at 200 C for 22-25 minutes until puffed, golden, and hollow-sounding. Eat hot — the texture is best in the first hour.",
        ],
        "translations": {
            "zh": {
                "title": "巴西木薯奶酪面包",
                "description": "巴西经典小食：木薯粉与奶酪烤制而成，外壳酥脆，内里Q弹拉丝。",
            },
            "ja": {
                "title": "ポン・デ・ケージョ",
                "description": "タピオカ粉とチーズで作る、外はカリッと中はもちもちのブラジルの定番チーズパン。",
            },
            "ko": {
                "title": "팡 지 케이주",
                "description": "타피오카 가루와 치즈로 굽는 브라질의 대표 간식. 겉은 바삭하고 속은 쫀득쫀득.",
            },
            "vi": {
                "title": "Bánh phô mai Pão de Queijo",
                "description": "Bánh phô mai bột năng kiểu Brazil — vỏ giòn, ruột dai mềm và đầy vị bơ sữa.",
            },
        },
    },
    # ---- Peruvian ----
    {
        "title": "Lomo Saltado",
        "description": "Stir-fried beef sirloin with red onion, tomato, soy, and fries — the chifa classic.",
        "cuisine": "peruvian", "language": "en", "spice_level": 1,
        "prep": 20, "cook": 12, "servings": 4, "image": _img("lomo-saltado"),
        "tags": ["main course", "weeknight", "fast"],
        "ingredients": [
            {"quantity": 500, "unit": "g", "name": "beef sirloin, cut into thick strips"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 0.5, "unit": "tsp", "name": "black pepper"},
            {"quantity": 1, "unit": "tsp", "name": "ground cumin"},
            {"quantity": 3, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 1, "name": "red onion, sliced into thick wedges"},
            {"quantity": 2, "name": "Roma tomatoes, cut into wedges"},
            {"quantity": 1, "name": "ají amarillo (or yellow chili), sliced"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 3, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 2, "unit": "tbsp", "name": "red wine vinegar"},
            {"quantity": 1, "unit": "small bunch", "name": "fresh cilantro, chopped"},
            {"quantity": 500, "unit": "g", "name": "frozen French fries, hot from the fryer"},
            {"name": "steamed white rice, to serve"},
        ],
        "steps": [
            "Toss beef with salt, pepper, and cumin.",
            "Heat oil in a wok or wide pan over the highest heat; sear beef in two batches 90 seconds each, leaving the inside pink. Lift out.",
            "Add onion and ají to the same pan; toss 1 minute over high heat so they char but stay crisp.",
            "Add tomato and garlic; toss 30 seconds.",
            "Return beef and any juices; splash in soy sauce and vinegar and toss 30 seconds to glaze.",
            "Stir in the hot fries and cilantro, toss once, and serve immediately alongside white rice.",
        ],
        "translations": {
            "zh": {
                "title": "洛莫萨尔塔多",
                "description": "炒牛肉配薯条、酱油和黄辣椒",
            },
            "ja": {
                "title": "ロモサルタード",
                "description": "牛肉とフライを炒めたペルー風料理に醤油とアヒアマリロを添える",
            },
            "ko": {
                "title": "로모 살타도",
                "description": "소고기와 감자튀김, 간장, 그리고 아히 아마릴로를 넣은 페루식 볶음 요리",
            },
            "vi": {
                "title": "Thịt bò xào kiểu Peru",
                "description": "Thịt bò xào với khoai tây chiên, nước tương và ớt vàng",
            },
        },
    },
    {
        "title": "Ceviche",
        "description": "Lime-cured fish with red onion, ají, cilantro, and sweet potato — Peru's coastal classic.",
        "cuisine": "peruvian", "language": "en", "spice_level": 2,
        "prep": 25, "cook": 15, "servings": 4, "image": _img("ceviche"),
        "tags": ["appetizer", "main course", "lunch"],
        "ingredients": [
            {"quantity": 600, "unit": "g", "name": "very fresh white fish (sole, sea bass), skinless, cut into 2-cm cubes"},
            {"quantity": 200, "unit": "ml", "name": "fresh lime juice (from about 12 limes)"},
            {"quantity": 1, "name": "red onion, very thinly sliced"},
            {"quantity": 1, "name": "ají limo (or habanero), seeded and finely chopped"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger, grated"},
            {"quantity": 2, "unit": "cloves", "name": "garlic, grated"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 1, "unit": "small bunch", "name": "fresh cilantro, chopped"},
            {"quantity": 1, "name": "sweet potato, boiled and sliced into rounds"},
            {"quantity": 1, "name": "ear corn, boiled, kernels removed"},
            {"quantity": 50, "unit": "g", "name": "toasted Peruvian corn (cancha), to serve"},
        ],
        "steps": [
            "Soak sliced red onion in iced water 10 minutes to mellow the bite; drain and pat dry.",
            "Mash a few cilantro stems with the salt, garlic, ginger, and ají in a wide bowl with the side of a knife to make a 'leche de tigre' base.",
            "Pour lime juice over the base.",
            "Add fish cubes and toss gently. Cure 4 minutes — the cubes should turn opaque on the outside but stay tender inside.",
            "Fold in the red onion and most of the cilantro.",
            "Plate immediately with sweet potato and corn alongside, scatter cancha, and finish with the rest of the cilantro.",
        ],
        "translations": {
            "zh": {
                "title": "生鱼片",
                "description": "用柠檬腌制的鱼肉，配以红洋葱、阿吉阿马里洛辣椒、香菜和甜薯——秘鲁的经典海鲜菜肴",
            },
            "ja": {
                "title": "セビチェ",
                "description": "ライムでマリネした魚に、赤たまねぎ、アヒアマリロ、香菜、さつまいもを添えたペルーの郷土料理",
            },
            "ko": {
                "title": "세비체",
                "description": "라임 마리네 소스에 재운 생선에 빨간 양파, 아히 아마리요,香菜, 고구마를 곁들인 페루의 대표적인 해산물 요리",
            },
            "vi": {
                "title": "Cá ướp chanh Ceviche",
                "description": "Cá trắng tươi ướp nước cốt chanh chín tới, dùng kèm hành tím, ngò, ớt Peru, khoai lang và bắp — món biển kinh điển của Peru.",
            },
        },
    },
    {
        "title": "Ají de Gallina",
        "description": "Creamy shredded chicken in yellow chili-walnut sauce, ladled over rice and potato.",
        "cuisine": "peruvian", "language": "en", "spice_level": 1,
        "prep": 20, "cook": 45, "servings": 4, "image": _img("aji-de-gallina"),
        "tags": ["main course", "comfort", "make-ahead"],
        "ingredients": [
            {"quantity": 600, "unit": "g", "name": "boneless chicken breast"},
            {"quantity": 1, "unit": "L", "name": "chicken stock"},
            {"quantity": 4, "name": "slices stale white bread, crusts removed"},
            {"quantity": 250, "unit": "ml", "name": "evaporated milk"},
            {"quantity": 3, "unit": "tbsp", "name": "ají amarillo paste"},
            {"quantity": 60, "unit": "g", "name": "walnuts, toasted and chopped"},
            {"quantity": 50, "unit": "g", "name": "Parmesan, grated"},
            {"quantity": 1, "name": "large onion, finely chopped"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 3, "unit": "tbsp", "name": "olive oil"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 4, "name": "boiled yellow potatoes, sliced"},
            {"quantity": 4, "name": "hard-boiled eggs, halved"},
            {"quantity": 12, "name": "black olives"},
            {"name": "white rice, to serve"},
        ],
        "steps": [
            "Poach chicken in stock 18 minutes until just cooked through; cool in the broth, then shred. Reserve the broth.",
            "Soak bread slices in evaporated milk 5 minutes.",
            "Sweat onion in olive oil 6 minutes until soft; add garlic and ají amarillo paste, cook 3 minutes until darkened.",
            "Blend the bread-milk mixture with the onion base and 200 ml reserved stock until silky.",
            "Return the sauce to the pan with shredded chicken, walnuts, Parmesan, and salt; simmer 8 minutes, thinning with more stock to a velvety stew.",
            "Spoon over a bed of rice with potato slices, halved eggs, and olives arranged on top.",
        ],
        "translations": {
            "zh": {
                "title": "秘鲁黄椒鸡丝奶汁",
                "description": "黄椒、核桃与奶香炖煮的鸡丝，淋在米饭与土豆上，配煮蛋与橄榄。",
            },
            "ja": {
                "title": "アヒ・デ・ガジーナ",
                "description": "黄唐辛子とくるみ、エバミルクで仕立てた濃厚チキンソースを、ご飯とゆでじゃがいもにかけるペルーの家庭料理。",
            },
            "ko": {
                "title": "아히 데 가지나",
                "description": "노란 페루 고추와 호두, 연유로 끓여낸 진한 닭고기 스튜를 밥과 감자에 부어내는 페루 가정식.",
            },
            "vi": {
                "title": "Gà sốt ớt vàng Ají de Gallina",
                "description": "Gà xé sốt kem ớt vàng Peru và óc chó, dùng kèm cơm trắng, khoai luộc, trứng và ô-liu đen.",
            },
        },
    },
    # ---- Caribbean ----
    {
        "title": "Jamaican Jerk Chicken",
        "description": "Scotch bonnet-allspice marinated chicken char-grilled over pimento wood.",
        "cuisine": "caribbean", "language": "en", "spice_level": 3,
        "prep": 30, "cook": 40, "servings": 6, "image": _img("jerk-chicken"),
        "tags": ["main course", "grill", "weekend"],
        "ingredients": [
            {"quantity": 8, "name": "bone-in chicken thighs and drumsticks"},
            {"quantity": 4, "name": "Scotch bonnet peppers, stemmed (use less for milder)"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger"},
            {"quantity": 6, "unit": "cloves", "name": "garlic"},
            {"quantity": 1, "name": "small onion, quartered"},
            {"quantity": 4, "name": "spring onions, white and green"},
            {"quantity": 2, "unit": "tbsp", "name": "ground allspice (pimento)"},
            {"quantity": 1, "unit": "tbsp", "name": "fresh thyme leaves"},
            {"quantity": 1, "unit": "tsp", "name": "ground cinnamon"},
            {"quantity": 1, "unit": "tsp", "name": "ground nutmeg"},
            {"quantity": 2, "unit": "tbsp", "name": "brown sugar"},
            {"quantity": 3, "unit": "tbsp", "name": "soy sauce"},
            {"quantity": 3, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 60, "unit": "ml", "name": "lime juice"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
        ],
        "steps": [
            "Blend Scotch bonnets, ginger, garlic, onion, spring onion, allspice, thyme, cinnamon, nutmeg, brown sugar, soy, oil, lime juice, and salt into a thick paste.",
            "Slash chicken pieces 1 cm deep on the skin side; rub the marinade in deeply with gloves on (the chilies will burn skin).",
            "Marinate at least 4 hours; overnight is much better.",
            "Set a charcoal grill for indirect heat; if you have allspice (pimento) wood or hardwood chips, add them to the coals for smoke.",
            "Grill chicken skin-side up over indirect heat for 30 minutes, then move directly over the coals 8 minutes to crisp the skin, turning once.",
            "Rest 5 minutes, chop through the bone with a cleaver into 2-bite pieces, and serve with rice and peas plus festival bread.",
        ],
        "translations": {
            "zh": {
                "title": "牙买加烟熏辣鸡",
                "description": "苏格兰帽辣椒与多香果腌制的鸡肉，用烟熏木炭烤至焦香，是牙买加的国民烤肉。",
            },
            "ja": {
                "title": "ジャマイカン・ジャークチキン",
                "description": "スコッチボネットとオールスパイスでマリネした鶏肉を、ピメント材の炭でじっくり燻し焼きにするジャマイカの定番。",
            },
            "ko": {
                "title": "자메이칸 저크 치킨",
                "description": "스코치 보넷 고추와 올스파이스로 양념한 닭을 피멘토 나무 숯에 훈제 향을 입혀 굽는 자메이카의 국민 음식.",
            },
            "vi": {
                "title": "Gà nướng Jerk Jamaica",
                "description": "Gà ướp ớt Scotch bonnet và allspice nướng than thơm khói pimento — món nướng quốc dân của Jamaica.",
            },
        },
    },
    {
        "title": "Rice and Peas",
        "description": "Jamaican coconut rice cooked with kidney beans, thyme, and Scotch bonnet.",
        "cuisine": "caribbean", "language": "en", "spice_level": 1,
        "prep": 10, "cook": 35, "servings": 6, "image": _img("rice-and-peas"),
        "tags": ["side dish", "weeknight", "make-ahead"],
        "ingredients": [
            {"quantity": 1, "unit": "can", "name": "kidney beans (400 g), drained"},
            {"quantity": 400, "unit": "ml", "name": "coconut milk"},
            {"quantity": 300, "unit": "ml", "name": "water"},
            {"quantity": 400, "unit": "g", "name": "long-grain rice, rinsed"},
            {"quantity": 4, "name": "spring onions, white and green, smashed"},
            {"quantity": 3, "unit": "sprigs", "name": "fresh thyme"},
            {"quantity": 3, "unit": "cloves", "name": "garlic, smashed"},
            {"quantity": 1, "name": "whole Scotch bonnet pepper (do not pierce!)"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 1, "unit": "tbsp", "name": "neutral oil"},
        ],
        "steps": [
            "Combine kidney beans, coconut milk, water, spring onions, thyme, garlic, salt, and oil in a heavy pot. Bring to a simmer.",
            "Add the whole Scotch bonnet floating on top — this gives the dish its perfume, NOT its heat. Pierce it and you'll have a fire.",
            "Cook 5 minutes so the broth picks up the spices.",
            "Stir in rinsed rice and bring back to a simmer.",
            "Reduce heat to the lowest setting, cover tightly, and cook 18 minutes undisturbed.",
            "Off heat, rest covered 10 minutes. Remove the Scotch bonnet (gently!) and thyme stems, fluff with a fork, and serve.",
        ],
        "translations": {
            "zh": {
                "title": "牙买加椰浆豆饭",
                "description": "椰浆与红芸豆同煮的米饭，飘着百里香与苏格兰帽辣椒的清香 — 与烟熏辣鸡的灵魂搭档。",
            },
            "ja": {
                "title": "ライス・アンド・ピーズ",
                "description": "ココナッツミルクで赤いんげん豆と炊き上げ、タイムとスコッチボネットの香りをまとわせるジャマイカの伝統サイド。",
            },
            "ko": {
                "title": "라이스 앤 피스",
                "description": "코코넛 밀크에 강낭콩과 함께 지은 자메이카 전통 밥. 타임과 스코치 보넷의 향이 은은하게 배어든다.",
            },
            "vi": {
                "title": "Cơm dừa đậu Jamaica",
                "description": "Cơm nấu nước cốt dừa với đậu đỏ, dậy hương cỏ xạ và ớt Scotch bonnet — món ăn kèm quốc dân của Jamaica.",
            },
        },
    },
    {
        "title": "Ackee and Saltfish",
        "description": "Jamaica's national dish — silky ackee with flaked salt cod, tomato, and Scotch bonnet.",
        "cuisine": "caribbean", "language": "en", "spice_level": 1,
        "prep": 30, "cook": 20, "servings": 4, "image": _img("ackee-saltfish"),
        "tags": ["breakfast", "main course", "weekend"],
        "ingredients": [
            {"quantity": 300, "unit": "g", "name": "boneless salt cod, soaked overnight (change water twice)"},
            {"quantity": 1, "unit": "can", "name": "ackee in brine (540 g), drained gently"},
            {"quantity": 3, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 1, "name": "large onion, finely chopped"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 1, "name": "red bell pepper, diced"},
            {"quantity": 2, "name": "tomatoes, chopped"},
            {"quantity": 4, "name": "spring onions, sliced"},
            {"quantity": 0.5, "name": "Scotch bonnet, finely chopped (more to taste)"},
            {"quantity": 1, "unit": "tsp", "name": "fresh thyme leaves"},
            {"quantity": 0.5, "unit": "tsp", "name": "black pepper"},
            {"name": "boiled green bananas and fried dumplings (festival), to serve"},
        ],
        "steps": [
            "Boil soaked salt cod in fresh water 10 minutes; drain and flake into 2-cm pieces, removing any bones.",
            "Sauté onion in oil over medium 5 minutes until soft.",
            "Add garlic, bell pepper, spring onions, Scotch bonnet, and thyme; cook 3 minutes.",
            "Stir in tomatoes and salt cod; warm through 3 minutes.",
            "Gently fold in the ackee (do not stir vigorously — it falls apart) and warm for 2 minutes only.",
            "Crack on black pepper and serve with boiled green bananas and fried dumplings for the full Jamaican breakfast.",
        ],
        "translations": {
            "zh": {
                "title": "牙买加阿基果与咸鳕鱼",
                "description": "牙买加国菜：温润的阿基果与脱盐鳕鱼丝，配番茄、彩椒与苏格兰帽辣椒。",
            },
            "ja": {
                "title": "アキー・アンド・ソルトフィッシュ",
                "description": "塩抜きしたタラと滑らかなアキーの実を、トマトやスコッチボネットと炒め合わせるジャマイカの国民料理。",
            },
            "ko": {
                "title": "아키와 솔트피쉬",
                "description": "소금기를 뺀 대구살과 부드러운 아키 열매를 토마토, 스코치 보넷과 함께 볶아내는 자메이카의 국민 음식.",
            },
            "vi": {
                "title": "Ackee và cá muối Jamaica",
                "description": "Quốc thực Jamaica: quả ackee mềm mượt xào cùng cá tuyết muối, cà chua và ớt Scotch bonnet.",
            },
        },
    },
    # ---- Taiwanese ----
    {
        "title": "Taiwanese Beef Noodle Soup",
        "description": "Slow-braised beef shank in a spiced soy broth with hand-pulled noodles and pickled mustard greens.",
        "cuisine": "taiwanese", "language": "en", "spice_level": 2,
        "prep": 25, "cook": 180, "servings": 4, "image": _img("beef-noodle-soup"),
        "tags": ["soup", "main course", "weekend"],
        "ingredients": [
            {"quantity": 1, "unit": "kg", "name": "beef shank, cut into 5-cm pieces"},
            {"quantity": 200, "unit": "g", "name": "beef tendon (optional, classic)"},
            {"quantity": 3, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 2, "unit": "tbsp", "name": "doubanjiang (Sichuan broad bean chili paste)"},
            {"quantity": 1, "unit": "tbsp", "name": "tomato paste"},
            {"quantity": 4, "name": "ripe tomatoes, quartered"},
            {"quantity": 1, "name": "large onion, sliced"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger, sliced"},
            {"quantity": 6, "unit": "cloves", "name": "garlic, smashed"},
            {"quantity": 2, "name": "star anise"},
            {"quantity": 1, "unit": "stick", "name": "cinnamon"},
            {"quantity": 1, "unit": "tsp", "name": "Sichuan peppercorns"},
            {"quantity": 80, "unit": "ml", "name": "Shaoxing wine"},
            {"quantity": 80, "unit": "ml", "name": "dark soy sauce"},
            {"quantity": 2, "unit": "tbsp", "name": "rock sugar"},
            {"quantity": 2, "unit": "L", "name": "water or chicken stock"},
            {"quantity": 400, "unit": "g", "name": "fresh hand-pulled noodles"},
            {"quantity": 1, "unit": "small bunch", "name": "bok choy, halved"},
            {"quantity": 100, "unit": "g", "name": "Taiwanese pickled mustard greens (suan cai), chopped"},
            {"quantity": 4, "name": "spring onions, sliced"},
        ],
        "steps": [
            "Blanch beef and tendon 3 minutes in boiling water, drain, and rinse to clean the broth.",
            "Heat oil in a heavy pot; fry doubanjiang and tomato paste 90 seconds until red oil separates.",
            "Add onion, ginger, garlic, star anise, cinnamon, and Sichuan peppercorns; stir 1 minute.",
            "Add beef, tendon, tomatoes, Shaoxing, dark soy, rock sugar, and water. Bring to a simmer and cook covered on the lowest heat 2.5 hours, until the beef and tendon are spoon-tender.",
            "Cook noodles in a separate pot per package; blanch bok choy 60 seconds.",
            "Divide noodles between bowls, top with beef, tendon, and bok choy; ladle hot broth over and finish with pickled mustard greens and spring onion.",
        ],
        "translations": {
            "zh": {
                "title": "台湾牛肉面",
                "description": "慢煮的牛腱在香料酱油汤中，配以手拉面和腌制的芥菜",
            },
            "ja": {
                "title": "台湾風牛肉ラーメン",
                "description": "スパイシーな醤油ベースのスープで煮込んだ牛肉のしんがいに、手打ち麺と漬け菜を添えた",
            },
            "ko": {
                "title": "타이완식 소고기 라면",
                "description": "스파이시한 간장국에 고기와 국물이 어우러진 타이완식 소고기 라면, 손수 뽑은 면과 담근 무청으로 풍미를 더했다",
            },
            "vi": {
                "title": "Phở bò Đài Loan",
                "description": "Thịt bò hầm chậm trong nước dùng gia vị từ xì dầu, ăn kèm với mì tươi và rau cải muối",
            },
        },
    },
    {
        "title": "Three-Cup Chicken",
        "description": "Chicken simmered in equal cups of soy sauce, rice wine, and sesame oil — finished with Thai basil.",
        "cuisine": "taiwanese", "language": "en", "spice_level": 1,
        "prep": 15, "cook": 25, "servings": 4, "image": _img("three-cup-chicken"),
        "tags": ["main course", "weeknight", "fast"],
        "ingredients": [
            {"quantity": 700, "unit": "g", "name": "bone-in chicken thighs, chopped into 4-cm pieces"},
            {"quantity": 80, "unit": "ml", "name": "toasted sesame oil"},
            {"quantity": 80, "unit": "ml", "name": "Shaoxing rice wine"},
            {"quantity": 60, "unit": "ml", "name": "light soy sauce + 1 tbsp dark soy"},
            {"quantity": 1, "unit": "thumb", "name": "fresh ginger, sliced into thick coins"},
            {"quantity": 1, "unit": "head", "name": "garlic, peeled (whole cloves)"},
            {"quantity": 4, "name": "dried red chilies"},
            {"quantity": 1, "unit": "tbsp", "name": "rock sugar (or palm sugar)"},
            {"quantity": 1, "unit": "large bunch", "name": "Thai basil leaves"},
        ],
        "steps": [
            "Heat sesame oil in a wide pan over medium until just shimmering — do not smoke; sesame oil burns fast.",
            "Fry ginger 90 seconds until edges curl and the oil smells nutty.",
            "Add whole garlic cloves and dried chilies; toss 30 seconds.",
            "Push aside and brown chicken pieces skin-side down 4 minutes.",
            "Pour in rice wine, both soy sauces, and rock sugar. Cover and simmer 12 minutes, then uncover and reduce 5 minutes until the sauce glazes the chicken.",
            "Off heat, toss in a generous handful of Thai basil — it should wilt from residual heat. Serve directly from the clay pot with rice.",
        ],
        "translations": {
            "zh": {
                "title": "三杯鸡",
                "description": "三杯（酱油、米酒、麻油）煨煮的鸡肉，最后拌入九层塔，是台湾经典家常菜。",
            },
            "ja": {
                "title": "三杯鶏（サンベイジー）",
                "description": "醤油・米酒・ごま油を同量で煮詰め、最後にタイバジルを加える台湾の名物鶏煮込み。",
            },
            "ko": {
                "title": "삼배계 (산베이지)",
                "description": "간장·미주·참기름을 1대1대1로 졸여 닭을 익히고, 마지막에 타이 바질을 듬뿍 넣는 대만의 대표 가정식.",
            },
            "vi": {
                "title": "Gà ba chén Tam Bôi Kê",
                "description": "Gà rim với nước tương, rượu gạo và dầu mè theo tỉ lệ ngang nhau, kết bằng húng quế Thái — đặc sản Đài Loan.",
            },
        },
    },
    {
        "title": "Lu Rou Fan",
        "description": "Braised pork belly in five-spice soy, ladled over a bowl of rice with a pickled-mustard slice.",
        "cuisine": "taiwanese", "language": "en", "spice_level": 0,
        "prep": 15, "cook": 90, "servings": 4, "image": _img("lu-rou-fan"),
        "tags": ["main course", "comfort", "make-ahead"],
        "ingredients": [
            {"quantity": 600, "unit": "g", "name": "pork belly, cut into 5-mm dice (skin on, classic)"},
            {"quantity": 2, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 4, "name": "shallots, finely chopped"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 4, "unit": "tbsp", "name": "light soy sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "dark soy sauce"},
            {"quantity": 60, "unit": "ml", "name": "Shaoxing rice wine"},
            {"quantity": 2, "unit": "tbsp", "name": "rock sugar"},
            {"quantity": 1, "unit": "tsp", "name": "Chinese five-spice powder"},
            {"quantity": 1, "unit": "stick", "name": "cinnamon"},
            {"quantity": 2, "name": "star anise"},
            {"quantity": 500, "unit": "ml", "name": "water or chicken stock"},
            {"quantity": 4, "name": "hard-boiled eggs, peeled"},
            {"name": "steamed white rice and pickled mustard greens, to serve"},
        ],
        "steps": [
            "Brown pork belly in oil over medium-high 8 minutes until fat is rendered and edges crisp.",
            "Pour off most of the fat, leaving 2 tbsp; add shallots and garlic and cook 4 minutes until fragrant.",
            "Stir in rock sugar and let it melt and lightly caramelize 60 seconds.",
            "Add both soy sauces, Shaoxing, five-spice, cinnamon, star anise, water, and eggs.",
            "Bring to a simmer, cover, and cook on the lowest heat 75 minutes, until the pork is glossy, tender, and the sauce has thickened.",
            "Spoon a generous ladle over hot rice with a halved egg and pickled mustard alongside.",
        ],
        "translations": {
            "zh": {
                "title": "卤肉饭",
                "description": "五花肉丁以酱油、五香与冰糖慢卤至晶莹油亮，浇在热米饭上配卤蛋与酸菜。",
            },
            "ja": {
                "title": "魯肉飯（ルーローファン）",
                "description": "五香粉と醤油、氷砂糖でじっくり煮込んだ豚バラ肉のあんを、熱々ご飯にかける台湾の国民丼。",
            },
            "ko": {
                "title": "루로우판 (대만식 돼지고기 덮밥)",
                "description": "오향가루와 간장, 얼음 설탕으로 푹 졸인 삼겹살을 따끈한 밥에 올리고 절임 채소와 함께 내는 대만 대표 덮밥.",
            },
            "vi": {
                "title": "Cơm thịt kho Lỗ Nhục Phạn",
                "description": "Ba chỉ heo rim ngũ vị, nước tương và đường phèn rưới lên cơm nóng với trứng kho và cải chua — món bình dân kinh điển Đài Loan.",
            },
        },
    },
    # ---- Portuguese ----
    {
        "title": "Bacalhau à Brás",
        "description": "Salt cod with shredded fried potatoes, eggs, onion, and black olives — Lisbon comfort food.",
        "cuisine": "portuguese", "language": "en", "spice_level": 0,
        "prep": 25, "cook": 25, "servings": 4, "image": _img("bacalhau-a-bras"),
        "tags": ["main course", "weeknight", "weekend"],
        "ingredients": [
            {"quantity": 400, "unit": "g", "name": "boneless salt cod, soaked 24 hours (change water 3 times)"},
            {"quantity": 4, "name": "medium potatoes, julienned (or 300 g matchstick fried potatoes)"},
            {"quantity": 100, "unit": "ml", "name": "extra-virgin olive oil"},
            {"quantity": 2, "name": "large onions, thinly sliced"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, sliced"},
            {"quantity": 1, "name": "bay leaf"},
            {"quantity": 6, "name": "large eggs, beaten"},
            {"quantity": 1, "unit": "small bunch", "name": "flat-leaf parsley, chopped"},
            {"quantity": 16, "name": "black olives (Portuguese, oil-cured)"},
            {"name": "salt, white pepper"},
            {"name": "neutral oil for frying potatoes"},
        ],
        "steps": [
            "Poach soaked cod in barely-simmering water 5 minutes; drain, cool, and flake into 2-cm shreds (discard skin and any bones).",
            "Deep-fry julienned potatoes at 170 C until pale golden and crisp; drain on paper towels.",
            "Heat olive oil in a wide pan; cook onions, garlic, and bay leaf over medium-low 12 minutes until soft and sweet (no color).",
            "Add the flaked cod and toss to warm through, 2 minutes.",
            "Add the crisp potatoes and beaten eggs at the same time. Stir gently for 60 seconds — the eggs should bind everything into a soft, custardy mixture, NOT scramble dry.",
            "Plate immediately, sprinkle parsley and olives over, and serve with a green salad.",
        ],
        "translations": {
            "zh": {
                "title": "巴卡洛阿布拉斯",
                "description": "用鸡蛋和细条土豆拌碎的咸鳕鱼",
            },
            "ja": {
                "title": "バカラウ・ア・ブラス",
                "description": "塩鮭を細かく刻んで卵と細切りのジャガイモと合わせて",
            },
            "ko": {
                "title": "바칼라우 아 브라스",
                "description": "소금에 절인 대구를 으깨서 계란과 썬감자와 함께",
            },
            "vi": {
                "title": "Cá tuyết xào trứng khoai tây",
                "description": "Cá tuyết muối xé nhỏ với trứng và khoai tây cắt que",
            },
        },
    },
    {
        "title": "Caldo Verde",
        "description": "Velvety potato soup studded with shredded couve and smoky chouriço.",
        "cuisine": "portuguese", "language": "en", "spice_level": 0,
        "prep": 15, "cook": 35, "servings": 6, "image": _img("caldo-verde"),
        "tags": ["soup", "comfort", "weeknight"],
        "ingredients": [
            {"quantity": 700, "unit": "g", "name": "starchy potatoes, peeled and quartered"},
            {"quantity": 1, "name": "large onion, chopped"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, smashed"},
            {"quantity": 1.5, "unit": "L", "name": "water"},
            {"quantity": 60, "unit": "ml", "name": "extra-virgin olive oil, plus more to finish"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 200, "unit": "g", "name": "chouriço (Portuguese smoked sausage), thinly sliced"},
            {"quantity": 300, "unit": "g", "name": "couve galega or kale, central rib removed, sliced into hair-thin ribbons"},
            {"name": "freshly ground black pepper; crusty bread to serve"},
        ],
        "steps": [
            "Simmer potatoes, onion, garlic, salt, and 30 ml olive oil in water for 25 minutes, until potatoes fall apart at a touch.",
            "While the soup simmers, dry-fry the chouriço slices in a pan until lightly crisp; reserve.",
            "Slice the couve as thinly as possible — true caldo verde calls for ribbons no wider than 1 mm, almost shaved.",
            "Mash or blend the soup smooth, then return to the pot.",
            "Stir in the sliced couve and the remaining olive oil; simmer just 5 minutes — the greens should be al dente and grassy-bright.",
            "Ladle into bowls, top with chouriço slices, drizzle with more olive oil, and grind black pepper over. Serve with broa or crusty bread.",
        ],
        "translations": {
            "zh": {
                "title": "卡尔多维尔德",
                "description": "一道加入西班牙辣香肠的羽叶甘蓝和土豆汤",
            },
            "ja": {
                "title": "カルド・ヴェルデ",
                "description": "コリザとジャガイモを使用したポルトガル風スープ、ショリーソが入っています",
            },
            "ko": {
                "title": "칼도 베르데",
                "description": "콜라드와 감자, 그리고 쇼리소가 들어간 포르투갈식 수프",
            },
            "vi": {
                "title": "Canh Xanh",
                "description": "Canh cải kale và khoai tây với chouriço",
            },
        },
    },
    {
        "title": "Pastel de Nata",
        "description": "Lisbon custard tarts in shatter-crisp puff pastry, blistered black on top.",
        "cuisine": "portuguese", "language": "en", "spice_level": 0,
        "prep": 30, "cook": 15, "servings": 12, "image": _img("pastel-de-nata"),
        "tags": ["dessert", "snack", "make-ahead"],
        "ingredients": [
            {"quantity": 1, "unit": "sheet", "name": "all-butter puff pastry (about 320 g), thawed"},
            {"quantity": 250, "unit": "ml", "name": "whole milk"},
            {"quantity": 1, "unit": "strip", "name": "lemon zest"},
            {"quantity": 1, "unit": "stick", "name": "cinnamon"},
            {"quantity": 150, "unit": "g", "name": "caster sugar"},
            {"quantity": 80, "unit": "ml", "name": "water"},
            {"quantity": 25, "unit": "g", "name": "cornstarch"},
            {"quantity": 6, "name": "egg yolks"},
            {"name": "ground cinnamon and icing sugar, to serve"},
        ],
        "steps": [
            "Roll the puff pastry into a tight log, slice into 12 discs, and press each disc into a muffin tin to form a thin cup, walls slightly above the rim.",
            "Warm milk with lemon zest and cinnamon stick until just steaming; remove from heat and infuse 10 minutes. Discard zest and cinnamon.",
            "Boil sugar and water 3 minutes to make a thin syrup; let stand briefly.",
            "Whisk cornstarch into the warm milk until smooth, then pour the hot sugar syrup in a thin stream while whisking. Cook over medium 2 minutes until it thickens to a custard.",
            "Off heat, whisk in egg yolks one at a time. Cool slightly so it pours without breaking the pastry, then fill each cup three-quarters full.",
            "Bake at the HOTTEST setting your oven goes (260 C/500 F) on the top rack for 11-13 minutes until the tops are blistered black in patches. Cool 5 minutes; dust with cinnamon and icing sugar.",
        ],
        "translations": {
            "zh": {
                "title": "葡式蛋挞",
                "description": "脆得碎成层的酥皮包裹丝滑卡仕达，表面烤至焦黑斑驳，是里斯本的传奇甜点。",
            },
            "ja": {
                "title": "パステル・デ・ナタ",
                "description": "サクサクのパフ生地にとろりとしたカスタードを詰め、表面を焦げ目がつくほど焼き上げるリスボンの名物菓子。",
            },
            "ko": {
                "title": "파스텔 드 나타",
                "description": "겹겹이 부풀어 오른 페이스트리 안에 부드러운 커스터드를 채워, 윗면을 검게 그을릴 정도로 구워내는 리스본의 명물 디저트.",
            },
            "vi": {
                "title": "Bánh trứng Pastel de Nata",
                "description": "Vỏ phyllo giòn rụm bọc nhân kem trứng mịn, mặt nướng cháy vàng đậm — đặc sản huyền thoại của Lisbon.",
            },
        },
    },
    # ---- British ----
    {
        "title": "Fish and Chips",
        "description": "Beer-battered cod with thick-cut chips, mushy peas, and tartare sauce.",
        "cuisine": "british", "language": "en", "spice_level": 0,
        "prep": 20, "cook": 25, "servings": 4, "image": _img("fish-and-chips"),
        "tags": ["main course", "weekend", "comfort"],
        "ingredients": [
            {"quantity": 4, "name": "cod fillets, 180 g each, skinned"},
            {"quantity": 200, "unit": "g", "name": "self-raising flour"},
            {"quantity": 2, "unit": "tbsp", "name": "cornstarch"},
            {"quantity": 1, "unit": "tsp", "name": "salt"},
            {"quantity": 300, "unit": "ml", "name": "cold pale ale or lager, very fizzy"},
            {"quantity": 800, "unit": "g", "name": "starchy potatoes, peeled, cut into 1.5-cm chips"},
            {"quantity": 2, "unit": "L", "name": "neutral oil for deep-frying"},
            {"quantity": 300, "unit": "g", "name": "frozen peas, blanched"},
            {"quantity": 30, "unit": "g", "name": "butter (for peas)"},
            {"quantity": 1, "unit": "small bunch", "name": "fresh mint, chopped"},
            {"name": "malt vinegar, lemon, and tartare sauce, to serve"},
        ],
        "steps": [
            "Soak chips in cold water 15 minutes; drain and pat dry — this is what makes them crisp.",
            "First fry: lower chips into 140 C oil and cook 7 minutes until soft but barely colored. Drain on a rack and rest 10 minutes.",
            "Whisk flour, cornstarch, and salt; pour in cold beer to a thick batter that just coats the back of a spoon. Rest 5 minutes.",
            "Heat fresh oil to 180 C. Pat fish dry, dust lightly in extra flour, then dip in batter and slip immediately into the oil.",
            "Fry fish 5 minutes, turning once, until deep golden and crisp; lift onto the rack with the chips.",
            "Second fry: drop the rested chips back into 190 C oil for 3 minutes until shatter-crisp. Crush peas with butter and mint. Plate everything together with vinegar, lemon, and tartare alongside.",
        ],
        "translations": {
            "zh": {
                "title": "英式炸鱼薯条",
                "description": "啤酒面糊裹炸的鳕鱼配粗切薯条、薄荷豌豆泥与塔塔酱，英国国民晚餐。",
            },
            "ja": {
                "title": "フィッシュ・アンド・チップス",
                "description": "ビール衣でカラッと揚げたタラに、太切りポテト、ミントのマッシュピー、タルタルソースを添える英国の国民料理。",
            },
            "ko": {
                "title": "피쉬 앤 칩스",
                "description": "맥주 반죽으로 바삭하게 튀긴 대구와 두툼한 감자튀김, 으깬 완두콩과 타르타르 소스 — 영국식 국민 메뉴.",
            },
            "vi": {
                "title": "Cá chiên & khoai Anh",
                "description": "Cá tuyết tẩm bột bia chiên giòn ăn cùng khoai cắt dày, sốt tartare và đậu Hà Lan nghiền bạc hà — món Anh kinh điển.",
            },
        },
    },
    {
        "title": "Shepherd's Pie",
        "description": "Slow-cooked lamb mince under a piped mash of buttery mashed potato, baked until bronzed.",
        "cuisine": "british", "language": "en", "spice_level": 0,
        "prep": 25, "cook": 75, "servings": 6, "image": _img("shepherds-pie"),
        "tags": ["main course", "comfort", "make-ahead"],
        "ingredients": [
            {"quantity": 700, "unit": "g", "name": "ground lamb"},
            {"quantity": 2, "unit": "tbsp", "name": "olive oil"},
            {"quantity": 2, "name": "onions, finely chopped"},
            {"quantity": 2, "name": "carrots, finely diced"},
            {"quantity": 4, "unit": "cloves", "name": "garlic, minced"},
            {"quantity": 2, "unit": "tbsp", "name": "tomato paste"},
            {"quantity": 2, "unit": "tbsp", "name": "Worcestershire sauce"},
            {"quantity": 1, "unit": "tbsp", "name": "fresh thyme leaves (or 1 tsp dried)"},
            {"quantity": 250, "unit": "ml", "name": "beef stock"},
            {"quantity": 200, "unit": "g", "name": "frozen peas"},
            {"quantity": 1, "unit": "kg", "name": "floury potatoes (Maris Piper, russet), peeled and chunked"},
            {"quantity": 80, "unit": "g", "name": "unsalted butter"},
            {"quantity": 120, "unit": "ml", "name": "warm whole milk"},
            {"quantity": 1, "name": "egg yolk (for glaze)"},
            {"name": "salt, pepper"},
        ],
        "steps": [
            "Brown lamb in olive oil over high heat 8 minutes; drain off most fat.",
            "Add onions and carrots; cook 8 minutes until soft.",
            "Stir in garlic, tomato paste, Worcestershire, and thyme; cook 1 minute. Pour in stock, season, and simmer 25 minutes until thick. Stir in peas off heat.",
            "Boil potatoes in salted water 15 minutes until tender; drain and steam-dry 3 minutes.",
            "Mash with butter and warm milk until smooth (not gluey); season.",
            "Spoon meat into a 26-cm baking dish, top with mash, score with fork tines, brush with egg yolk for sheen, and bake at 200 C for 25-30 minutes until deep golden and bubbling at the edges.",
        ],
        "translations": {
            "zh": {
                "title": "王婏美",
                "description": "美婏米不当後为美婏美为美婏美为美婏美",
            },
            "ja": {
                "title": "シャンバーバー",
                "description": "シャンバーバーに不当後が婏ですがシャンバーバーを不当後が婏です",
            },
            "ko": {
                "title": "구가기가",
                "description": "구가기가当後가가가가가가가가가가가가",
            },
            "vi": {
                "title": "Bánh Pâté Chảo",
                "description": "Thịt cừu hầm chậm dưới lớp khoai tây nghiền béo, nướng cho đến khi có màu nâu vàng",
            },
        },
    },
    {
        "title": "Full English Breakfast",
        "description": "The whole works — bacon, sausage, egg, beans, mushrooms, tomato, and a slice of toast.",
        "cuisine": "british", "language": "en", "spice_level": 0,
        "prep": 10, "cook": 25, "servings": 2, "image": _img("full-english-breakfast"),
        "tags": ["breakfast", "weekend", "comfort"],
        "ingredients": [
            {"quantity": 4, "unit": "rashers", "name": "back bacon"},
            {"quantity": 4, "name": "pork sausages"},
            {"quantity": 1, "unit": "can", "name": "baked beans in tomato sauce (400 g)"},
            {"quantity": 4, "name": "chestnut mushrooms, halved"},
            {"quantity": 2, "name": "tomatoes, halved"},
            {"quantity": 2, "name": "large eggs"},
            {"quantity": 2, "unit": "slices", "name": "thick white bread"},
            {"quantity": 30, "unit": "g", "name": "unsalted butter"},
            {"quantity": 1, "unit": "tbsp", "name": "neutral oil"},
            {"quantity": 2, "name": "black pudding slices (optional, classic)"},
            {"name": "salt, pepper, brown sauce or ketchup"},
        ],
        "steps": [
            "Bake sausages at 200 C on a tray for 18 minutes, turning halfway, until deep golden.",
            "Halfway through the sausages, add tomatoes (cut-side up, oiled, salted) and mushrooms to the same tray for the last 10 minutes.",
            "Warm beans in a small pan over low heat — do not boil them aggressively or they go pasty.",
            "In a wide frying pan, sizzle bacon (and black pudding if using) over medium 4 minutes per side until crisp at the edges.",
            "Fry eggs in butter in a second pan, basting the whites with hot butter so the yolks stay soft. Toast bread and butter generously.",
            "Plate everything in separate piles like a proper greasy-spoon caff: bacon, sausage, eggs, beans, tomatoes, mushrooms, black pudding, and toast on the side. Bring brown sauce to the table.",
        ],
        "translations": {
            "zh": {
                "title": "英式全餐",
                "description": "培根、香肠、煎蛋、烤豆、蘑菇、番茄与吐司一应俱全的传统英式早餐。",
            },
            "ja": {
                "title": "フルイングリッシュ・ブレックファスト",
                "description": "ベーコン、ソーセージ、目玉焼き、ベイクドビーンズ、マッシュルーム、トマト、トーストを一皿に盛る、英国の伝統朝食。",
            },
            "ko": {
                "title": "풀 잉글리시 브렉퍼스트",
                "description": "베이컨, 소시지, 달걀 프라이, 베이크드 빈, 버섯, 토마토, 토스트까지 한 접시에 담아내는 영국의 전통 아침 식사.",
            },
            "vi": {
                "title": "Bữa sáng Anh đầy đủ",
                "description": "Bữa sáng truyền thống Anh đủ vị: thịt xông khói, xúc xích, trứng ốp, đậu sốt cà, nấm, cà chua nướng và bánh mì nướng bơ.",
            },
        },
    },
]

from scripts.cuisine_expansion_v5_east_asia import EAST_ASIA_EXPANSION_RECIPES  # noqa: E402
from scripts.cuisine_expansion_v6_original import ORIGINAL_EXPANSION_RECIPES  # noqa: E402
from scripts.cuisine_expansion_v7_myanmar import MYANMAR_EXPANSION_RECIPES  # noqa: E402

CURATED.extend(EAST_ASIA_EXPANSION_RECIPES)
CURATED.extend(ORIGINAL_EXPANSION_RECIPES)
CURATED.extend(MYANMAR_EXPANSION_RECIPES)

# Expansion modules overlap the base catalog; keep the first occurrence only.
_base_len = (
    len(CURATED)
    - len(EAST_ASIA_EXPANSION_RECIPES)
    - len(ORIGINAL_EXPANSION_RECIPES)
    - len(MYANMAR_EXPANSION_RECIPES)
)
_seen_titles = {r["title"] for r in CURATED[:_base_len]}
_deduped: list = []
for r in CURATED[_base_len:]:
    if r["title"] in _seen_titles:
        continue
    _deduped.append(r)
    _seen_titles.add(r["title"])
CURATED[:] = CURATED[:_base_len] + _deduped

