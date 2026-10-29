"""Build Recipe + Ingredient tables from scraped Cal Dining menu items.

Run: uv run --with pandas python scripts/build_recipes.py

Inputs : data/raw/menus/menu_items.csv (rerunnable while the scrape grows)
         data/raw/reference/ingredients.csv (optional; if present, ids are aligned to it)
Outputs: data/recipes/{ingredients,recipes,recipe_ingredients,menu_item_map,
         ingredient_rules,name_rules,unmatched_components,coverage}.csv

Deterministic: no randomness; all outputs sorted.
Quantity basis: qty_per_batch is edible-portion (as-served, cooked) weight, expressed in
the ingredient's default_unit. The generator converts to as-purchased via yields.csv.
"""

from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / "data/raw/menus/menu_items.csv"
REF_ING = ROOT / "data/raw/reference/ingredients.csv"
SHELF = ROOT / "data/raw/reference/shelf_life.csv"
LOSS = ROOT / "data/raw/reference/loss_rates.csv"
OUT = ROOT / "data/recipes"

PORTIONS_PER_BATCH = 100
TOP_N = 300  # items guaranteed a specific (non-generic) recipe when any evidence exists
MAX_PORTION_OZ = 16.0  # Eatec serving sizes above this are pan/batch weights, not portions

