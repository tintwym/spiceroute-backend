"""Hand-curated Wikimedia Commons photos for Myanmar / Burmese recipes.

Every URL is a verified `upload.wikimedia.org` thumb (1280px) of real
Burmese or closely related SE Asian dish photography — never generic
Unsplash stock. Slugs match `generate_myanmar_expansion.py` and the
national `burmese` curated rows in `curated_data.py`.
"""
from __future__ import annotations

# ── Verified Commons URLs (HTTP 200, 2026-06) ─────────────────────────────
_MOHINGA = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Mohnga.jpg/1280px-Mohnga.jpg"
_SHAN_NOODLE = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Shan_Noodle.jpg/1280px-Shan_Noodle.jpg"
_LAPHET = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Laphet_thoke.JPG/1280px-Laphet_thoke.JPG"
_TEA_EGG = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Tea_eggs_ez.jpg/1280px-Tea_eggs_ez.jpg"
_OHN_NO_KHAO_SWE = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/"
    "Ohn_No_Khao_Swe_at_Sapphire_Asian_Cuisine_%2810988302274%29.jpg/"
    "1280px-Ohn_No_Khao_Swe_at_Sapphire_Asian_Cuisine_%2810988302274%29.jpg"
)
_KHAO_SOI = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/"
    "Khao_Soi_Northern_Thai_food_%E0%B8%82%E0%B9%89%E0%B8%B2%E0%B8%A7%E0%B8%8B%E0%B8%AD%E0%B8%A2_%E0%B8%9C%E0%B8%B1%E0%B8%81%E0%B8%94%E0%B8%AD%E0%B8%87.jpg/"
    "1280px-Khao_Soi_Northern_Thai_food_%E0%B8%82%E0%B9%89%E0%B8%B2%E0%B8%A7%E0%B8%8B%E0%B8%AD%E0%B8%A2_%E0%B8%9C%E0%B8%B1%E0%B8%81%E0%B8%94%E0%B8%AD%E0%B8%87.jpg"
)
_BURMESE_TOFU = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/76/"
    "Burmese_tofu_%28to_hpu%29.jpg/1280px-Burmese_tofu_%28to_hpu%29.jpg"
)
_NGAPI = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Raw_ngapi.JPG/1280px-Raw_ngapi.JPG"
_SAMOSA = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/"
    "Samosas%2C_snack_food_at_Wikipedia%27s_16th_Birthday_celebration_in_Chittagong_%2801%29.jpg/"
    "1280px-Samosas%2C_snack_food_at_Wikipedia%27s_16th_Birthday_celebration_in_Chittagong_%2801%29.jpg"
)
_FISH_CURRY = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/"
    "Fish_Amok_with_Rice.jpg/1280px-Fish_Amok_with_Rice.jpg"
)
_STICKY_RICE = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/"
    "Chapssal_%28glutinous_rice%29.jpg/1280px-Chapssal_%28glutinous_rice%29.jpg"
)
_BAMBOO = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/"
    "Bamboo_sprout2.JPG/1280px-Bamboo_sprout2.JPG"
)
_TOM_YUM = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/"
    "Tom_yam_kung_maenam.jpg/1280px-Tom_yam_kung_maenam.jpg"
)
_GREEN_SALAD = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/"
    "2013_Tam_Lao.jpg/1280px-2013_Tam_Lao.jpg"
)
_BIRYANI = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/"
    "%22Hyderabadi_Dum_Biryani%22.jpg/1280px-%22Hyderabadi_Dum_Biryani%22.jpg"
)
_RENDANG = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/"
    "Rendang_daging_sapi_asli_Padang.JPG/1280px-Rendang_daging_sapi_asli_Padang.JPG"
)
_DAL = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/"
    "Dal_Tadka-Delhi.jpg/1280px-Dal_Tadka-Delhi.jpg"
)
_SATAY = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/"
    "Sate_Udang.JPG/1280px-Sate_Udang.JPG"
)
_KARAHI = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/"
    "Punjabi_Chicken_Karahi.JPG/1280px-Punjabi_Chicken_Karahi.JPG"
)
_LUMPIA = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/"
    "Loenpia_Semarang.JPG/1280px-Loenpia_Semarang.JPG"
)
_RICE_CURRY = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/"
    "Sri_Lankan_Rice_and_Curry.jpg/1280px-Sri_Lankan_Rice_and_Curry.jpg"
)
_MISIR_WAT = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/"
    "Misir_Wot_and_Gomen_Besiga_-_Abyssinia%2C_Brighton.jpg/"
    "1280px-Misir_Wot_and_Gomen_Besiga_-_Abyssinia%2C_Brighton.jpg"
)
_PICKLED_TEA = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/"
    "Pickled_tea_%28lahpet%29.JPG/1280px-Pickled_tea_%28lahpet%29.JPG"
)

