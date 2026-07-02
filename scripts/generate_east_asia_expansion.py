"""One-shot generator for v5 East Asia cuisine expansion recipes.

Run: uv run python -m scripts.generate_east_asia_expansion
Writes: scripts/cuisine_expansion_v5_east_asia.py
"""

from __future__ import annotations

from pathlib import Path

from app.models.cuisine_catalog import (
    CHINESE_SUBNATIONAL_WIRES,
    MYANMAR_REGIONAL_WIRES,
)


def _seed_cuisine(wire: str) -> str:
    if wire in CHINESE_SUBNATIONAL_WIRES:
        return "chinese"
    if wire in MYANMAR_REGIONAL_WIRES:
        return "burmese"
    if wire == "okinawan":
        return "japanese"
    return wire

# (wire, slug, title, description, spice, tags, ingredients, steps)
_DISHES: list[tuple] = [
    # mongolian
    ("mongolian", "buuz", "Mongolian Buuz", "Steamed meat-filled dumplings, Mongolia's national comfort food.", 0,
     ["dumpling", "steamed", "comfort"],
     ["500 g ground lamb", "1 onion, minced", "2 cloves garlic", "1 tsp salt", "black pepper", "350 g flour", "warm water"],
     ["Mix lamb with onion, garlic, salt, and pepper.", "Knead flour and water into a firm dough; rest 20 min.", "Roll small discs; fill and pleat into buuz.", "Steam 18–20 minutes until cooked through.", "Serve hot with tea."]),
    ("mongolian", "khuushuur", "Khuushuur", "Crisp fried meat pastries eaten at Naadam festivals.", 0,
     ["fried", "festival", "handheld"],
     ["400 g ground beef", "1 onion, diced", "2 cloves garlic", "1 tsp cumin", "flour", "oil for frying"],
     ["Season beef with onion, garlic, cumin, salt.", "Roll dough thin; cut circles and fill.", "Fold into half-moon and crimp edges.", "Deep-fry until golden and crisp.", "Drain and serve immediately."]),
    ("mongolian", "tsuivan", "Tsuivan", "Hand-pulled noodles stir-fried with meat and vegetables.", 1,
     ["noodles", "stir-fry", "weeknight"],
     ["300 g flour noodles", "200 g beef, sliced", "1 carrot", "1 onion", "2 tbsp soy sauce", "1 tbsp oil"],
     ["Boil noodles until al dente; drain.", "Stir-fry beef until browned; set aside.", "Sauté carrot and onion.", "Toss noodles, beef, and soy sauce over high heat.", "Serve steaming hot."]),
    # tibetan
    ("tibetan", "momo", "Tibetan Momo", "Juicy steamed dumplings with spiced meat or vegetable filling.", 1,
     ["dumpling", "steamed", "snack"],
     ["300 g ground yak or beef", "1 cup cabbage, shredded", "2 tbsp soy sauce", "ginger-garlic paste", "flour dough"],
     ["Mix filling with cabbage, soy, ginger, and garlic.", "Shape dough into wrappers.", "Fill and pleat momo tightly.", "Steam 12–15 minutes.", "Serve with chili-tomato dipping sauce."]),
    ("tibetan", "thukpa", "Thukpa", "Hearty noodle soup with bone broth and warming spices.", 1,
     ["soup", "noodles", "comfort"],
     ["200 g wheat noodles", "500 ml beef broth", "100 g beef, sliced", "spinach", "garlic", "Sichuan pepper"],
     ["Simmer broth with garlic and pepper.", "Cook noodles separately.", "Blanch spinach briefly.", "Assemble bowls with noodles, beef, spinach, and hot broth.", "Finish with fresh cilantro."]),
    ("tibetan", "sha-balep", "Sha Balep", "Pan-fried meat pies with flaky crust.", 0,
     ["pastry", "fried", "handheld"],
     ["300 g minced beef", "1 onion", "2 cups flour", "butter", "cumin", "oil"],
     ["Make shortcrust with flour and butter.", "Cook spiced beef-onion filling.", "Fill rounds and fold into crescents.", "Pan-fry until golden both sides.", "Rest 2 minutes before serving."]),
    # hong_kong
    ("hong_kong", "char-siu", "Char Siu", "Glossy Cantonese barbecue pork with maltose lacquer.", 0,
     ["roast", "pork", "classic"],
     ["800 g pork shoulder", "hoisin sauce", "soy sauce", "honey", "five-spice", "red food coloring optional"],
     ["Marinate pork overnight in hoisin, soy, honey, five-spice.", "Roast at 200°C, basting every 15 min.", "Glaze with honey in final 10 min.", "Rest and slice against the grain.", "Serve with steamed rice."]),
    ("hong_kong", "wonton-noodle-soup", "Wonton Noodle Soup", "Silky egg noodles in clear broth with shrimp wontons.", 0,
     ["soup", "noodles", "classic"],
     ["fresh egg noodles", "200 g shrimp", "pork mince", "wonton wrappers", "chicken stock", "choy sum"],
     ["Mix shrimp and pork filling; wrap wontons.", "Blanch noodles and greens.", "Poach wontons in simmering stock.", "Assemble bowls with noodles, wontons, and greens.", "Top with scallion oil."]),
    ("hong_kong", "egg-tart", "Hong Kong Egg Tart", "Buttery pastry cups with silky baked custard.", 0,
     ["dessert", "baked", "cafe"],
     ["puff pastry", "3 eggs", "200 ml milk", "sugar", "vanilla"],
     ["Line tart molds with pastry.", "Whisk eggs, milk, sugar, and vanilla.", "Strain custard into shells.", "Bake at 200°C until set with light caramel spots.", "Cool slightly before serving."]),
    # macanese
    ("macanese", "african-chicken", "African Chicken", "Macanese braised chicken in rich coconut and peanut sauce.", 1,
     ["braised", "chicken", "fusion"],
     ["1 whole chicken, cut up", "coconut milk", "peanut butter", "paprika", "bay leaves", "onion"],
     ["Brown chicken pieces.", "Sauté onion and spices.", "Add coconut milk and peanut butter; simmer 40 min.", "Reduce sauce until thick and glossy.", "Serve with rice."]),
    ("macanese", "minchi", "Minchi", "Minced beef and potato hash, Macau's everyday comfort plate.", 0,
     ["beef", "comfort", "weeknight"],
     ["400 g ground beef", "2 potatoes, diced", "soy sauce", "Worcestershire", "onion", "fried egg"],
     ["Dice and parboil potatoes.", "Brown beef with onion.", "Add potatoes, soy, and Worcestershire.", "Cook until potatoes crisp at edges.", "Top with fried egg."]),
    ("macanese", "pork-chop-bun", "Pork Chop Bun", "Crispy fried pork cutlet in a sweet soft bun.", 0,
     ["sandwich", "fried", "street food"],
     ["pork chops", "flour", "eggs", "breadcrumbs", "soft buns", "sugar glaze"],
     ["Pound and marinate pork chops.", "Bread and deep-fry until golden.", "Glaze buns lightly with sugar butter.", "Sandwich chop in bun.", "Serve warm."]),
    # sichuan
    ("sichuan", "kung-pao-chicken", "Kung Pao Chicken", "Wok-tossed chicken with peanuts, chilies, and Sichuan pepper.", 3,
     ["stir-fry", "spicy", "classic"],
     ["400 g chicken thigh", "roasted peanuts", "dried chilies", "Sichuan pepper", "soy sauce", "black vinegar"],
     ["Dice chicken; marinate in soy and starch.", "Stir-fry chilies and pepper until fragrant.", "Sear chicken over high heat.", "Add sauce, peanuts; toss quickly.", "Serve with steamed rice."]),
    ("sichuan", "dan-dan-noodles", "Dan Dan Noodles", "Noodles in spicy sesame-chili sauce with preserved mustard.", 3,
     ["noodles", "spicy", "street food"],
     ["fresh wheat noodles", "sesame paste", "chili oil", "ya cai", "ground pork", "Sichuan pepper"],
     ["Cook pork with ya cai until crisp.", "Whisk sesame paste, chili oil, soy, and vinegar.", "Boil noodles; drain.", "Toss noodles with sauce.", "Top with pork and scallions."]),
    ("sichuan", "mapo-tofu-sichuan", "Sichuan Mapo Tofu", "Silken tofu in fiery doubanjiang and minced pork sauce.", 3,
     ["tofu", "spicy", "classic"],
     ["400 g silken tofu", "150 g pork mince", "doubanjiang", "Sichuan pepper", "garlic", "stock"],
     ["Brown pork with doubanjiang and garlic.", "Add stock and simmer.", "Slide in tofu gently; do not stir hard.", "Thicken with starch slurry.", "Finish with ground Sichuan pepper."]),
    # cantonese
    ("cantonese", "har-gow", "Har Gow", "Translucent shrimp dumplings, dim sum classic.", 0,
     ["dim sum", "steamed", "seafood"],
     ["300 g shrimp", "wheat starch dough", "bamboo shoots", "sesame oil", "white pepper"],
     ["Chop shrimp coarsely with bamboo shoots.", "Season with oil and pepper.", "Wrap in thin starch skins.", "Pleat har gow shape.", "Steam 6–7 minutes until pink."]),
    ("cantonese", "char-siu-bao", "Char Siu Bao", "Fluffy steamed buns filled with sweet barbecue pork.", 0,
     ["dim sum", "steamed", "pork"],
     ["char siu pork, diced", "hoisin", "sugar", "yeast dough"],
     ["Dice char siu; bind with hoisin and sugar.", "Proof yeast dough until airy.", "Fill buns and pleat tops closed.", "Steam 12 minutes.", "Serve hot from the steamer."]),
    ("cantonese", "clay-pot-rice", "Clay Pot Rice", "Crisp-bottom rice with lap cheong and soy glaze.", 0,
     ["rice", "comfort", "classic"],
     ["jasmine rice", "Chinese sausage", "soy sauce", "ginger", "scallion", "clay pot"],
     ["Soak rice 30 minutes.", "Cook rice in clay pot with sausage on top.", "Drizzle soy around edges for crust.", "Rest off heat 5 min.", "Garnish with ginger and scallion."]),
    # shanghainese
    ("shanghainese", "xiaolongbao", "Xiaolongbao", "Soup-filled pork dumplings with delicate pleated skins.", 0,
     ["dumpling", "steamed", "classic"],
     ["ground pork", "aspic", "flour", "ginger", "Shaoxing wine"],
     ["Set pork aspic into filling.", "Roll thin wrappers.", "Pleat 18 folds per bun.", "Steam in bamboo baskets 8 min.", "Serve with black vinegar and ginger."]),
    ("shanghainese", "red-braised-pork", "Red-Braised Pork Belly", "Hong shao rou — sweet soy-braised pork belly.", 1,
     ["braised", "pork", "classic"],
     ["600 g pork belly", "Shaoxing wine", "dark soy", "rock sugar", "ginger", "star anise"],
     ["Blanch belly; cut into cubes.", "Caramelize rock sugar.", "Braise with soy, wine, ginger, anise 90 min.", "Reduce sauce until glossy.", "Serve with steamed rice."]),
    ("shanghainese", "lion-head-meatballs", "Lion's Head Meatballs", "Giant pork meatballs braised with cabbage.", 0,
     ["braised", "pork", "comfort"],
     ["500 g pork mince", "water chestnuts", "Napa cabbage", "soy sauce", "ginger"],
     ["Mix pork with chestnuts and seasonings.", "Form large meatballs.", "Layer cabbage in pot; nestle meatballs.", "Simmer in light soy broth 45 min.", "Serve in deep bowls."]),
    # fujian
    ("fujian", "buddha-jumps-wall", "Buddha Jumps Over the Wall", "Luxurious slow-simmered seafood and poultry soup.", 0,
     ["soup", "banquet", "seafood"],
     ["abalone", "sea cucumber", "chicken", "ham", "Shaoxing wine", "stock"],
     ["Soak dried delicacies overnight.", "Layer ingredients in clay jar.", "Seal and simmer gently 4 hours.", "Unseal; adjust seasoning.", "Serve ceremonially in the jar."]),
    ("fujian", "oyster-omelette", "Oyster Omelette", "Crisp-edged egg pancake studded with plump oysters.", 0,
     ["seafood", "street food", "snack"],
     ["fresh oysters", "eggs", "sweet potato starch", "garlic chives", "chili sauce"],
     ["Mix starch slurry with eggs.", "Fry oysters until edges curl.", "Pour batter; crisp both sides.", "Top with chives.", "Serve with chili sauce."]),
    ("fujian", "red-wine-chicken", "Red Wine Chicken", "Fujian chicken braised in glutinous rice wine.", 0,
     ["braised", "chicken", "classic"],
     ["1 chicken, cut up", "Fujian red wine", "ginger", "sesame oil", "rock sugar"],
     ["Sear chicken in sesame oil.", "Add ginger and wine.", "Braise covered 35 min.", "Glaze with reduced wine.", "Serve warm."]),
    # hunan
    ("hunan", "chairman-maos-pork", "Chairman's Red-Braised Pork", "Hunan-style caramelized pork belly with chilies.", 2,
     ["braised", "pork", "spicy"],
     ["pork belly", "dried chilies", "dark soy", "Shaoxing wine", "garlic"],
     ["Blanch and cube belly.", "Render fat; fry chilies and garlic.", "Braise with soy and wine until tender.", "Reduce to sticky glaze.", "Serve with rice."]),
    ("hunan", "steamed-fish-head", "Steamed Fish Head with Chilies", "Fiery chopped chili blanket over tender fish head.", 3,
     ["steamed", "fish", "spicy"],
     ["fish head", "chopped salted chilies", "ginger", "garlic", "steaming wine"],
     ["Clean fish head; score flesh.", "Top with ginger and chopped chilies.", "Steam 12–15 minutes.", "Sizzle hot oil over aromatics.", "Serve immediately."]),
    ("hunan", "stir-fried-pork-liver", "Stir-Fried Pork Liver", "Quick wok dish with pickled peppers and garlic shoots.", 2,
     ["stir-fry", "offal", "weeknight"],
     ["300 g pork liver", "pickled peppers", "garlic shoots", "soy sauce", "vinegar"],
     ["Slice liver thin; soak in milk.", "Blanch briefly; drain.", "Stir-fry peppers and shoots.", "Toss liver with sauce at high heat.", "Serve right away."]),
    # yunnan
    ("yunnan", "crossing-bridge-noodles", "Crossing the Bridge Noodles", "DIY noodle soup with sizzling chicken fat seal.", 1,
     ["soup", "noodles", "classic"],
     ["rice noodles", "chicken slices", "quail eggs", "chicken fat", "rich stock"],
     ["Keep stock piping hot with oil layer.", "Arrange raw toppings on plate.", "Slide ingredients into bowl.", "Pour boiling stock to cook proteins.", "Add noodles last."]),
    ("yunnan", "steam-pot-chicken", "Steam Pot Chicken", "Yunnan chicken slowly steamed with herbs in terra-cotta pot.", 0,
     ["steamed", "chicken", "herbal"],
     ["whole chicken", "goji berries", "red dates", "ginger", "Yunnan ham"],
     ["Stuff chicken with herbs.", "Place in steam pot with ham and dates.", "Steam 3 hours on low heat.", "Skim and season broth.", "Serve chicken shredded in soup."]),
    ("yunnan", "erkuai", "Erkuai Stir-Fry", "Grilled rice cake stir-fried with ham and greens.", 0,
     ["rice", "stir-fry", "street food"],
     ["erkuai rice cakes", "Xuanwei ham", "garlic chives", "soy sauce"],
     ["Slice erkuai into strips.", "Char lightly on griddle.", "Stir-fry ham and chives.", "Toss erkuai with soy.", "Serve hot."]),
    # beijing
    ("beijing", "peking-duck", "Peking Duck", "Crisp lacquered duck with pancakes and hoisin.", 0,
     ["roast", "duck", "banquet"],
     ["whole duck", "maltose glaze", "pancakes", "hoisin", "cucumber", "scallion"],
     ["Air-dry duck; brush maltose.", "Roast until skin shatters.", "Carve tableside.", "Wrap slices in pancakes with hoisin and veg.", "Serve with duck soup from bones."]),
    ("beijing", "zhajiangmian", "Zhajiangmian", "Noodles with savory fermented soybean paste pork sauce.", 0,
     ["noodles", "comfort", "classic"],
     ["thick wheat noodles", "ground pork", "sweet bean paste", "cucumber", "bean sprouts"],
     ["Brown pork; stir in bean paste.", "Simmer sauce until thick.", "Boil noodles.", "Top with julienned cucumber and sprouts.", "Toss with sauce."]),
    ("beijing", "jingjiang-rousi", "Jingjiang Rousi", "Shredded pork in sweet bean sauce with scallion pockets.", 0,
     ["stir-fry", "pork", "classic"],
     ["pork tenderloin", "sweet bean sauce", "scallion", "pancakes", "sugar"],
     ["Shred and velvet pork.", "Stir-fry sauce until bubbling.", "Toss pork quickly.", "Serve with scallion in pancakes.", "Roll and eat by hand."]),
    # dongbei
    ("dongbei", "guobaorou", "Guobaorou", "Northeast sweet-and-sour crispy pork slices.", 0,
     ["fried", "pork", "classic"],
     ["pork tenderloin", "potato starch", "sugar", "vinegar", "carrot", "ginger"],
     ["Double-fry pork until crisp.", "Wok-toss with sweet-sour glaze.", "Add carrot and ginger strips.", "Coat evenly and serve fast.", "Eat while crunchy."]),
    ("dongbei", "di-san-xian", "Di San Xian", "Stir-fried potato, eggplant, and green pepper.", 0,
     ["stir-fry", "vegetarian", "comfort"],
     ["potato", "eggplant", "green pepper", "garlic", "soy sauce"],
     ["Fry potato and eggplant separately.", "Stir-fry pepper and garlic.", "Combine with light soy.", "Toss until glossy.", "Serve with rice."]),
    ("dongbei", "dongbei-dumplings", "Dongbei Dumplings", "Hearty pork-and-cabbage boiled dumplings.", 0,
     ["dumpling", "boiled", "comfort"],
     ["ground pork", "Napa cabbage", "flour dough", "ginger", "soy sauce"],
     ["Salt cabbage; squeeze dry.", "Mix filling with pork and ginger.", "Wrap dumplings.", "Boil until floating plus 2 min.", "Serve with vinegar dip."]),
    # hakka
    ("hakka", "salt-baked-chicken", "Salt-Baked Chicken", "Whole chicken encrusted in hot salt until juicy.", 0,
     ["baked", "chicken", "classic"],
     ["whole chicken", "coarse salt", "sand ginger", "star anise", "foil"],
     ["Rub chicken with sand ginger.", "Pack in heated salt crust.", "Bake 1 hour.", "Crack salt; brush off.", "Chop and serve."]),
    ("hakka", "stuffed-tofu", "Hakka Stuffed Tofu", "Firm tofu pockets filled with seasoned pork.", 0,
     ["tofu", "braised", "comfort"],
     ["firm tofu", "pork mince", "shiitake", "scallion", "stock"],
     ["Hollow tofu cubes.", "Stuff with pork and mushroom mix.", "Pan-fry then braise in stock.", "Reduce sauce.", "Garnish with scallion."]),
    ("hakka", "lei-cha", "Lei Cha", "Ground tea porridge with grains and herbs.", 0,
     ["porridge", "herbal", "healthy"],
     ["green tea leaves", "peanuts", "sesame", "rice", "mint", "tofu"],
     ["Pound tea, nuts, and herbs to paste.", "Cook rice porridge.", "Stir in lei cha paste.", "Top with crispy toppings.", "Serve warm."]),
    # uyghur
    ("uyghur", "laghman", "Laghman", "Hand-pulled noodles with lamb and bell peppers.", 2,
     ["noodles", "lamb", "spicy"],
     ["hand-pulled noodles", "lamb", "bell pepper", "tomato", "garlic", "cumin"],
     ["Pull noodles fresh or use thick wheat noodles.", "Stir-fry lamb with cumin.", "Add peppers and tomato.", "Toss noodles in wok.", "Serve with chili vinegar."]),
    ("uyghur", "polo", "Uyghur Polo", "Pilaf rice with lamb, carrots, and raisins.", 1,
     ["rice", "lamb", "pilaf"],
     ["basmati rice", "lamb shoulder", "carrot sticks", "onion", "raisins", "cumin"],
     ["Brown lamb; add onion and carrot.", "Layer rice over meat.", "Steam until rice fluffy.", "Fold in raisins.", "Serve on large platter."]),
    ("uyghur", "samsa", "Samsa", "Baked lamb-filled pastries from a tandoor-style oven.", 1,
     ["baked", "lamb", "handheld"],
     ["lamb mince", "onion", "cumin", "flour dough", "egg wash"],
     ["Season lamb filling.", "Shape triangular pastries.", "Brush with egg.", "Bake at 220°C until golden.", "Serve hot."]),
    # okinawan
    ("okinawan", "goya-champuru", "Goya Champuru", "Bitter melon stir-fry with tofu and egg.", 0,
     ["stir-fry", "vegetarian", "classic"],
     ["bitter melon", "firm tofu", "eggs", "pork optional", "soy sauce"],
     ["Salt bitter melon; blanch.", "Scramble eggs; set aside.", "Stir-fry tofu and melon.", "Toss with eggs and soy.", "Serve with rice."]),
    ("okinawan", "rafute", "Rafute", "Okinawan pork belly simmered in awamori and soy.", 0,
     ["braised", "pork", "comfort"],
     ["pork belly", "awamori or sake", "soy sauce", "brown sugar", "ginger"],
     ["Blanch belly.", "Simmer in awamori, soy, sugar 2 hours.", "Cool and slice thick.", "Glaze in reduced sauce.", "Serve with mustard pickle."]),
    ("okinawan", "taco-rice", "Taco Rice", "Okinawa fusion — seasoned beef on rice with salsa and cheese.", 1,
     ["rice", "fusion", "casual"],
     ["cooked rice", "ground beef", "taco seasoning", "lettuce", "cheese", "salsa"],
     ["Season and brown beef.", "Layer hot rice in bowls.", "Top with beef, lettuce, cheese.", "Add salsa and hot sauce.", "Serve immediately."]),
    # shandong
    ("shandong", "sweet-sour-carp", "Sweet and Sour Carp", "Whole fried carp in glossy Shandong sauce.", 0,
     ["fish", "fried", "banquet"],
     ["whole carp", "vinegar", "sugar", "soy", "ginger", "starch"],
     ["Score and fry carp until crisp.", "Wok-toss with sweet-sour sauce.", "Pour over fish.", "Garnish with cilantro.", "Serve whole."]),
    ("shandong", "dezhou-braised-chicken", "Dezhou Braised Chicken", "Famous braised chicken with aromatic spices.", 0,
     ["braised", "chicken", "classic"],
     ["whole chicken", "soy sauce", "star anise", "cassia", "cloves", "rock sugar"],
     ["Blanch chicken.", "Braise in spiced soy 1 hour.", "Cool in broth for flavor.", "Chop and serve.", "Brush with reduced sauce."]),
    ("shandong", "jianbing", "Jianbing", "Crispy crepe with egg, cracker, and sauces.", 0,
     ["street food", "breakfast", "crepe"],
     ["mung bean batter", "egg", "crispy cracker", "hoisin", "chili", "scallion"],
     ["Spread batter on griddle.", "Crack egg; scatter scallion.", "Add cracker; fold.", "Brush sauces.", "Roll and serve hot."]),
    # guangxi
    ("guangxi", "snail-rice-noodles", "Luosifen", "Famous Liuzhou snail rice noodles with fermented bamboo.", 2,
     ["noodles", "soup", "spicy"],
     ["rice noodles", "snail broth", "pickled bamboo", "peanuts", "fried tofu", "chili oil"],
     ["Simmer snail and pork bone broth.", "Cook rice noodles.", "Assemble with toppings.", "Pour hot broth.", "Add chili oil to taste."]),
    ("guangxi", "beer-fish", "Guilin Beer Fish", "Fresh river fish braised in local beer.", 1,
     ["fish", "braised", "classic"],
     ["whole freshwater fish", "beer", "tomato", "chili", "ginger"],
     ["Fry fish until golden.", "Add beer, tomato, chili.", "Braise 15 minutes.", "Reduce sauce.", "Serve in wok."]),
    ("guangxi", "sticky-rice-dumplings", "Zongzi", "Glutinous rice dumplings wrapped in bamboo leaves.", 0,
     ["rice", "steamed", "festival"],
     ["glutinous rice", "pork belly", "mung beans", "bamboo leaves", "string"],
     ["Soak rice and leaves.", "Layer rice, pork, beans in leaves.", "Fold and tie tightly.", "Boil 3 hours.", "Cool before unwrapping."]),
    # teochew
    ("teochew", "teochew-oyster-omelette", "Teochew Oyster Omelette", "Wok-fried oyster omelette with fish sauce edge.", 0,
     ["seafood", "street food", "snack"],
     ["oysters", "eggs", "sweet potato starch", "fish sauce", "cilantro"],
     ["Mix starch batter.", "Fry oysters until plump.", "Add eggs; crisp edges.", "Season with fish sauce.", "Garnish with cilantro."]),
    ("teochew", "braised-goose", "Teochew Braised Goose", "Whole goose braised in master stock.", 0,
     ["braised", "poultry", "classic"],
     ["whole goose", "master stock", "star anise", "cassia", "dark soy"],
     ["Blanch goose.", "Braise in stock 2 hours.", "Cool in broth.", "Chop into pieces.", "Serve with plum sauce."]),
    ("teochew", "crystal-dumplings", "Teochew Crystal Dumplings", "Translucent tapioca-skinned shrimp dumplings.", 0,
     ["dim sum", "steamed", "seafood"],
     ["shrimp", "pork fat", "tapioca starch dough", "bamboo shoots"],
     ["Chop filling finely.", "Shape translucent wrappers.", "Pleat dumplings.", "Steam 8 minutes.", "Serve with chili oil."]),
    # hainanese
    ("hainanese", "hainan-chicken-rice", "Hainanese Chicken Rice", "Poached chicken with fragrant ginger rice.", 0,
     ["chicken", "rice", "classic"],
     ["whole chicken", "jasmine rice", "ginger", "garlic", "pandan", "chili sauce"],
     ["Poach chicken in ginger broth.", "Cook rice in chicken fat and broth.", "Ice chicken for silky skin.", "Chop and serve with rice.", "Offer ginger, chili, and dark soy."]),
    ("hainanese", "wenchang-chicken", "Wenchang Chicken", "Hainan's famous free-range poached chicken.", 0,
     ["chicken", "poached", "classic"],
     ["Wenchang chicken", "ginger", "salt", "chicken stock", "coconut optional"],
     ["Rub chicken with salt.", "Poach gently 40 min.", "Shock in ice water.", "Chop and plate.", "Serve with ginger-scallion oil."]),
    ("hainanese", "coconut-rice", "Hainan Coconut Rice", "Steamed rice cooked in fresh coconut water.", 0,
     ["rice", "coconut", "side"],
     ["jasmine rice", "coconut water", "coconut meat", "salt"],
     ["Rinse rice.", "Cook in coconut water.", "Fold in young coconut.", "Steam until fluffy.", "Serve with curry or chicken."]),
    # jiangsu
    ("jiangsu", "squirrel-fish", "Squirrel Fish", "Deep-fried fish in sweet tomato glaze.", 0,
     ["fish", "fried", "banquet"],
     ["whole fish", "tomato sauce", "sugar", "vinegar", "pine nuts"],
     ["Score fish into squirrel shape.", "Deep-fry until crisp.", "Toss in sweet-sour tomato sauce.", "Garnish with pine nuts.", "Serve immediately."]),
    ("jiangsu", "yangzhou-fried-rice", "Yangzhou Fried Rice", "Refined fried rice with ham, shrimp, and egg.", 0,
     ["rice", "fried", "classic"],
     ["day-old rice", "ham", "shrimp", "eggs", "peas", "scallion"],
     ["Scramble eggs; set aside.", "Stir-fry ham and shrimp.", "Add rice; toss over high heat.", "Fold in eggs and peas.", "Finish with scallion."]),
    ("jiangsu", "braised-lion-meatballs", "Braised Lion's Head", "Jiangsu giant meatballs in light broth.", 0,
     ["braised", "pork", "comfort"],
     ["pork mince", "water chestnut", "cabbage", "stock", "ginger"],
     ["Form large meatballs.", "Sear lightly.", "Braise in stock with cabbage.", "Simmer 50 min.", "Serve in bowls."]),
    # zhejiang
    ("zhejiang", "west-lake-fish", "West Lake Fish in Vinegar", "Hangzhou poached fish in sweet vinegar sauce.", 0,
     ["fish", "poached", "classic"],
     ["grass carp", "Zhenjiang vinegar", "sugar", "ginger", "stock"],
     ["Poach fish until just cooked.", "Reduce vinegar-sugar sauce.", "Pour over fish.", "Garnish with ginger.", "Serve warm."]),
    ("zhejiang", "beggars-chicken", "Beggar's Chicken", "Clay-wrapped lotus-leaf chicken baked in embers.", 0,
     ["baked", "chicken", "banquet"],
     ["whole chicken", "lotus leaves", "clay", "Shaoxing wine", "ham", "mushrooms"],
     ["Stuff chicken with ham and mushrooms.", "Wrap in lotus and clay.", "Bake 3 hours.", "Crack clay at table.", "Serve aromatic meat."]),
    ("zhejiang", "dongpo-pork", "Dongpo Pork", "Slow-braised pork belly named for poet Su Dongpo.", 0,
     ["braised", "pork", "classic"],
     ["pork belly", "Shaoxing wine", "soy sauce", "rock sugar", "ginger"],
     ["Blanch belly.", "Braise with wine and soy 2 hours.", "Flip once for even color.", "Reduce to lacquer glaze.", "Serve with steamed buns."]),
    # anhui
    ("anhui", "stinky-tofu", "Stinky Tofu", "Fermented tofu deep-fried with chili dip.", 2,
     ["tofu", "fried", "street food"],
     ["fermented tofu", "oil", "chili sauce", "pickled veg"],
     ["Pat tofu dry.", "Deep-fry until puffed and crisp.", "Drain well.", "Serve with chili and pickles.", "Eat hot."]),
    ("anhui", "bamboo-shoot-stew", "Bamboo Shoot Stew", "Fresh bamboo simmered with pork and ham.", 0,
     ["stew", "pork", "seasonal"],
     ["fresh bamboo shoots", "pork belly", "ham", "stock", "ginger"],
     ["Blanch bamboo to remove bitterness.", "Brown pork.", "Simmer all in stock 45 min.", "Adjust seasoning.", "Serve in clay pot."]),
    ("anhui", "hair-tofu", "Hairy Tofu", "Anhui fermented tofu with fine mold 'hairs'.", 1,
     ["tofu", "fermented", "regional"],
     ["hairy tofu", "chili oil", "garlic", "scallion"],
     ["Steam tofu gently.", "Top with chili oil and garlic.", "Garnish scallion.", "Serve as appetizer.", "Pair with rice wine."]),
    # jiangxi
    ("jiangxi", "clay-pot-soup", "Jiangxi Clay Pot Soup", "Slow-simmered soup in individual clay pots.", 0,
     ["soup", "comfort", "classic"],
     ["pork ribs", "lotus root", "red dates", "ginger", "stock"],
     ["Blanch ribs.", "Layer in clay pot with lotus and dates.", "Simmer 2 hours.", "Season lightly.", "Serve bubbling hot."]),
    ("jiangxi", "steamed-pork-ribs", "Steamed Pork Ribs with Rice Flour", "Fen zheng rou — tender steamed rib coins.", 1,
     ["steamed", "pork", "spicy"],
     ["pork ribs", "rice flour", "chili paste", "garlic", "sweet potato"],
     ["Cut ribs into coins.", "Coat with spiced rice flour.", "Layer over sweet potato.", "Steam 45 minutes.", "Garnish with scallion."]),
    ("jiangxi", "nanchang-mixed-noodles", "Nanchang Mixed Noodles", "Cold noodles tossed with chili and peanuts.", 2,
     ["noodles", "spicy", "street food"],
     ["wheat noodles", "chili oil", "peanuts", "pickled veg", "soy"],
     ["Boil and cool noodles.", "Toss with chili oil and soy.", "Add peanuts and pickles.", "Mix thoroughly.", "Serve at room temp."]),
    # guizhou
    ("guizhou", "sour-fish-soup", "Guizhou Sour Fish Soup", "Tomato and pickled chili fish soup.", 2,
     ["soup", "fish", "spicy"],
     ["fish fillets", "pickled chilies", "tomato", "ginger", "herbs"],
     ["Fry pickled chilies and tomato.", "Add stock; simmer.", "Slide in fish.", "Finish with herbs.", "Serve with rice."]),
    ("guizhou", "siwawa", "Siwawa", "DIY rice-paper rolls with shredded fillings.", 0,
     ["wrap", "vegetarian", "snack"],
     ["rice paper rounds", "shredded vegetables", "tofu strips", "dipping sauce"],
     ["Prep assorted shredded fillings.", "Steam rice paper soft.", "Fill and roll at table.", "Dip in spicy sauce.", "Eat fresh."]),
    ("guizhou", "glutinous-rice-rolls", "Glutinous Rice Rolls", "Sticky rice rolls with sweet or savory filling.", 0,
     ["rice", "snack", "street food"],
     ["glutinous rice", "sugar or pork filling", "bamboo leaves"],
     ["Cook sticky rice.", "Spread filling.", "Roll tightly in leaves.", "Steam 30 min.", "Slice and serve."]),
    # manchurian
    ("manchurian", "manchurian-chicken", "Manchurian Chicken", "Crispy chicken in tangy Indo-Chinese sauce.", 2,
     ["fried", "chicken", "fusion"],
     ["chicken", "cornstarch", "soy sauce", "ginger", "garlic", "green chili"],
     ["Fry battered chicken crisp.", "Stir-fry ginger, garlic, chili.", "Toss with soy-vinegar glaze.", "Garnish scallion.", "Serve hot."]),
    ("manchurian", "suan-cai-stew", "Suan Cai Stew", "Northeast sour cabbage and pork hot pot.", 1,
     ["stew", "pork", "comfort"],
     ["sour cabbage", "pork belly", "glass noodles", "stock", "chili"],
     ["Render pork.", "Add sour cabbage and stock.", "Simmer 40 min.", "Add noodles last.", "Serve in deep bowls."]),
    ("manchurian", "manchurian-meatballs", "Manchurian Meatballs", "Large beef meatballs in brown gravy.", 0,
     ["meatballs", "beef", "comfort"],
     ["ground beef", "breadcrumbs", "onion", "soy", "star anise", "stock"],
     ["Form and brown meatballs.", "Braise in spiced gravy.", "Simmer until tender.", "Thicken sauce.", "Serve with rice."]),
    # shaanxi
    ("shaanxi", "biang-biang-noodles", "Biang Biang Noodles", "Wide hand-pulled belt noodles with chili oil.", 2,
     ["noodles", "spicy", "classic"],
     ["belt noodles", "chili flakes", "garlic", "vinegar", "bok choy", "hot oil"],
     ["Pull noodles wide.", "Boil until chewy.", "Top with chili and garlic.", "Sizzle hot oil over aromatics.", "Toss and serve."]),
    ("shaanxi", "roujiamo", "Roujiamo", "Shaanxi 'burger' — cumin lamb in crisp flatbread.", 1,
     ["sandwich", "lamb", "street food"],
     ["lamb stew", "cumin", "flatbread", "cilantro", "chili"],
     ["Slow-braise lamb with cumin.", "Shred meat.", "Split and toast bread.", "Stuff with meat and herbs.", "Serve immediately."]),
    ("shaanxi", "lamb-paomo", "Lamb Paomo", "Shredded flatbread soaked in lamb broth.", 1,
     ["soup", "lamb", "comfort"],
     ["flatbread", "lamb broth", "glass noodles", "cilantro", "fermented garlic"],
     ["Tear bread into tiny pieces.", "Simmer lamb broth.", "Pour over bread to soak.", "Add noodles and meat.", "Top with cilantro and garlic."]),
]


def _fmt_ingredients(raw: list[str]) -> str:
    return ",\n".join(f'            {{"name": "{item}"}}' for item in raw)


def _fmt_steps(steps: list[str]) -> str:
    return ",\n".join(f'            "{s}"' for s in steps)


def main() -> None:
    out = Path(__file__).parent / "cuisine_expansion_v5_east_asia.py"
    chunks = [
        '"""v5 East Asia cuisine expansion — 26 cuisines × 3 recipes (78 total).',
        "",
        "Auto-generated by `generate_east_asia_expansion.py`.",
        '"""',
        "",
        "from scripts.curated_data import RecipeSpec, _img",
        "",
        "EAST_ASIA_EXPANSION_RECIPES: list[RecipeSpec] = [",
    ]
    for row in _DISHES:
        cuisine, slug, title, desc, spice, tags, ings, steps = row
        tag_str = ", ".join(f'"{t}"' for t in tags)
        chunks.append("    {")
        chunks.append(f'        "title": "{title}",')
        chunks.append(f'        "description": "{desc}",')
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