# ---------------------------------------------------------------------------
# Canonical ingredients: id, name, category, default_unit, lb_per_unit, storage, role, notes
# role drives weight allocation: major = carries the dish, minor = fat/acid/sauce, trace = seasoning
# ---------------------------------------------------------------------------
ING = [
    # produce
    ("lettuce_romaine", "Romaine lettuce", "produce", "lb", 1, "cooler", "major", "incl. green leaf, iceberg"),
    ("greens_mixed", "Mixed greens / spring mix", "produce", "lb", 1, "cooler", "major", "incl. arugula"),
    ("spinach", "Spinach", "produce", "lb", 1, "cooler", "major", "baby + chopped"),
    ("kale_collards", "Kale / collard greens", "produce", "lb", 1, "cooler", "major", ""),
    ("cabbage", "Cabbage", "produce", "lb", 1, "cooler", "major", "green, red, napa"),
    ("greens_asian", "Bok choy / gai lan", "produce", "lb", 1, "cooler", "major", ""),
    ("cucumber", "Cucumber", "produce", "lb", 1, "cooler", "major", ""),
    ("tomato", "Tomato, fresh", "produce", "lb", 1, "cooler", "major", "roma, cherry, grape, sliced"),
    ("carrot", "Carrot", "produce", "lb", 1, "cooler", "major", "whole, shredded, baby"),
    ("onion", "Onion, dry", "produce", "lb", 1, "dry", "major", "yellow, white, red, shallot"),
    ("onion_green", "Green onion", "produce", "lb", 1, "cooler", "minor", ""),
    ("pepper_bell", "Bell pepper", "produce", "lb", 1, "cooler", "major", "red, green; diced/julienne"),
    ("pepper_chili", "Chili pepper, fresh", "produce", "lb", 1, "cooler", "minor", "jalapeno, serrano, poblano"),
    ("garlic", "Garlic, peeled", "produce", "lb", 1, "cooler", "minor", ""),
    ("ginger", "Ginger, peeled", "produce", "lb", 1, "cooler", "minor", "incl. lemongrass, galangal"),
    ("celery", "Celery", "produce", "lb", 1, "cooler", "major", ""),
    ("broccoli", "Broccoli", "produce", "lb", 1, "cooler", "major", "florets, broccolini"),
    ("cauliflower", "Cauliflower", "produce", "lb", 1, "cooler", "major", ""),
    ("squash_summer", "Zucchini / yellow squash", "produce", "lb", 1, "cooler", "major", ""),
    ("squash_winter", "Winter squash", "produce", "lb", 1, "dry", "major", "butternut, kabocha, pumpkin"),
    ("mushroom", "Mushrooms", "produce", "lb", 1, "cooler", "major", "crimini, white, shiitake, portobello"),
    ("potato", "Potato, fresh", "produce", "lb", 1, "dry", "major", "russet, yukon, red"),
    ("potato_sweet", "Sweet potato", "produce", "lb", 1, "dry", "major", ""),
    ("eggplant", "Eggplant", "produce", "lb", 1, "cooler", "major", ""),
    ("corn", "Corn kernels", "produce", "lb", 1, "freezer", "major", "IQF / flame roasted"),
    ("peas_green", "Green peas / pea-carrot blend", "produce", "lb", 1, "freezer", "major", "incl. snap peas, edamame"),
    ("beans_green", "Green beans", "produce", "lb", 1, "cooler", "major", ""),
    ("beets", "Beets", "produce", "lb", 1, "cooler", "major", ""),
    ("radish", "Radish", "produce", "lb", 1, "cooler", "major", "red, daikon"),
    ("veg_other", "Other fresh vegetables", "produce", "lb", 1, "cooler", "major", "asparagus, brussels, fennel, sprouts"),
    ("herbs_fresh", "Fresh herbs", "produce", "lb", 1, "cooler", "trace", "cilantro, parsley, basil, mint, dill"),
    ("citrus", "Lemons / limes", "produce", "each", 0.25, "cooler", "minor", ""),
    ("fruit_banana", "Banana", "produce", "each", 0.33, "dry", "major", ""),
    ("fruit_apple", "Apple", "produce", "each", 0.4, "cooler", "major", ""),
    ("fruit_orange", "Orange", "produce", "each", 0.45, "cooler", "major", ""),
    ("fruit_melon", "Melon", "produce", "lb", 1, "cooler", "major", "cantaloupe, honeydew, watermelon"),
    ("fruit_berries", "Berries", "produce", "lb", 1, "cooler", "major", "fresh or IQF"),
    ("fruit_pineapple", "Pineapple", "produce", "lb", 1, "cooler", "major", "fresh or IQF chunks"),
    ("fruit_other", "Other fruit", "produce", "lb", 1, "cooler", "major", "grapes, mango, pear, peach"),
    ("avocado", "Avocado", "produce", "lb", 1, "cooler", "major", "incl. guacamole"),
    ("fruit_dried", "Dried fruit", "produce", "lb", 1, "dry", "major", "raisins, cranberries, apricots, coconut flake"),
    # dairy
    ("milk", "Milk, dairy", "dairy", "gal", 8.6, "cooler", "major", "whole, 2%, nonfat"),
    ("cream", "Cream / half-and-half", "dairy", "gal", 8.4, "cooler", "minor", ""),
    ("butter", "Butter", "dairy", "lb", 1, "cooler", "minor", ""),
    ("butter_substitute", "Plant butter spread", "dairy", "lb", 1, "cooler", "minor", "Smart Balance, vegan butter"),
    ("cheese_shredded_sliced", "Cheese, cheddar/jack/american/provolone", "dairy", "lb", 1, "cooler", "major", ""),
    ("cheese_mozzarella", "Mozzarella / pizza cheese", "dairy", "lb", 1, "cooler", "major", ""),
    ("cheese_parmesan", "Parmesan", "dairy", "lb", 1, "cooler", "minor", ""),
    ("cheese_crumbled", "Feta / blue / cotija", "dairy", "lb", 1, "cooler", "major", ""),
    ("cheese_vegan", "Plant-based cheese", "dairy", "lb", 1, "cooler", "major", "Daiya etc."),
    ("cream_cheese", "Cream cheese", "dairy", "lb", 1, "cooler", "major", ""),
    ("yogurt", "Yogurt", "dairy", "lb", 1, "cooler", "major", "Greek and regular"),
    ("sour_cream", "Sour cream", "dairy", "lb", 1, "cooler", "minor", ""),
    ("soft_serve_mix", "Soft serve mix", "dairy", "gal", 9.0, "cooler", "major", "dairy and vegan"),
    # protein
    ("chicken_raw", "Chicken, raw", "protein", "lb", 1, "cooler", "major", "breast, thigh, 8-cut"),
    ("chicken_cooked", "Chicken, precooked", "protein", "lb", 1, "freezer", "major", "diced, breaded tenders"),
    ("turkey", "Turkey", "protein", "lb", 1, "cooler", "major", "deli, ground, sausage"),
    ("beef_ground", "Ground beef", "protein", "lb", 1, "cooler", "major", "incl. patties, meatballs"),
    ("beef_whole", "Beef, whole-muscle", "protein", "lb", 1, "cooler", "major", "tri tip, stew, sirloin, stir fry"),
    ("pork", "Pork", "protein", "lb", 1, "cooler", "major", "loin, butt, stew, ham"),
    ("sausage_bacon", "Sausage / bacon", "protein", "lb", 1, "freezer", "major", "pork sausage, bacon bits"),
    ("fish", "Fish fillet", "protein", "lb", 1, "freezer", "major", "salmon, cod, rockfish, pollock"),
    ("shrimp", "Shrimp", "protein", "lb", 1, "freezer", "major", ""),
    ("tuna_canned", "Tuna, canned/pouch", "protein", "lb", 1, "dry", "major", ""),
    ("eggs", "Eggs", "protein", "lb", 1, "cooler", "major", "liquid, shell, hard-boiled (8.6 lb/gal liquid)"),
    ("egg_alt", "Plant egg", "protein", "lb", 1, "cooler", "major", "JUST Egg"),
    ("tofu", "Tofu", "protein", "lb", 1, "cooler", "major", ""),
    ("meat_alt", "Plant-based meat", "protein", "lb", 1, "freezer", "major", "Beyond, Gardein, soyrizo"),
    ("beans_canned", "Beans, canned", "protein", "lb", 1, "dry", "major", "garbanzo, black, kidney, pinto, white"),
    ("legumes_dried", "Lentils / dried beans", "protein", "lb", 1, "dry", "major", "cooked weight basis"),
    ("nuts_seeds", "Nuts and seeds", "protein", "lb", 1, "dry", "major", "almond, pumpkin, sunflower"),
    # grain
    ("rice_white", "Rice, white", "grain", "lb", 1, "dry", "major", "jasmine, basmati, long grain, arborio; cooked basis"),
    ("rice_brown", "Rice, brown", "grain", "lb", 1, "dry", "major", "cooked basis"),
    ("pasta", "Pasta, dry", "grain", "lb", 1, "dry", "major", "penne, spaghetti, fettuccine, macaroni; cooked basis"),
    ("pasta_gf", "Pasta, gluten-free", "grain", "lb", 1, "dry", "major", "cooked basis"),
    ("noodles_asian", "Rice / egg noodles", "grain", "lb", 1, "dry", "major", "cooked basis"),
    ("oats", "Oats", "grain", "lb", 1, "dry", "major", "cooked basis"),
    ("grains_other", "Quinoa / farro / bulgur / couscous", "grain", "lb", 1, "dry", "major", "cooked basis"),
    ("flour", "Flour", "grain", "lb", 1, "dry", "minor", "AP, bread, GF"),
    ("cornmeal", "Cornmeal / polenta / masa", "grain", "lb", 1, "dry", "major", "cooked basis"),
    ("pancake_mix", "Pancake / waffle mix", "grain", "lb", 1, "dry", "major", ""),
    ("cereal_cold", "Cold cereal / granola", "grain", "lb", 1, "dry", "major", ""),
    # bakery
    ("bread_sliced", "Bread, sliced loaf", "bakery", "lb", 1, "dry", "major", ""),
    ("bread_roll", "Rolls / buns / baguette", "bakery", "lb", 1, "dry", "major", "incl. naan, biscuit"),
    ("bagel", "Bagel", "bakery", "each", 0.25, "dry", "major", ""),
    ("tortilla", "Tortilla", "bakery", "lb", 1, "dry", "major", "corn and flour"),
    ("pastry", "Pastry", "bakery", "lb", 1, "freezer", "major", "danish, muffin, croissant"),
    ("pizza_base", "Pizza base, frozen", "bakery", "lb", 1, "freezer", "major", "dough, crusts, and pre-topped 16 in cheese pizza blanks"),
    ("croutons_crumbs", "Croutons / panko / crumbs", "bakery", "lb", 1, "dry", "major", ""),
    # prepared
    ("tomato_canned", "Tomato, canned/sauce", "prepared", "lb", 1, "dry", "major", "crushed, diced, paste, marinara"),
    ("sauce_prepared", "Prepared sauce", "prepared", "lb", 1, "cooler", "minor", "alfredo, pesto, BBQ, curry paste, teriyaki"),
    ("soup_base", "Soup base / stock concentrate", "prepared", "lb", 1, "dry", "trace", "reconstitute with water"),
    ("coconut_milk", "Coconut milk, canned", "prepared", "lb", 1, "dry", "minor", ""),
    ("hummus_dips", "Hummus / dips", "prepared", "lb", 1, "cooler", "major", ""),
    ("salsa", "Salsa / pico", "prepared", "lb", 1, "cooler", "minor", ""),
    ("potato_frozen", "Frozen potato products", "prepared", "lb", 1, "freezer", "major", "fries, hash browns, wedges, chips"),
    ("soup_prepared", "Prepared soup, frozen/bulk", "prepared", "lb", 1, "freezer", "major", "purchased ready-to-heat soups and chowders"),
    ("prepared_entree", "Prepared entree component", "prepared", "lb", 1, "freezer", "major", "mac & cheese bulk, spring rolls, dumplings"),
    ("dessert_prepared", "Prepared dessert / cookie dough", "prepared", "lb", 1, "freezer", "major", ""),
    ("pickles_olives", "Pickles / olives / capers", "prepared", "lb", 1, "dry", "minor", "incl. canned artichoke"),
    # condiment
    ("oil_cooking", "Oil, cooking blend / canola", "condiment", "gal", 7.6, "dry", "minor", "incl. spray"),
    ("oil_olive", "Olive oil", "condiment", "gal", 7.6, "dry", "minor", ""),
    ("oil_fryer", "Fryer oil", "condiment", "gal", 7.6, "dry", "minor", "absorbed share only"),
    ("oil_sesame", "Sesame oil", "condiment", "gal", 7.6, "dry", "trace", ""),
    ("salt", "Salt", "condiment", "lb", 1, "dry", "trace", ""),
    ("spices", "Dried spices and herbs", "condiment", "lb", 1, "dry", "trace", "all ground/whole spices + blends"),
    ("sugar", "Sugar", "condiment", "lb", 1, "dry", "minor", "white, brown, powdered"),
    ("syrup_honey", "Honey / syrups", "condiment", "lb", 1, "dry", "minor", "maple, molasses, agave"),
    ("vinegar", "Vinegar", "condiment", "gal", 8.4, "dry", "minor", ""),
    ("soy_sauce", "Soy / fish / seasoning sauce", "condiment", "gal", 9.6, "dry", "minor", ""),
    ("dressing", "Salad dressing", "condiment", "gal", 8.0, "cooler", "minor", "ranch, caesar, vinaigrettes"),
    ("mayonnaise", "Mayonnaise", "condiment", "lb", 1, "cooler", "minor", "dairy and vegan"),
    ("mustard_ketchup", "Mustard / ketchup / relish", "condiment", "lb", 1, "dry", "minor", ""),
    ("hot_sauce", "Hot sauce / chili sauce", "condiment", "lb", 1, "dry", "minor", "sriracha, chipotle in adobo"),
    ("jam_spreads", "Jam / nut butter", "condiment", "lb", 1, "dry", "major", "jelly, preserves, peanut butter"),
    ("baking_staples", "Baking staples", "condiment", "lb", 1, "dry", "trace", "cornstarch, yeast, leavening, vanilla, gums"),
    ("wine_cooking", "Cooking wine", "condiment", "gal", 8.3, "dry", "minor", ""),
    # beverage
    ("juice", "Juice", "beverage", "gal", 8.7, "cooler", "minor", "orange, lemon, lime, apple"),
    ("milk_plant", "Plant milk", "beverage", "gal", 8.6, "cooler", "major", "oat, soy, almond"),
    ("coffee_tea", "Coffee / tea", "beverage", "lb", 1, "dry", "major", ""),
    # fallback
    ("misc_dry", "Other dry goods", "prepared", "lb", 1, "dry", "minor", "unmatched component bucket"),
]