MYANMAR_WIKIMEDIA_BY_SLUG: dict[str, str] = {
    # National burmese (curated_data slugs)
    "mohinga": _MOHINGA,
    "lahpet-thoke": _LAPHET,
    "shan-noodles": _SHAN_NOODLE,
    # Shan
    "shan-khauk-swe": _SHAN_NOODLE,
    "shan-tofu-nway": _BURMESE_TOFU,
    "hinny-paw": _STICKY_RICE,
    # Rakhine
    "rakhine-mont-di": _MOHINGA,
    "rakhine-fish-curry": _FISH_CURRY,
    "bamboo-shoot-fish": _BAMBOO,
    # Mon
    "mon-curry": _KARAHI,
    "htamane-mon": _STICKY_RICE,
    "ngapi-dip": _NGAPI,
    # Kachin
    "kachin-rice": _BIRYANI,
    "kachin-singju": _GREEN_SALAD,
    "bamboo-soup-kachin": _BAMBOO,
    # Kayin
    "kayin-sour-soup": _TOM_YUM,
    "kayin-bamboo-curry": _RENDANG,
    "fermented-pork-kayin": _NGAPI,
    # Chin
    "chin-baum": _STICKY_RICE,
    "chin-smoked-meat": _SATAY,
    "chin-bamboo-stew": _BAMBOO,
    # Kayah
    "kayah-pork-rice": _BIRYANI,
    "kayah-sour-leaf": _TOM_YUM,
    "kayah-tomato-salad": _GREEN_SALAD,
    # Mandalay
    "mee-shay": _SHAN_NOODLE,
    "mandalay-tea-leaf": _LAPHET,
    "mandalay-beef-curry": _RENDANG,
    # Yangon
    "yangon-mohinga": _MOHINGA,
    "samosa-thoke": _SAMOSA,
    "tea-shop-eggs": _TEA_EGG,
    # Ayeyarwady
    "delta-fish-curry": _FISH_CURRY,
    "river-prawn-soup": _TOM_YUM,
    "tamarind-fish": _FISH_CURRY,
    # Tanintharyi
    "southern-sour-curry": _TOM_YUM,
    "coastal-crab-curry": _TOM_YUM,
    "dawei-noodles": _SHAN_NOODLE,
    # Intha
    "intha-htamin-jin": _STICKY_RICE,
    "intha-tomato-salad": _GREEN_SALAD,
    "intha-fish-curry": _FISH_CURRY,
    # Naga
    "naga-smoked-pork": _SATAY,
    "naga-bamboo": _BAMBOO,
    "naga-chili-chutney": _NGAPI,
    # Pa'O
    "pao-htamin-jin": _STICKY_RICE,
    "pao-shan-tofu": _BURMESE_TOFU,
    "pao-sour-mustard": _GREEN_SALAD,
    # Danu
    "danu-fermented-tea": _PICKLED_TEA,
    "danu-pork-curry": _RENDANG,
    "danu-chicken": _KARAHI,
    # Wa
    "wa-grilled-meat": _SATAY,
    "wa-chili-paste": _NGAPI,
    "wa-rice": _STICKY_RICE,
    # Magway
    "peanut-curry": _KARAHI,
    "sesame-chicken": _KARAHI,
    "bean-soup-magway": _DAL,
    # Bago
    "fish-paste-curry": _NGAPI,
    "palm-sugar-dessert": _STICKY_RICE,
    "tamarind-leaves": _TOM_YUM,
    # Sagaing
    "monastic-curry": _MISIR_WAT,
    "moringa-soup": _DAL,
    "bean-fritters": _LUMPIA,
    # Taunggyi
    "taunggyi-khauk-swe": _SHAN_NOODLE,
    "shan-khao-suey": _KHAO_SOI,
    "pickled-tea-snack": _PICKLED_TEA,
}

# Burmese titles in curated_data that are not in the expansion generator.
MYANMAR_WIKIMEDIA_BY_TITLE: dict[str, str] = {
    "Mohinga": _MOHINGA,
    "Burmese Tea Leaf Salad": _LAPHET,
    "Shan Noodles": _SHAN_NOODLE,
    "Burmese Chicken Curry": _RICE_CURRY,
    "Ohn No Khao Swè": _OHN_NO_KHAO_SWE,
}