# ---------------------------------------------------------------------------
# Crosswalk to research tables (free-text keys there). "~" prefix = proxy, not exact.
# id: (shelf_life.csv `ingredient`, loss_rates.csv `commodity`)
# ---------------------------------------------------------------------------
REF_XWALK: dict[str, tuple[str, str]] = {
    "lettuce_romaine": ("romaine lettuce", "Fresh leaf lettuce"),
    "greens_mixed": ("~romaine lettuce", "~Fresh leaf lettuce"),
    "spinach": ("spinach, fresh", "Fresh spinach"),
    "kale_collards": ("~spinach, fresh", "Fresh kale"),
    "cabbage": ("cabbage, green", "Fresh cabbage"),
    "greens_asian": ("~spinach, fresh", "~Fresh cabbage"),
    "cucumber": ("cucumbers", "Fresh cucumbers"),
    "tomato": ("tomatoes, fresh", "Fresh tomatoes"),
    "carrot": ("carrots", "Fresh carrots"),
    "onion": ("onions, yellow", "Fresh onions"),
    "onion_green": ("~onions, yellow", "~Fresh onions"),
    "pepper_bell": ("bell peppers", "Fresh bell peppers"),
    "pepper_chili": ("~bell peppers", "~Fresh bell peppers"),
    "garlic": ("", "Fresh garlic"),
    "ginger": ("", "~Fresh garlic"),
    "celery": ("", "Fresh celery"),
    "broccoli": ("broccoli", "Fresh broccoli"),
    "cauliflower": ("~broccoli", "Fresh cauliflower"),
    "squash_summer": ("zucchini", "Fresh squash"),
    "squash_winter": ("", "Fresh pumpkin"),
    "mushroom": ("mushrooms, white", "Fresh mushrooms"),
    "potato": ("potatoes, russet", "Fresh potatoes"),
    "potato_sweet": ("sweet potatoes", "Fresh sweet potatoes"),
    "eggplant": ("", "Fresh eggplant"),
    "corn": ("", "Frozen sweet corn"),
    "peas_green": ("", "Frozen green peas"),
    "beans_green": ("", "Fresh snap beans"),
    "beets": ("", "~Fresh vegetables"),
    "radish": ("", "Fresh radishes"),
    "veg_other": ("", "Fresh vegetables"),
    "herbs_fresh": ("", "~Fresh vegetables"),
    "citrus": ("", "Fresh lemons"),
    "fruit_banana": ("bananas", "Fresh bananas"),
    "fruit_apple": ("apples", "Fresh apples"),
    "fruit_orange": ("oranges", "Fresh oranges"),
    "fruit_melon": ("~cut fruit", "Fresh cantaloupe"),
    "fruit_berries": ("strawberries", "Fresh strawberries"),
    "fruit_pineapple": ("~cut fruit", "Fresh pineapple"),
    "fruit_other": ("~cut fruit", "Fresh noncitrus"),
    "avocado": ("avocados", "Fresh avocados"),
    "fruit_dried": ("", "Dried fruit"),
    "milk": ("milk, 2%", "2 percent milk"),
    "cream": ("", "Heavy cream"),
    "butter": ("butter", "Butter"),
    "butter_substitute": ("~butter", "Margarine"),
    "cheese_shredded_sliced": ("cheddar cheese, shredded", "Cheddar cheese"),
    "cheese_mozzarella": ("mozzarella, shredded", "Mozzarella cheese"),
    "cheese_parmesan": ("", "Parmesan cheese"),
    "cheese_crumbled": ("", "Blue cheese"),
    "cheese_vegan": ("~mozzarella, shredded", "~Total cheese"),
    "cream_cheese": ("", "Cream cheese"),
    "yogurt": ("yogurt, plain low-fat", "Yogurt"),
    "sour_cream": ("", "Sour cream"),
    "soft_serve_mix": ("", "Frozen dairy products"),
    "chicken_raw": ("chicken thigh, boneless skinless", "Chicken"),
    "chicken_cooked": ("cooked poultry dishes", "Chicken"),
    "turkey": ("", "Turkey"),
    "beef_ground": ("ground beef 80/20", "Beef"),
    "beef_whole": ("", "Beef"),
    "pork": ("pork shoulder, boneless", "Pork"),
    "sausage_bacon": ("", "Pork"),
    "fish": ("salmon fillet", "Fresh and frozen fish"),
    "shrimp": ("", "Fresh and frozen shellfish"),
    "tuna_canned": ("", "Canned Tuna"),
    "eggs": ("eggs, shell, large", "Eggs"),
    "egg_alt": ("", ""),
    "tofu": ("tofu, firm", ""),
    "meat_alt": ("", ""),
    "beans_canned": ("chickpeas, canned", "~Dry edible beans"),
    "legumes_dried": ("lentils, dry", "Dry peas and lentils"),
    "nuts_seeds": ("", "Total tree nuts"),
    "rice_white": ("white rice, long grain", "Rice"),
    "rice_brown": ("brown rice, long grain", "Rice"),
    "pasta": ("pasta, dry (spaghetti/penne)", "Durum flour"),
    "pasta_gf": ("~pasta, dry (spaghetti/penne)", "~Rice"),
    "noodles_asian": ("~pasta, dry (spaghetti/penne)", "~Rice"),
    "oats": ("rolled oats", "Oat products"),
    "grains_other": ("quinoa", "~Total grains"),
    "flour": ("", "White and whole wheat flour"),
    "cornmeal": ("", "Corn flour and meal"),
    "pancake_mix": ("", "~Wheat flour"),
    "cereal_cold": ("", "~Total grains"),
    "bread_sliced": ("sandwich bread, sliced", "~Wheat flour"),
    "bread_roll": ("~sandwich bread, sliced", "~Wheat flour"),
    "bagel": ("~sandwich bread, sliced", "~Wheat flour"),
    "tortilla": ("flour tortillas", "~Wheat flour"),
    "pastry": ("", "~Wheat flour"),
    "pizza_base": ("~leftover pizza", "~Wheat flour"),
    "croutons_crumbs": ("", "~Wheat flour"),
    "tomato_canned": ("", "Canned tomatoes"),
    "sauce_prepared": ("", ""),
    "soup_base": ("", ""),
    "coconut_milk": ("", "Coconut"),
    "hummus_dips": ("~guacamole", "~Dry edible beans"),
    "salsa": ("~guacamole", "~Canned tomatoes"),
    "potato_frozen": ("", "Frozen potatoes"),
    "soup_prepared": ("~soups and stews", ""),
    "prepared_entree": ("main dishes or meals (hot or refrigerated)", ""),
    "dessert_prepared": ("", ""),
    "pickles_olives": ("", "Canned olives"),
    "oil_cooking": ("", "Salad and cooking oils"),
    "oil_olive": ("", "Salad and cooking oils"),
    "oil_fryer": ("", "Salad and cooking oils"),
    "oil_sesame": ("", "Salad and cooking oils"),
    "salt": ("", ""),
    "spices": ("", ""),
    "sugar": ("", ""),
    "syrup_honey": ("", ""),
    "vinegar": ("", ""),
    "soy_sauce": ("", ""),
    "dressing": ("", "~Salad and cooking oils"),
    "mayonnaise": ("", "~Salad and cooking oils"),
    "mustard_ketchup": ("", ""),
    "hot_sauce": ("", ""),
    "jam_spreads": ("", ""),
    "baking_staples": ("", "Corn starch"),
    "wine_cooking": ("", ""),
    "juice": ("", "Orange juice"),
    "milk_plant": ("", ""),
    "coffee_tea": ("", ""),
    "misc_dry": ("", ""),
}

ING_COLS = ["id", "name", "category", "default_unit", "lb_per_unit", "storage", "role", "notes"]
ROLE = {r[0]: r[6] for r in ING}
LB_PER_UNIT = {r[0]: r[4] for r in ING}
UNIT = {r[0]: r[3] for r in ING}

# ---------------------------------------------------------------------------
# Component -> canonical ingredient rules. First match wins; order matters.
# ---------------------------------------------------------------------------
SKIP = re.compile(r"^(water|ice|water ice|n/f .*|mono- and diglycerides|whey|natural and artificial flavors?|soy lecithin|natural flavor)$", re.I)
RULES: list[tuple[str, str]] = [
    (r"^soup (?!base)", "soup_prepared"),
    (r"\baloo\b|palak|paneer|pakora|\bbao\b|beignet|kachumber|macaroni and cheese|mac and cheese", "prepared_entree"),
    (r"meat alternative|beyond|impossible|gardein|soyrizo|veggie strip|land lover|plant.based", "meat_alt"),
    # Why: "Pizza Cheese 16 In" is a whole frozen cheese pizza (crust+sauce+cheese), not mozzarella.
    (r"pizza cheese \d|pizza (dough|crust|shell)|dough pizza|flatbread", "pizza_base"),
    (r"cheesecake|\bcake\b|\bpie\b|brownie|cookie|tart\b|pudding", "dessert_prepared"),
    (r"donut|danish|croissant|muffin|cinnamon roll|scone", "pastry"),
    (r"crouton|panko|bread ?crumb", "croutons_crumbs"),
    (r"granola|cereal", "cereal_cold"),
    (r"sunflower butter|butter sunflower|sunbutter|peanut butter|almond butter", "jam_spreads"),
    (r"coconut (creme|cream)", "coconut_milk"),
    (r"creamer oat|oat ?milk|milk (oat|soy|almond)", "milk_plant"),
    (r"^juice|juice (lemon|lime|orange|apple|pineapple|cranberry)", "juice"),
    (r"chicken .*with sauce", "chicken_cooked"),
    (r"vinegar", "vinegar"),
    (r"^yeast|yeast nutritional|baking (powder|soda)", "baking_staples"),
    (r"sauce (soy|fish|seasoning|oyster|tamari)|soy sauce|tamari|golden mountain|fish sauce|liquid aminos|worcestershire", "soy_sauce"),
    (r"chipotle|sriracha|sauce hot|hot sauce|sambal|chili garlic|sweet chili|gochujang|sauce buffalo|harissa", "hot_sauce"),
    (r"^sauce (?!.*(marinara|tomato|cheese vegan))", "sauce_prepared"),
    (r"molasses|syrup|\bhoney\b|agave", "syrup_honey"),
    (r"pineapple", "fruit_pineapple"),
    (r"peanut butter|jelly|jam\b|preserves|nutella|sunbutter", "jam_spreads"),
    (r"tortilla|taco shell|tostada", "tortilla"),
    (r"spring roll|egg roll|summer roll", "prepared_entree"),
    (r"cinnamon roll|danish|croissant|muffin", "pastry"),
    (r"bread.*slice|slice.*bread|bread white|bread wheat|texas toast|toast french|french toast", "bread_sliced"),
    (r"chicken.*(precooked|cooked|breaded|tempura|nugget|tender)|chicken diced meat", "chicken_cooked"),
    (r"biscuit|\bbread\b|baguette|\bbun\b|\broll\b|naan|pita", "bread_roll"),
    (r"beans? green|green beans?|haricot", "beans_green"),
    (r"black eye|lentil|beans? white dried|beans mung|split pea", "legumes_dried"),
    (r"^water\b.*\b(base|concentrate|bouillon)", "soup_base"),
    (r"\b(base|bouillon|stock|broth)\b.*(concentrate|vegetable|chicken|beef|no msg)|soup base|^base ", "soup_base"),
    (r"just egg|egg.*vegan|vegan.*egg", "egg_alt"),
    (r"meat alternative|beyond|impossible|gardein|soyrizo|veggie strip|land lover|vegan.*(sausage|chicken|beef)|plant.based", "meat_alt"),
    (r"cheese alternative|vegan.*cheese|cheese.*vegan|daiya|sauce cheese vegan", "cheese_vegan"),
    (r"butter substitute|smart balance|vegan butter|butter.*vegan|earth balance|margarine", "butter_substitute"),
    (r"mayonnaise|\bmayo\b|aioli", "mayonnaise"),
    (r"^dressing|vinaigrette|dressing\b", "dressing"),
    (r"oil.*olive|olive oil", "oil_olive"),
    (r"oil fryer|fryer", "oil_fryer"),
    (r"oil sesame|sesame oil", "oil_sesame"),
    (r"^oil\b|\boil (cooking|canola|spray|vegetable|salad)|canola|oil spray", "oil_cooking"),
    (r"spice salt|^salt\b|kosher salt|sea salt", "salt"),
    (r"^spice|seasoning (?!sauce)|spice blend|^herb.*dried|saffron|paprika|cumin|cinnamon|nutmeg|oregano ground", "spices"),
    (r"sesame seed|poppy seed|chia|flax", "spices"),
    (r"juice (lemon|lime|orange|apple|pineapple|cranberry)|^juice|lemonade", "juice"),
    (r"^herb (cilantro|parsley|basil|mint|dill|chives|thyme|rosemary|sage|oregano)|^herb|cilantro|parsley|basil|\bmint\b|\bdill\b|chives", "herbs_fresh"),
    (r"lemongrass|galangal|^ginger|ginger peeled|ginger root", "ginger"),
    (r"garlic", "garlic"),
    (r"onion green|green onion|scallion", "onion_green"),
    (r"onion|shallot|leek", "onion"),
    (r"chipotle|sriracha|sauce hot|hot sauce|sambal|chili sauce|sweet chili|gochujang|sauce buffalo", "hot_sauce"),
    (r"pepper bell|bell pepper|pepper.*roasted red|pimento", "pepper_bell"),
    (r"jalapeno|serrano|poblano|pepper (chili|guajillo|ancho|thai|habanero|anaheim)|chile", "pepper_chili"),
    (r"potato (fries|hashbrown|wedge|chip|breakfast cubes|tots)|fries|hash ?brown|tater", "potato_frozen"),
    (r"potato sweet|sweet potato|yam", "potato_sweet"),
    (r"potato", "potato"),
    (r"tomato (crushed|diced canned|paste|puree|sauce)|paste tomato|sauce tomato|marinara|tomato.*canned|tomato sundried", "tomato_canned"),
    (r"tomato|tomatillo", "tomato"),
    (r"salsa|pico de gallo", "salsa"),
    (r"lettuce|romaine|iceberg", "lettuce_romaine"),
    (r"mixed greens|spring mix|arugula|mesclun|greens mix", "greens_mixed"),
    (r"spinach", "spinach"),
    (r"kale|collard|chard|mustard greens", "kale_collards"),
    (r"bok choy|gai lan|chinese broccoli|yu choy", "greens_asian"),
    (r"cabbage|slaw", "cabbage"),
    (r"cucumber", "cucumber"),
    (r"carrot", "carrot"),
    (r"celery", "celery"),
    (r"broccoli|broccolini", "broccoli"),
    (r"cauliflower", "cauliflower"),
    (r"squash (zucchini|yellow)|zucchini|yellow squash", "squash_summer"),
    (r"squash|pumpkin(?! seed)|kabocha", "squash_winter"),
    (r"mushroom", "mushroom"),
    (r"eggplant", "eggplant"),
    (r"\bcorn\b(?! ?starch| syrup| tortilla|meal| masa| flour| chip)|hominy", "corn"),
    (r"pea green|green pea|sugar snap|snap pea|edamame|vegetable blend|peas? carrot|\bpeas?\b", "peas_green"),
    (r"beans? green|green beans?|haricot", "beans_green"),
    (r"beet", "beets"),
    (r"radish|daikon", "radish"),
    (r"asparagus|brussels|fennel|sprouts|artichoke fresh|okra|jicama|vegetable", "veg_other"),
    (r"artichoke|olive|pickle|caper|relish|jalapeno rings|giardiniera|kimchi", "pickles_olives"),
    (r"lemon|lime", "citrus"),
    (r"banana", "fruit_banana"),
    (r"apple(?! cider)", "fruit_apple"),
    (r"orange(?! juice)|mandarin|clementine", "fruit_orange"),
    (r"melon|cantaloupe|honeydew", "fruit_melon"),
    (r"pineapple", "fruit_pineapple"),
    (r"avocado|guacamole", "avocado"),
    (r"raisin|cranberr|apricot dried|dried|date|coconut flake", "fruit_dried"),
    (r"berr(y|ies)", "fruit_berries"),
    (r"grape|mango|pear|peach|kiwi|plum|fruit", "fruit_other"),
    (r"soft serve|ice cream|frozen yogurt|sorbet", "soft_serve_mix"),
    (r"cream cheese", "cream_cheese"),
    (r"sour cream", "sour_cream"),
    (r"yogurt", "yogurt"),
    (r"milk coconut|coconut milk|coconut cream", "coconut_milk"),
    (r"milk (oat|soy|almond)|oat ?milk|soy ?milk|almond ?milk", "milk_plant"),
    (r"cream heavy|heavy cream|half and half|creamer|whipping|whipped topping", "cream"),
    (r"butter(?!milk)", "butter"),
    (r"mozzarella|pizza cheese|cheese pizza", "cheese_mozzarella"),
    (r"parmesan|romano|asiago", "cheese_parmesan"),
    (r"feta|blue crumbles|cheese blue|cotija|goat cheese|queso fresco", "cheese_crumbled"),
    (r"cheese", "cheese_shredded_sliced"),
    (r"milk|buttermilk", "milk"),
    (r"egg", "eggs"),
    (r"tofu", "tofu"),
    (r"chicken.*(precooked|cooked|breaded|tempura|nugget|tender)|chicken diced meat", "chicken_cooked"),
    (r"chicken", "chicken_raw"),
    (r"turkey", "turkey"),
    (r"sausage|bacon|chorizo|pepperoni|hot dog|salami", "sausage_bacon"),
    (r"beef ground|ground beef|beef patty|meatball|hamburger|burger patty", "beef_ground"),
    (r"beef|steak", "beef_whole"),
    (r"pork|ham\b|carnitas", "pork"),
    (r"tuna", "tuna_canned"),
    (r"shrimp|prawn", "shrimp"),
    (r"salmon|cod|rockfish|pollock|tilapia|fish(?! sauce)|catfish|swai|halibut", "fish"),
    (r"hummus|baba|tzatziki|tahini|dip\b", "hummus_dips"),
    (r"beans?.*canned|garbanzo|chickpea|bean (black|kidney|pinto|cannellini|white)|beans (black|kidney|pinto|white)|refried", "beans_canned"),
    (r"lentil|beans? .*dried|black eye|mung|split pea|dal", "legumes_dried"),
    (r"lamb|goat meat|veal", "beef_whole"),
    (r"clam|lobster|scallop|crab|mussel", "shrimp"),
    (r"parsnip|turnip|yucca|cassava|plantain|alfalfa|taro", "veg_other"),
    (r"pepperoncini|sauerkraut", "pickles_olives"),
    (r"pepper (pasilla|calabrian|scotch|cherry|piquante|red roasted)", "pepper_chili"),
    (r"harissa", "hot_sauce"),
    (r"cream of wheat|malt o meal|freekeh", "grains_other"),
    (r"annato|annatto|ancho powder|fenugreek", "spices"),
    (r"whipped cream", "cream"),
    (r"pomegranate", "fruit_other"),
    (r"almond|walnut|pecan|cashew|peanut(?! butter)|pumpkin seed|sunflower seed|pepita|pistachio|nut", "nuts_seeds"),
    (r"peanut butter|jelly|jam|preserves|nutella|sunbutter", "jam_spreads"),
    (r"rice brown|brown rice", "rice_brown"),
    (r"noodle|ramen|udon|soba|vermicelli", "noodles_asian"),
    (r"rice", "rice_white"),
    (r"pasta.*(gf|gluten)|gluten free.*pasta", "pasta_gf"),
    (r"pasta|penne|spaghetti|fettuccine|macaroni|rotini|linguine|lasagna|orzo|gnocchi|tortellini|ravioli", "pasta"),
    (r"oat", "oats"),
    (r"quinoa|farro|bulgur|couscous|barley|millet", "grains_other"),
    (r"polenta|cornmeal|masa|grits", "cornmeal"),
    (r"pancake|waffle|french toast", "pancake_mix"),
    (r"cereal|granola|cheerios|flakes", "cereal_cold"),
    (r"panko|crouton|bread ?crumb|crumbs", "croutons_crumbs"),
    (r"bagel", "bagel"),
    (r"tortilla|taco shell|tostada|chip tortilla", "tortilla"),
    (r"pizza (dough|crust)|dough pizza|flatbread", "pizza_base"),
    (r"danish|muffin|croissant|scone|pastry|donut|cinnamon roll", "pastry"),
    (r"bread (white|wheat|sourdough|rye|multigrain).*sliced|bread .*slice|bread sliced|texas toast|bread white", "bread_sliced"),
    (r"bread|roll|bun|baguette|naan|pita|biscuit|ciabatta|focaccia|hoagie|croissant", "bread_roll"),
    (r"flour", "flour"),
    (r"cookie|cake|brownie|pie|cheesecake|pudding|dessert|frosting|icing|chocolate chip|chocolate", "dessert_prepared"),
    (r"macaroni and cheese|mac and cheese|spring roll|egg roll|dumpling|potsticker|samosa|empanada|falafel", "prepared_entree"),
    (r"sauce (soy|fish|seasoning|oyster|tamari)|soy sauce|tamari|golden mountain|fish sauce|liquid aminos|worcestershire", "soy_sauce"),
    (r"vinegar", "vinegar"),
    (r"mustard|ketchup|catsup", "mustard_ketchup"),
    (r"sugar|sweetener", "sugar"),
    (r"honey|syrup|molasses|agave", "syrup_honey"),
    (r"wine|sherry|mirin|sake", "wine_cooking"),
    (r"cornstarch|starch|yeast|baking (powder|soda)|extract|vanilla|xanthan|gelatin|agar|cocoa|leaven", "baking_staples"),
    (r"paste (curry|miso|achiote|chili)|curry paste|miso|achiote|^sauce|sauce\b|pesto|gravy|glaze|teriyaki|hoisin|bbq|alfredo|vindaloo|mole", "sauce_prepared"),
    (r"coffee|tea\b|espresso", "coffee_tea"),
]
RULES_C = [(re.compile(p, re.I), i) for p, i in RULES]

# ---------------------------------------------------------------------------
# Name rules for items with no ingredient list anywhere. Shares are of batch weight.
# ---------------------------------------------------------------------------
NAME_RULES: list[tuple[str, list[tuple[str, float]]]] = [
    (r"pizza", [("pizza_base", 0.5), ("cheese_mozzarella", 0.3), ("tomato_canned", 0.2)]),
    (r"hot links?", [("sausage_bacon", 0.97), ("oil_cooking", 0.03)]),
    (r"caldo de pollo|chicken soup", [("chicken_raw", 0.3), ("potato", 0.15), ("carrot", 0.15), ("corn", 0.1), ("squash_summer", 0.1), ("onion", 0.08), ("celery", 0.06), ("soup_base", 0.04), ("herbs_fresh", 0.02)]),
    (r"tamale", [("cornmeal", 0.55), ("chicken_raw", 0.2), ("salsa", 0.12), ("oil_cooking", 0.1), ("spices", 0.03)]),
    (r"risotto", [("rice_white", 0.6), ("mushroom", 0.2), ("cheese_parmesan", 0.06), ("butter", 0.05), ("onion", 0.05), ("soup_base", 0.02), ("wine_cooking", 0.02)]),
    (r"ratatouille", [("eggplant", 0.3), ("squash_summer", 0.3), ("tomato", 0.2), ("pepper_bell", 0.1), ("onion", 0.06), ("oil_olive", 0.03), ("herbs_fresh", 0.01)]),
    (r"brussels", [("veg_other", 0.93), ("vinegar", 0.03), ("oil_olive", 0.03), ("salt", 0.01)]),
    (r"taco|burrito|quesadilla", [("tortilla", 0.3), ("chicken_raw", 0.35), ("salsa", 0.1), ("cabbage", 0.1), ("cheese_shredded_sliced", 0.08), ("onion", 0.04), ("spices", 0.03)]),
    (r"salsa|tomatillo", [("tomato", 0.6), ("onion", 0.15), ("pepper_chili", 0.1), ("herbs_fresh", 0.05), ("citrus", 0.05), ("salt", 0.05)]),
    (r"mockjito|lemonade|agua fresca|juice", [("juice", 0.85), ("sugar", 0.1), ("herbs_fresh", 0.05)]),
    (r"^(mint|cilantro|parsley|basil|chives?)$", [("herbs_fresh", 1.0)]),
    (r"black bean burger|veggie burger", [("beans_canned", 0.45), ("bread_roll", 0.35), ("grains_other", 0.1), ("onion", 0.05), ("oil_cooking", 0.03), ("spices", 0.02)]),
    (r"hot dog", [("sausage_bacon", 0.55), ("bread_roll", 0.35), ("pickles_olives", 0.04), ("tomato", 0.03), ("mustard_ketchup", 0.03)]),
    (r"tri tip|lamb", [("beef_whole", 0.9), ("onion", 0.04), ("oil_cooking", 0.03), ("spices", 0.02), ("salt", 0.01)]),
    (r"fries|tots|tator|tater", [("potato_frozen", 0.96), ("oil_fryer", 0.03), ("salt", 0.01)]),
    (r"blintz", [("pancake_mix", 0.45), ("cream_cheese", 0.3), ("fruit_berries", 0.2), ("sugar", 0.05)]),
    (r"couscous", [("grains_other", 0.92), ("onion", 0.03), ("oil_olive", 0.03), ("spices", 0.02)]),
    (r"dressing|vinaigrette", [("dressing", 1.0)]),
    (r"dried cranberr|raisin", [("fruit_dried", 1.0)]),
    (r"pickling brine", [("vinegar", 0.6), ("sugar", 0.3), ("salt", 0.1)]),
    (r"romesco", [("pepper_bell", 0.5), ("nuts_seeds", 0.25), ("oil_olive", 0.15), ("tomato", 0.1)]),
    (r"pho broth|broth", [("onion", 0.35), ("ginger", 0.15), ("soy_sauce", 0.2), ("soup_base", 0.15), ("spices", 0.1), ("sugar", 0.05)]),
    (r"cauliflower", [("cauliflower", 0.95), ("oil_cooking", 0.03), ("spices", 0.02)]),
    (r"gai ?lan|gailon|bok choy", [("greens_asian", 0.94), ("garlic", 0.03), ("oil_cooking", 0.03)]),
    (r"asparagus|brussel", [("veg_other", 0.92), ("oil_olive", 0.03), ("cheese_parmesan", 0.04), ("salt", 0.01)]),
    (r"bagel", [("bagel", 1.0)]),
    (r"yogurt", [("yogurt", 1.0)]),
    (r"oatmeal|porridge", [("oats", 0.95), ("sugar", 0.03), ("salt", 0.02)]),
    (r"waffle|pancake|french toast", [("pancake_mix", 0.8), ("milk", 0.1), ("eggs", 0.07), ("oil_cooking", 0.03)]),
    (r"tofu.*scramble|scramble.*tofu", [("tofu", 0.65), ("spinach", 0.15), ("tomato", 0.12), ("oil_cooking", 0.04), ("spices", 0.04)]),
    (r"scramble|scrambled|omelet|frittata", [("eggs", 0.86), ("butter", 0.04), ("onion", 0.04), ("pepper_bell", 0.04), ("salt", 0.01), ("spices", 0.01)]),
    (r"vegan.*sausage|sausage.*vegan|mung bean patty", [("meat_alt", 0.97), ("oil_cooking", 0.03)]),
    (r"sausage|bacon", [("sausage_bacon", 0.97), ("oil_cooking", 0.03)]),
    (r"danish|muffin|croissant|scone|pastr", [("pastry", 1.0)]),
    (r"cookie|cake|pie|brownie|cobbler|bar\b|crisp", [("dessert_prepared", 1.0)]),
    (r"chili", [("beans_canned", 0.38), ("tomato_canned", 0.25), ("turkey", 0.2), ("onion", 0.08), ("pepper_bell", 0.06), ("spices", 0.02), ("oil_cooking", 0.01)]),
    (r"\b(soup|stew|bisque|chowder|caldo)\b", [("veg_other", 0.25), ("potato", 0.2), ("carrot", 0.15), ("onion", 0.12), ("celery", 0.1), ("beans_canned", 0.1), ("soup_base", 0.05), ("spices", 0.02), ("oil_cooking", 0.01)]),
    (r"beans? and rice|rice and beans", [("rice_white", 0.5), ("beans_canned", 0.38), ("onion", 0.06), ("pepper_bell", 0.03), ("spices", 0.02), ("oil_cooking", 0.01)]),
    (r"brown rice", [("rice_brown", 0.99), ("salt", 0.01)]),
    (r"rice|pilaf|biryani", [("rice_white", 0.97), ("oil_cooking", 0.02), ("salt", 0.01)]),
    (r"alfredo", [("sauce_prepared", 1.0)]),
    (r"marinara|tomato sauce", [("tomato_canned", 0.9), ("onion", 0.04), ("garlic", 0.02), ("oil_olive", 0.02), ("spices", 0.02)]),
    (r"gluten free.*(pasta|penne)", [("pasta_gf", 0.98), ("oil_olive", 0.02)]),
    (r"pasta|penne|spaghetti|macaroni|noodle", [("pasta", 0.98), ("oil_olive", 0.02)]),
    (r"collard|greens|kale", [("kale_collards", 0.85), ("onion", 0.07), ("garlic", 0.02), ("oil_cooking", 0.04), ("spices", 0.02)]),
    (r"broccoli.*cauliflower", [("broccoli", 0.5), ("cauliflower", 0.47), ("oil_cooking", 0.02), ("salt", 0.01)]),
    (r"broccoli", [("broccoli", 0.97), ("oil_cooking", 0.02), ("salt", 0.01)]),
    (r"medley|vegetable|veggie", [("squash_summer", 0.3), ("carrot", 0.25), ("broccoli", 0.2), ("pepper_bell", 0.17), ("onion", 0.05), ("oil_cooking", 0.02), ("salt", 0.01)]),
    (r"cucumber.*tomato|tomato.*cucumber", [("cucumber", 0.5), ("tomato", 0.42), ("vinegar", 0.04), ("oil_olive", 0.03), ("salt", 0.01)]),
    (r"potato|hash", [("potato", 0.94), ("oil_cooking", 0.04), ("spices", 0.01), ("salt", 0.01)]),
    (r"roll|bread|biscuit|bun|naan", [("bread_roll", 1.0)]),
    (r"tofu", [("tofu", 0.88), ("sauce_prepared", 0.06), ("oil_cooking", 0.04), ("spices", 0.02)]),
    (r"chicken", [("chicken_raw", 0.85), ("onion", 0.05), ("sauce_prepared", 0.04), ("oil_cooking", 0.03), ("spices", 0.02), ("salt", 0.01)]),
    (r"beef", [("beef_whole", 0.75), ("onion", 0.08), ("carrot", 0.06), ("tomato_canned", 0.05), ("oil_cooking", 0.03), ("spices", 0.02), ("salt", 0.01)]),
    (r"pork", [("pork", 0.85), ("onion", 0.06), ("sauce_prepared", 0.04), ("oil_cooking", 0.03), ("spices", 0.02)]),
    (r"turkey", [("turkey", 0.9), ("onion", 0.05), ("oil_cooking", 0.03), ("spices", 0.02)]),
    (r"salmon|fish|cod|tilapia", [("fish", 0.9), ("citrus", 0.04), ("oil_olive", 0.04), ("spices", 0.02)]),
    (r"shrimp", [("shrimp", 0.88), ("garlic", 0.03), ("butter", 0.05), ("spices", 0.04)]),
    (r"pea.*stew|black.eyed|lentil|dal", [("legumes_dried", 0.6), ("tomato_canned", 0.2), ("onion", 0.1), ("oil_cooking", 0.05), ("spices", 0.05)]),
    (r"pizza", [("pizza_base", 0.5), ("cheese_mozzarella", 0.3), ("tomato_canned", 0.2)]),
    (r"salad", [("lettuce_romaine", 0.6), ("tomato", 0.15), ("cucumber", 0.12), ("carrot", 0.08), ("dressing", 0.05)]),
    (r"fruit|melon|banana|apple|orange", [("fruit_other", 1.0)]),
]
NAME_RULES_C = [(re.compile(p, re.I), s) for p, s in NAME_RULES]

GENERIC: dict[str, list[tuple[str, float]]] = {
    "entree": [("chicken_raw", 0.4), ("rice_white", 0.2), ("onion", 0.1), ("pepper_bell", 0.1), ("tomato_canned", 0.1), ("sauce_prepared", 0.05), ("oil_cooking", 0.03), ("spices", 0.02)],
    "side": [("veg_other", 0.45), ("potato", 0.3), ("rice_white", 0.2), ("oil_cooking", 0.03), ("salt", 0.02)],
    "soup": [("veg_other", 0.3), ("potato", 0.2), ("onion", 0.15), ("carrot", 0.15), ("beans_canned", 0.12), ("soup_base", 0.06), ("spices", 0.02)],
    "salad": [("lettuce_romaine", 0.55), ("tomato", 0.15), ("cucumber", 0.12), ("carrot", 0.1), ("dressing", 0.08)],
    "dessert": [("dessert_prepared", 1.0)],
    "breakfast": [("eggs", 0.5), ("potato_frozen", 0.3), ("bread_sliced", 0.15), ("butter", 0.05)],
    "beverage": [("juice", 1.0)],
}
DEFAULT_PORTION_OZ = {"entree": 6, "side": 4, "soup": 8, "salad": 1, "dessert": 3, "breakfast": 4, "beverage": 8}

# Why: mayo is the binder (~20-30% by weight) in these salads, not a 3% condiment.
BOUND_SALAD = re.compile(r"\b(egg|tuna|chicken|potato|pasta|macaroni|ham) salad\b|coleslaw|slaw")

TRACE_SHARE = 0.005
MINOR_SHARE = 0.03


def normalize(name: str) -> str:
    s = html.unescape(str(name)).lower()
    s = s.replace("’", "'").replace("&", " and ")
    s = re.sub(r"[\"'`]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")[:60]


def split_top(s: str, seps: str) -> list[str]:
    out, buf, depth = [], [], 0
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch in seps and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return [p.strip() for p in out if p.strip()]


def components(ingredients: str) -> list[str]:
    """Top-level components in label order, sub-ingredient detail dropped."""
    s = html.unescape(str(ingredients))
    s = re.sub(r"<[^>]+>", " ", s).replace("\xa0", " ")
    comps = []
    for part in split_top(s, ";"):
        for piece in split_top(part, ","):
            head = re.sub(r"\(.*", "", piece).strip(" .*")
            head = re.sub(r"\s+", " ", head)
            if head and not SKIP.match(head):
                comps.append(head)
    return comps


def match_component(comp: str) -> str | None:
    for rx, iid in RULES_C:
        if rx.search(comp):
            return iid
    return None


def allocate(ids: list[str], promote: frozenset[str] = frozenset()) -> dict[str, float]:
    """Label-order + role allocation of batch weight shares. Returns {ingredient_id: share}."""
    seen: list[str] = []
    for i in ids:
        if i not in seen:
            seen.append(i)
    roles = {i: ("major" if i in promote else ROLE[i]) for i in seen}
    majors = [i for i in seen if roles[i] == "major"]
    if not majors:  # condiment-only items (e.g. a dressing): minors carry the dish
        majors = [i for i in seen if roles[i] == "minor"] or seen
    shares: dict[str, float] = {}
    for i in seen:
        if i in majors:
            continue
        shares[i] = TRACE_SHARE if roles[i] == "trace" else MINOR_SHARE
    fixed = sum(shares.values())
    if fixed > 0.4:  # long condiment lists: cap so the main ingredients still dominate
        for k in shares:
            shares[k] *= 0.4 / fixed
        fixed = 0.4
    # Why: labels list components by predominance; 1/rank is a transparent, monotone weighting.
    w = {m: 1.0 / (r + 1) for r, m in enumerate(majors)}
    tw = sum(w.values())
    for m in majors:
        shares[m] = (1 - fixed) * w[m] / tw
    return shares


def classify(name: str, station: str, periods: list[str]) -> str:
    """Name signals first, then the item's most common station."""
    n, st = name, (station or "").lower()
    if re.search(r"\b(soup|chili|stew|bisque|chowder|pozole|menudo|pho|gumbo|caldo)\b", n):
        return "soup"
    if re.search(r"\b(juice|coffee|tea|lemonade|smoothie|agua fresca|horchata|mockjito|milk)\b", n) and not re.search(r"chocolate|coconut milk|milk bread", n):
        return "beverage"
    if re.search(r"soft serve|cookie|cake|cupcake|brownie|\bpie\b|pudding|cobbler|crisp|cheesecake|ice cream|sundae|blondie|\btart\b|churro|macaron|mochi", n):
        return "dessert"
    if re.search(r"\b(dressing|vinaigrette|salad)\b", n):
        return "salad"
    if re.search(r"\b(eggs?|scramble|scrambled|omelet|pancakes?|waffles?|french toast|bagels?|oatmeal|yogurt|granola|hash browns?|breakfast|cream cheese|jelly|muffin|danish|croissant)\b", n):
        return "breakfast"
    if "soup" in st:
        return "soup"
    if re.search(r"dessert|soft serve|pastr", st):
        return "dessert"
    if re.search(r"salad bar|cold food bar|deli bar|appetizers/condiments|fresh fruit", st):
        return "salad"
    if re.search(r"breakfast|bagel|cereal|hot grain|yogurt|bread spreads", st) and all("breakfast" in p.lower() for p in periods):
        return "breakfast"
    if re.search(r"\b(rice|potato|potatoes|fries|steamed|roasted|roll|rolls|bread|beans|corn|broccoli|vegetables|medley|greens|pasta|penne|noodles|tortilla|naan|pilaf|quinoa|polenta|sauce|salsa|hummus|chips|sprouts)\b", n) and not re.search(r"chicken|beef|pork|tofu|shrimp|salmon|fish|turkey|lamb|bowl|curry|stir fry|lasagna|parmesan|burger|taco|burrito|sandwich|pizza|arrabbiata|tri tip|lamb|hot dog", n):
        return "side"
    return "entree"


def parse_oz(s) -> float | None:
    m = re.match(r"\s*([\d.]+)\s*oz", str(s))
    return float(m.group(1)) if m else None


def mode(series: pd.Series):
    vc = series.dropna().value_counts()
    if vc.empty:
        return None
    top = vc[vc == vc.max()].index
    return sorted(top)[0]  # deterministic tie-break


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(MENU, dtype=str)
    df["norm"] = df["item_name"].map(normalize)
    df = df[df["norm"] != ""]
    n_rows = len(df)

    freq = df["norm"].value_counts()
    order = sorted(freq.index, key=lambda k: (-freq[k], k))
    rank = {k: r for r, k in enumerate(order)}

    unmatched = Counter()
    comp_total = 0
    comp_matched = 0
    recipes, rec_ing, item_map = [], [], []

    for norm in order:
        g = df[df["norm"] == norm]
        display = mode(g["item_name"])
        station = mode(g["station"].dropna().str.strip())
        periods = sorted(g["meal_period"].dropna().unique())
        cat = classify(norm, station, periods)
        oz_vals = [v for v in g["serving_size"].map(parse_oz) if v]
        oz_vals = [v for v in oz_vals if v <= MAX_PORTION_OZ]
        portion_oz = round(float(pd.Series(oz_vals).median()), 2) if oz_vals else float(DEFAULT_PORTION_OZ[cat])
        ing_str = mode(g["ingredients"])
        src_ids = ";".join(sorted(g["recipe_id"].dropna().unique()))

        shares: dict[str, float] | None = None
        method = None
        rule = ""
        if ing_str:
            ids = []
            for c in components(ing_str):
                comp_total += 1
                iid = match_component(c)
                if iid is None:
                    unmatched[c] += 1
                    iid = "misc_dry"
                else:
                    comp_matched += 1
                ids.append(iid)
            if ids:
                promote = frozenset({"mayonnaise"}) if BOUND_SALAD.search(norm) else frozenset()
                shares = allocate(ids, promote)
                method = "nutrislice_ingredients"
        if shares is None:
            for rx, s in NAME_RULES_C:
                if rx.search(norm):
                    shares, method, rule = dict(s), "name_rule", rx.pattern
                    break
        if shares is None and rank[norm] < TOP_N:
            # Why: top items must not be generic; fall back to category template but give it its own id.
            shares, method, rule = dict(GENERIC[cat]), "name_rule", f"category_template:{cat}"

        if shares is None:
            rid = f"r_generic_{cat}"
            method = "generic_fallback"
        else:
            rid = f"r_{slug(norm)}"
            batch_lb = PORTIONS_PER_BATCH * portion_oz / 16.0
            recipes.append({"recipe_id": rid, "name": display, "category": cat,
                            "portions_per_batch": PORTIONS_PER_BATCH, "portion_oz": portion_oz,
                            "method": method, "occurrences": int(freq[norm])})
            for iid, sh in sorted(shares.items()):
                lb = batch_lb * sh
                rec_ing.append({"recipe_id": rid, "ingredient_id": iid,
                                "qty_per_batch": round(lb / LB_PER_UNIT[iid], 3), "unit": UNIT[iid],
                                "qty_lb": round(lb, 3)})
        item_map.append({"item_name_normalized": norm, "item_name_display": display, "recipe_id": rid,
                         "method": method, "rule": rule, "category": cat, "occurrences": int(freq[norm]),
                         "frequency_rank": rank[norm] + 1, "eatec_recipe_ids": src_ids})

    # Generic recipes per category (always emitted so the generator can rely on them).
    for cat, s in sorted(GENERIC.items()):
        rid = f"r_generic_{cat}"
        oz = float(DEFAULT_PORTION_OZ[cat])
        recipes.append({"recipe_id": rid, "name": f"Generic {cat}", "category": cat,
                        "portions_per_batch": PORTIONS_PER_BATCH, "portion_oz": oz,
                        "method": "generic_fallback", "occurrences": 0})
        batch_lb = PORTIONS_PER_BATCH * oz / 16.0
        for iid, sh in sorted(s):
            lb = batch_lb * sh
            rec_ing.append({"recipe_id": rid, "ingredient_id": iid,
                            "qty_per_batch": round(lb / LB_PER_UNIT[iid], 3), "unit": UNIT[iid],
                            "qty_lb": round(lb, 3)})

    ing_df = pd.DataFrame(ING, columns=ING_COLS)
    assert set(REF_XWALK) == set(ing_df["id"]), set(ing_df["id"]) ^ set(REF_XWALK)
    ref_status = {}
    for col, path, key in (("shelf_life_ref", SHELF, "ingredient"), ("loss_rate_ref", LOSS, "commodity")):
        idx = 0 if col == "shelf_life_ref" else 1
        refs = [REF_XWALK[i][idx] for i in ing_df["id"]]
        ing_df[col] = [r.lstrip("~") for r in refs]
        ing_df[col.replace("_ref", "_match")] = ["" if not r else ("proxy" if r.startswith("~") else "exact") for r in refs]
        if path.exists():
            have = set(pd.read_csv(path, dtype=str)[key].str.strip())
            missing = sorted({r for r in ing_df[col] if r and r not in have})
            if missing:
                print(f"WARNING {path.name}: crosswalk names not found: {missing}", file=sys.stderr)
            ref_status[path.name] = {"present": True, "names_not_found": missing}
        else:
            ref_status[path.name] = {"present": False}
    # Why: reference ingredients.csv shares shelf_life.csv's free-text keys, so the shelf crosswalk aligns both.
    ing_df["reference_ingredient"] = ""
    ing_df["reference_match"] = ""
    if REF_ING.exists():
        ref_names = set(pd.read_csv(REF_ING, dtype=str)["ingredient"].str.strip())
        hit = ing_df["shelf_life_ref"].isin(ref_names)
        ing_df.loc[hit, "reference_ingredient"] = ing_df.loc[hit, "shelf_life_ref"]
        ing_df.loc[hit, "reference_match"] = ing_df.loc[hit, "shelf_life_match"]
        ref_status[REF_ING.name] = {"present": True, "reference_rows": len(ref_names),
                                    "canonical_aligned": int(hit.sum()),
                                    "reference_rows_unused": sorted(ref_names - set(ing_df["shelf_life_ref"]))}
    else:
        ref_status[REF_ING.name] = {"present": False}
    used = {r["ingredient_id"] for r in rec_ing}
    ing_df["used_in_recipes"] = ing_df["id"].map(lambda i: sum(1 for r in rec_ing if r["ingredient_id"] == i))
    # Why: generator loader expects ingredient_id/unit; keep id/default_unit for the original spec.
    out_ing = ing_df.assign(ingredient_id=ing_df["id"], unit=ing_df["default_unit"])
    out_ing.sort_values("id").to_csv(OUT / "ingredients.csv", index=False)

    rec_df = pd.DataFrame(recipes).drop_duplicates("recipe_id").sort_values("recipe_id")
    rec_df["portion_lb"] = (rec_df["portion_oz"] / 16.0).round(4)
    rec_df.to_csv(OUT / "recipes.csv", index=False)
    ri = pd.DataFrame(rec_ing).drop_duplicates(["recipe_id", "ingredient_id"]).sort_values(["recipe_id", "ingredient_id"])
    ri["qty"] = ri["qty_per_batch"]
    ri.to_csv(OUT / "recipe_ingredients.csv", index=False)
    im = pd.DataFrame(item_map).sort_values("item_name_normalized")
    im.to_csv(OUT / "menu_items_unique.csv", index=False)
    # Why: generator joins per menu row (hall/date/meal/station); normalized name -> recipe_id is still 1:1.
    rows = df[["hall", "date", "meal_period", "station", "item_name", "norm", "recipe_id"]].rename(
        columns={"norm": "item_name_normalized", "recipe_id": "eatec_recipe_id"})
    rows = rows.merge(im[["item_name_normalized", "recipe_id", "method", "category"]], on="item_name_normalized", how="left")
    rows.sort_values(["hall", "date", "meal_period", "station", "item_name"], kind="mergesort").to_csv(
        OUT / "menu_item_map.csv", index=False)
    pd.DataFrame(RULES, columns=["pattern", "ingredient_id"]).to_csv(OUT / "ingredient_rules.csv", index_label="priority")
    pd.DataFrame([(p, ";".join(f"{i}:{s}" for i, s in sh)) for p, sh in NAME_RULES],
                 columns=["pattern", "shares"]).to_csv(OUT / "name_rules.csv", index_label="priority")
    pd.DataFrame(sorted(unmatched.items(), key=lambda kv: (-kv[1], kv[0])), columns=["component", "count"]).to_csv(
        OUT / "unmatched_components.csv", index=False)

    # Coverage
    occ = im.groupby("method")["occurrences"].sum()
    uniq = im["method"].value_counts()
    top = im[im["frequency_rank"] <= TOP_N]
    cov = {
        "menu_rows": n_rows,
        "unique_items_raw": int(df["item_name"].nunique()),
        "unique_items_normalized": int(len(freq)),
        "recipes_total": int(len(rec_df)),
        "ingredients_canonical": int(len(ing_df)),
        "ingredients_used": len(used),
        "recipe_ingredient_rows": int(len(ri)),
        "pct_occurrences_by_method": {k: round(100 * v / n_rows, 2) for k, v in occ.items()},
        "unique_items_by_method": {k: int(v) for k, v in uniq.items()},
        "top_n": TOP_N,
        "top_n_pct_of_occurrences": round(100 * top["occurrences"].sum() / n_rows, 2),
        "top_n_by_method": {k: int(v) for k, v in top["method"].value_counts().items()},
        "components_parsed": comp_total,
        "components_rule_matched_pct": round(100 * comp_matched / max(comp_total, 1), 2),
        "reference_ingredients_csv_present": REF_ING.exists(),
        "reference_alignment": ref_status,
        "ingredients_used_without_shelf_life_ref": sorted(i for i, r in zip(ing_df["id"], ing_df["shelf_life_ref"]) if not r and i in used),
        "ingredients_used_without_loss_rate_ref": sorted(i for i, r in zip(ing_df["id"], ing_df["loss_rate_ref"]) if not r and i in used),
    }
    # Demand-weighted view: lb of each ingredient per menu occurrence (one batch per occurrence).
    occ_by_recipe = im.groupby("recipe_id")["occurrences"].sum()
    w = ri.assign(lb_total=ri["qty_lb"] * ri["recipe_id"].map(occ_by_recipe).fillna(0))
    lb_by_ing = w.groupby("ingredient_id")["lb_total"].sum().sort_values(ascending=False)
    tot = lb_by_ing.sum()
    shelf_ok = set(ing_df.loc[ing_df["shelf_life_ref"] != "", "id"])
    loss_ok = set(ing_df.loc[ing_df["loss_rate_ref"] != "", "id"])
    cov["pct_demand_lb_with_shelf_life_ref"] = round(100 * lb_by_ing[lb_by_ing.index.isin(shelf_ok)].sum() / tot, 2)
    cov["pct_demand_lb_with_loss_rate_ref"] = round(100 * lb_by_ing[lb_by_ing.index.isin(loss_ok)].sum() / tot, 2)
    cov["pct_demand_lb_misc_dry"] = round(100 * lb_by_ing.get("misc_dry", 0) / tot, 2)
    cov["top_shelf_life_gaps_by_demand_lb_pct"] = {
        k: round(100 * v / tot, 2) for k, v in lb_by_ing.items() if k not in shelf_ok and v / tot >= 0.005}
    lb_by_ing.rename("demand_lb_per_menu_window").to_csv(OUT / "ingredient_demand_weights.csv")
    (OUT / "coverage.json").write_text(json.dumps(cov, indent=2, sort_keys=True) + "\n")
    print(json.dumps(cov, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
