"""Build data/raw/reference/{shelf_life,loss_rates,ingredients,yields}.csv from the
raw files downloaded by scripts/fetch_benchmarks.py. Pure parsing, no network.

Run:  uv run --python-preference only-managed --isolated \
        --with pandas --with openpyxl --with xlrd python scripts/build_reference_tables.py
"""
from __future__ import annotations

import csv
import io
import re
import warnings
import zipfile
from fractions import Fraction
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data" / "raw" / "reference"

FK_XLS = REF / "foodkeeper" / "FoodKeeper-Data.xls"
FK_URL = "https://catalog.data.gov/dataset/fsis-foodkeeper-data"  # canonical; file is a GitHub mirror, see MANIFEST
FDC_ZIP = REF / "fdc" / "FoodData_Central_sr_legacy_food_csv_2018-04.zip"
FBG_DIR = REF / "fbg" / "yield_tables"
FBG_URL = "https://foodbuyingguide.fns.usda.gov/files/Reports/USDA_FBG_{}"
LAFA_DIR = REF / "ers_lafa"
LAFA_URL = "https://www.ers.usda.gov/data-products/food-availability-per-capita-data-system/"
AH697_URL = "https://www.ers.usda.gov/media/7780/ah-697.pdf"
FAL_URL = "https://fns-prod.azureedge.us/sites/default/files/resource-files/usdafis-fal-sy26-27.pdf"
FBG_UNIT_URL = "https://foodbuyingguide.fns.usda.gov/"
G_PER_LB = 453.592

# One spec per ingredient. Fields:
#   fdc: SR Legacy description (kcal, portions); fdc_cooked: cooked form for cup->weight yields
#   fk: FoodKeeper product IDs; lafa: (workbook, sheet)
#   fbg: (regex on "Food As Purchased (AP)", purchase-unit regex, serving regex, method)
#   case: (unit label, lb per unit, source url, note)
S = [
 dict(i="chicken breast, boneless skinless", c="protein", fdc="Chicken, broiler or fryers, breast, skinless, boneless, meat only, raw",
      fk=[117], lafa=("meat-poultry-fish-eggs-nuts.xls", "Chicken"),
      fbg=(r"^Chicken, Boneless.*Tenders", r"^Pound", r"^1 oz", "lb_note"),
      case=("4/10 lb bag case", 40, FAL_URL, "proxy: USDA Foods raw cut-up chicken pack; no boneless breast item listed")),
 dict(i="chicken thigh, boneless skinless", c="protein", fdc="Chicken, broilers or fryers, dark meat, thigh, meat only, raw",
      fk=[118], lafa=("meat-poultry-fish-eggs-nuts.xls", "Chicken"),
      fbg=(r"^Chicken Parts.*Thighs Thighs \(boneless", r"^Pound", r"^1 oz", "lb_note"),
      case=("4/10 lb bag case", 40, FAL_URL, "proxy: USDA Foods raw cut-up chicken pack")),
 dict(i="ground beef 80/20", c="protein", fdc="Beef, ground, 80% lean meat / 20% fat, raw",
      fk=[43], lafa=("meat-poultry-fish-eggs-nuts.xls", "Beef"),
      fbg=(r"^Beef, Ground, fresh or frozen no more than 20% fat", r"^Pound", r"^1 oz", "lb_note"),
      case=("40 lb case", 40, FAL_URL, "USDA Foods fine ground beef 85/15 raw frozen")),
 dict(i="pork shoulder, boneless", c="protein", fdc="Pork, fresh, shoulder, whole, separable lean and fat, raw",
      fk=[74], lafa=("meat-poultry-fish-eggs-nuts.xls", "Pork"),
      fbg=(r"^Pork Shoulder, Boston Butt.*Without bone", r"^Pound", r"^1 oz", "lb_note"),
      case=("36-42 lb case", 39, FAL_URL, "proxy: USDA Foods pork leg roast raw frozen; midpoint")),
 dict(i="salmon fillet", c="protein", fdc="Fish, salmon, Atlantic, farmed, raw",
      fk=[146], lafa=("meat-poultry-fish-eggs-nuts.xls", "Fresh and frozen fish"),
      fbg=(r"^Seafood, pouch pack, Salmon", r"^Pound", r"^1 oz", "lb_note"),
      case=("pound", 1, FBG_UNIT_URL, "GAP: no public case weight for fresh salmon; FBG yield is for pouch salmon")),
 dict(i="tofu, firm", c="protein", fdc="Tofu, raw, firm, prepared with calcium sulfate",
      fk=[168], lafa=None,
      fbg=(r"^Tofu Commercially-prepared;\s*2\.2", r"^Pound", r".", "servings_x_oz:2.2"),
      case=("pound", 1, FBG_UNIT_URL, "GAP: no public institutional case weight")),
 dict(i="eggs, shell, large", c="protein", fdc="Egg, whole, raw, fresh",
      fk=[21], lafa=("meat-poultry-fish-eggs-nuts.xls", "Eggs"),
      fbg=(r"^Eggs, Shell Eggs", r"^Dozen", r".", "servings_x_portion:large"),
      case=("case, 30 dozen", 47.0, AH697_URL, "AH-697 Table 6")),
 dict(i="black beans, canned", c="protein", fdc="Beans, black turtle, mature seeds, canned",
      fk=[372], lafa=("vegetables.xlsx", "Dry black beans"),
      fbg=(r"^Beans, Black, \(Turtle\), dry, canned.*Low sodium", r"^No\. 10", r"unheated", "can_drained"),
      case=("6/#10 can case", round(6 * 109 / 16, 2), FAL_URL, "USDA Foods 6/#10 can; 109 oz/can from FBG")),
 dict(i="chickpeas, canned", c="protein", fdc="Chickpeas (garbanzo beans, bengal gram), mature seeds, canned, drained solids",
      fk=[372], lafa=("vegetables.xlsx", "Other dry beans"),
      fbg=(r"^Beans, Garbanzo.*canned.*Low s", r"^No\. 10 Can \(105", r".", "can_drained"),
      case=("6/#10 can case", round(6 * 105 / 16, 2), FAL_URL, "USDA Foods 6/#10 can; 105 oz/can from FBG")),
 dict(i="lentils, dry", c="protein", fdc="Lentils, raw", fdc_cooked="Lentils, mature seeds, cooked, boiled, without salt",
      fk=[334], lafa=("vegetables.xlsx", "Dry peas and lentils"),
      fbg=(r"^Lentils, dry", r"^Pound", r".", "servings_x_cup_cooked:0.25"),
      case=("pound", 1, FBG_UNIT_URL, "GAP: no public case weight (USDA Foods dry pinto beans ship 12/2 lb)")),
 dict(i="white rice, long grain", c="grain", fdc="Rice, white, long-grain, regular, raw, enriched", fdc_cooked="Rice, white, long-grain, regular, enriched, cooked",
      fk=[338, 178], lafa=("grains.xlsx", "Rice"),
      fbg=(r"^Rice \(Group H\) White, Long grain, Regular", r"^Pound", r".", "servings_x_cup_cooked:0.25"),
      case=("25 lb bag", 25, FAL_URL, "USDA Foods long grain parboiled rice")),
 dict(i="brown rice, long grain", c="grain", fdc="Rice, brown, long-grain, raw (Includes foods for USDA's Food Distribution Program)",
      fdc_cooked="Rice, brown, long-grain, cooked (Includes foods for USDA's Food Distribution Program)",
      fk=[339, 178], lafa=("grains.xlsx", "Rice"),
      fbg=(r"^Rice \(Group H\) Brown, Long grain, Regular", r"^Pound", r".", "servings_x_cup_cooked:0.25"),
      case=("25 lb bag", 25, FAL_URL, "USDA Foods brown rice parboiled")),
 dict(i="pasta, dry (spaghetti/penne)", c="grain", fdc="Pasta, dry, enriched", fdc_cooked="Pasta, cooked, enriched, without added salt",
      fk=[335, 177], lafa=("grains.xlsx", "Durum flour"),
      fbg=(r"^Pasta \(Group H\) Elbow Macaroni, Regular, Enriched", r"^Pound", r".", "servings_x_cup_cooked:0.25"),
      case=("20 lb case", 20, FAL_URL, "USDA Foods enriched spaghetti")),
 dict(i="sandwich bread, sliced", c="grain", fdc="Bread, white, commercially prepared (includes soft bread crumbs)",
      fk=[461], lafa=("grains.xlsx", "White and whole wheat flour"),
      fbg=(r"^Bread \(Group B\) Sliced", r"^Pound", r".", "ready_to_serve"),
      case=("pound", 1, FBG_UNIT_URL, "GAP: loaf/case weights not in public USDA lists")),
 dict(i="flour tortillas", c="grain", fdc="Tortillas, ready-to-bake or -fry, flour, refrigerated",
      fk=[196], lafa=("grains.xlsx", "White and whole wheat flour"), fbg=None,
      case=("12/24 count case (8 inch)", "portion:288", FAL_URL, "USDA Foods WGR tortillas; lb derived from FDC per-tortilla weight")),
 dict(i="rolled oats", c="grain", fdc="Cereals, oats, regular and quick, not fortified, dry",
      fdc_cooked="Cereals, oats, regular and quick, unenriched, cooked with water (includes boiling and microwaving), without salt",
      fk=[585, 375], lafa=("grains.xlsx", "Oat products"),
      fbg=(r"^Cereal Grains Oats \(Group H\) Rolled, Regular", r"^Pound", r".", "servings_x_cup_cooked:0.25"),
      case=("12/42 oz tube case", round(12 * 42 / 16, 2), FAL_URL, "USDA Foods quick rolled oats")),
 dict(i="quinoa", c="grain", fdc="Quinoa, uncooked", fdc_cooked="Quinoa, cooked",
      fk=[425, 426], lafa=None,
      fbg=(r"^Cereal Grains Quinoa", r"^Pound", r".", "lb_note"),
      case=("pound", 1, FBG_UNIT_URL, "GAP: no public case weight")),
 dict(i="spinach, fresh", c="produce", fdc="Spinach, raw", fk=[291], lafa=("vegetables.xlsx", "Fresh spinach"),
      fbg=(r"^Spinach, fresh Partly trimmed", r"^Pound", r".", "lb_note"),
      case=("bushel", 25, AH697_URL, "AH-697 Table 6 (1992)")),
 dict(i="romaine lettuce", c="produce", fdc="Lettuce, cos or romaine, raw", fk=[290], lafa=("vegetables.xlsx", "Fresh leaf lettuce"),
      fbg=(r"^Lettuce, fresh Romaine, Untrimmed", r"^Pound", r".", "lb_note"),
      case=("carton", 50, AH697_URL, "AH-697 'Lettuce, carton' (head lettuce); romaine cartons may differ")),
 dict(i="tomatoes, fresh", c="produce", fdc="Tomatoes, red, ripe, raw, year round average", fk=[306], lafa=("vegetables.xlsx", "Fresh tomatoes"),
      fbg=(r"^Tomatoes, fresh Whole, All sizes", r"^Pound", r".", "lb_note"),
      case=("carton", 25, AH697_URL, "AH-697 Table 6")),
 dict(i="bell peppers", c="produce", fdc="Peppers, sweet, green, raw", fk=[296], lafa=("vegetables.xlsx", "Fresh bell peppers"),
      fbg=(r"^Peppers, Bell, fresh Green", r"^Pound", r".", "lb_note"),
      case=("1-1/9 bushel carton", 28, AH697_URL, "AH-697 Table 6, green peppers")),
 dict(i="onions, yellow", c="produce", fdc="Onions, raw", fk=[294], lafa=("vegetables.xlsx", "Fresh onions"),
      fbg=(r"^Onions, Mature, fresh All sizes", r"^Pound", r".", "lb_note"),
      case=("sack", 50, AH697_URL, "AH-697 Table 6")),
 dict(i="potatoes, russet", c="produce", fdc="Potatoes, flesh and skin, raw", fk=[297], lafa=("vegetables.xlsx", "Fresh potatoes"),
      fbg=(r"^Potatoes, fresh White or Russet, All sizes", r"^Pound", r".", "lb_note"),
      case=("carton or sack", 100, AH697_URL, "AH-697 (1992) lists 100 lb; 50 lb cartons are common today (unsourced)")),
 dict(i="sweet potatoes", c="produce", fdc="Sweet potato, raw, unprepared (Includes foods for USDA's Food Distribution Program)", fk=[422],
      lafa=("vegetables.xlsx", "Fresh sweet potatoes"),
      fbg=(r"^Sweet Potatoes, fresh Whole", r"^Pound", r".", "lb_note:peeled"),
      case=("carton", 40, AH697_URL, "AH-697 Table 6")),
 dict(i="carrots", c="produce", fdc="Carrots, raw", fk=[279], lafa=("vegetables.xlsx", "Fresh carrots"),
      fbg=(r"^Carrots, fresh Without tops", r"^Pound", r".", "lb_note"),
      case=("sack", 50, AH697_URL, "AH-697 Table 6")),
 dict(i="broccoli", c="produce", fdc="Broccoli, raw", fk=[276], lafa=("vegetables.xlsx", "Fresh broccoli"),
      fbg=(r"^Broccoli, fresh Untrimmed", r"^Pound", r".", "lb_note"),
      case=("carton", 23, AH697_URL, "AH-697 Table 6")),
 dict(i="cucumbers", c="produce", fdc="Cucumber, with peel, raw", fk=[283], lafa=("vegetables.xlsx", "Fresh cucumbers"),
      fbg=(r"^Cucumbers, fresh Whole", r"^Pound", r".", "lb_note"),
      case=("1-1/9 bushel carton", 55, AH697_URL, "AH-697 Table 6")),
 dict(i="mushrooms, white", c="produce", fdc="Mushrooms, white, raw", fk=[292], lafa=("vegetables.xlsx", "Fresh mushrooms"),
      fbg=(r"^Mushrooms, fresh Whole", r"^Pound", r".", "lb_note"),
      case=("pound", 1, FBG_UNIT_URL, "GAP: not in AH-697 Table 6")),
 dict(i="zucchini", c="produce", fdc="Squash, summer, zucchini, includes skin, raw", fk=[302], lafa=("vegetables.xlsx", "Fresh squash"),
      fbg=(r"^Squash, summer, fresh Zucchini", r"^Pound", r".", "lb_note"),
      case=("pound", 1, FBG_UNIT_URL, "GAP: not in AH-697 Table 6")),
 dict(i="cabbage, green", c="produce", fdc="Cabbage, raw", fk=[278], lafa=("vegetables.xlsx", "Fresh cabbage"),
      fbg=(r"^Cabbage, fresh Green, Untrimmed", r"^Pound", r".", "lb_note"),
      case=("mesh bag or sack", 50, AH697_URL, "AH-697 Table 6")),
 dict(i="avocados", c="produce", fdc="Avocados, raw, California", fk=[250], lafa=("fruit.xlsx", "Fresh avocados"),
      fbg=(r"^Avocados, fresh All sizes", r"^Pound", r".", "lb_note"),
      case=("lug", 13.5, AH697_URL, "AH-697 lists 12-15 lb; midpoint")),
 dict(i="bananas", c="produce", fdc="Bananas, raw", fk=[251], lafa=("fruit.xlsx", "Fresh bananas"),
      fbg=(r"^Bananas, fresh 100-120 count", r"^Pound", r".", "lb_note"),
      case=("carton", 40, AH697_URL, "AH-697 Table 6")),
 dict(i="apples", c="produce", fdc="Apples, raw, with skin (Includes foods for USDA's Food Distribution Program)", fk=[248],
      lafa=("fruit.xlsx", "Fresh apples"),
      fbg=(r"^Apples, fresh Whole, Includes USDA Foods", r"^Pound", r".", "lb_note"),
      case=("40 lb case", 40, FAL_URL, "USDA Foods fresh apples; AH-697 also 40 lb")),
 dict(i="oranges", c="produce", fdc="Oranges, raw, all commercial varieties", fk=[256], lafa=("fruit.xlsx", "Fresh oranges"),
      fbg=(r"^Oranges, fresh 72-88 count", r"^Pound", r".", "lb_note"),
      case=("carton (CA/AZ)", 38, AH697_URL, "AH-697 Table 6")),
 dict(i="strawberries", c="produce", fdc="Strawberries, raw", fk=[481], lafa=("fruit.xlsx", "Fresh strawberries"),
      fbg=(r"^Strawberries, fresh Whole", r"^Pound", r".", "lb_note"),
      case=("flat, 12 x 1-pint", 12, AH697_URL, "AH-697 Table 6")),
 dict(i="milk, 2%", c="dairy", fdc="Milk, reduced fat, fluid, 2% milkfat, with added vitamin A and vitamin D", fk=[27],
      lafa=("dairy.xlsx", "2 percent milk"),
      fbg=(r"^Milk, fluid Pasteurized", r"^Gallon", r".", "ready_to_serve"),
      case=("gallon", 8.62, AH697_URL, "AH-697 Table 6")),
 dict(i="yogurt, plain low-fat", c="dairy", fdc="Yogurt, plain, low fat", fk=[33], lafa=("dairy.xlsx", "Yogurt"),
      fbg=(r"^Yogurt, fresh Plain", r"^32 oz", r".", "ready_to_serve"),
      case=("6/32 oz tub case", 12, FAL_URL, "USDA Foods high-protein yogurt tubs")),
 dict(i="cheddar cheese, shredded", c="dairy", fdc="Cheese, cheddar (Includes foods for USDA's Food Distribution Program)", fk=[5],
      lafa=("dairy.xlsx", "Cheddar cheese"),
      fbg=(r"^Cheese, American, Cheddar", r"^Pound", r".", "ready_to_serve"),
      case=("6/5 lb bag case", 30, FAL_URL, "USDA Foods shredded cheddar")),
 dict(i="mozzarella, shredded", c="dairy", fdc="Cheese, mozzarella, whole milk", fk=[5], lafa=("dairy.xlsx", "Mozzarella cheese"),
      fbg=(r"^Cheese, American, Cheddar, Mozzarella", r"^Pound", r".", "ready_to_serve"),
      case=("30 lb case", 30, FAL_URL, "USDA Foods LMPS shredded mozzarella")),
 dict(i="butter", c="dairy", fdc="Butter, salted", fk=[1], lafa=("fats-and-oils.xls", "Butter"),
      fbg=(r"^Butter", r"^Pound", r".", "ready_to_serve"),
      case=("box", 68, AH697_URL, "AH-697 Table 6 (bulk box)")),
]

# Prepared items for shelf life only (no ingredient-level purchase data).
PREPARED_FK = {173: "leftovers with meat, fish, poultry or egg", 174: "leftovers without meat (cooked vegetables, rice, potatoes)",
               177: "cooked pasta", 178: "cooked rice", 193: "soups and stews", 194: "casseroles", 135: "cooked poultry dishes",
               148: "cooked fish", 185: "main dishes or meals (hot or refrigerated)", 420: "pasta salad", 191: "potato salad",
               418: "chicken salad", 180: "guacamole", 603: "coleslaw", 175: "leftover pizza", 426: "cooked quinoa", 179: "cut fruit"}

# Why: these FoodKeeper IDs describe the cooked form, so their rows must not read as raw-ingredient shelf life.
COOKED_FK = {178, 177, 426}
# Why: FoodKeeper gives only text (use-by date / when ripe) for these, so no numeric row can be emitted.
NUMERICLESS_FK = {27, 306, 600, 179, 29, 636, 614}
UNIT_DAYS = {"indefinitely": 3650, "days": 1, "day": 1, "weeks": 7, "week": 7, "months": 30, "month": 30, "years": 365, "year": 365}


def parse_mixed(s: str) -> float:
    s = s.strip().replace("–", "-")
    if "-" in s and "/" in s:  # 7-1/2
        whole, frac = s.split("-", 1)
        return float(whole) + float(Fraction(frac))
    if " " in s and "/" in s:
        whole, frac = s.split(" ", 1)
        return float(whole) + float(Fraction(frac))
    return float(Fraction(s))


def load_fdc():
    z = zipfile.ZipFile(FDC_ZIP)
    base = "FoodData_Central_sr_legacy_food_csv_2018-04/"
    rd = lambda n: pd.read_csv(io.BytesIO(z.read(base + n)), dtype=str)
    food = rd("food.csv")
    fn = rd("food_nutrient.csv")
    kcal = fn[fn.nutrient_id == "1008"].set_index("fdc_id").amount.astype(float).to_dict()
    port = rd("food_portion.csv")
    unit = rd("measure_unit.csv").set_index("id").name.to_dict()
    port["unit"] = port.measure_unit_id.map(unit)
    by_desc = food.set_index("description").fdc_id.to_dict()
    return by_desc, kcal, port


def fdc_portion_g(port, fid, want):
    p = port[port.fdc_id == fid]
    for _, r in p.iterrows():
        raw = f"{r.amount} {r.unit if r.unit != 'undetermined' else ''} {r.modifier} {r.portion_description}"
        label = re.sub(r"\s+", " ", raw.replace("nan", "")).strip().lower()
        if re.search(want, label):
            return float(r.gram_weight) / float(r.amount or 1), label.strip()
    return None, None


CANON_MAP = ROOT / "scripts" / "canonical_reference_map.csv"
RECIPE_ING = ROOT / "data" / "recipes" / "ingredients.csv"
PRIMARY_STORAGE = {"cooler": "refrigerator", "dry": "pantry", "freezer": "freezer"}


def load_canonical_map():
    with CANON_MAP.open() as f:
        return list(csv.DictReader(f))


def build_shelf_life():
    p = pd.read_excel(FK_XLS, "Product")
    rows = []

    def emit(name, cat, fkid, cooked=False, canonical_id="", confidence="high", note="", primary=""):
        r = p[p.ID == fkid]
        if r.empty:
            return
        r = r.iloc[0]
        fk_name = f"{r.Name}" + (f" ({r.Name_subtitle})" if isinstance(r.Name_subtitle, str) else "")
        for storage, pre, clock in [("pantry", "Pantry", "unspecified"), ("pantry", "DOP_Pantry", "from purchase"),
                                    ("pantry_after_opening", "Pantry_After_Opening", "after opening"),
                                    ("refrigerator", "Refrigerate", "unspecified"),
                                    ("refrigerator", "DOP_Refrigerate", "from purchase"),
                                    ("refrigerator_after_opening", "Refrigerate_After_Opening", "after opening"),
                                    ("refrigerator_after_thawing", "Refrigerate_After_Thawing", "after thawing"),
                                    ("freezer", "Freeze", "unspecified"), ("freezer", "DOP_Freeze", "from purchase")]:
            lo, hi, met = r.get(f"{pre}_Min"), r.get(f"{pre}_Max"), r.get(f"{pre}_Metric")
            if not isinstance(met, str) or met.lower() not in UNIT_DAYS:
                continue
            if met.lower() == "indefinitely":  # Why: FoodKeeper says "Indefinitely"; encode as 10 years so it stays numeric.
                lo = hi = 1
            if pd.isna(lo):
                continue
            k = UNIT_DAYS[met.lower()]
            if cooked and clock in ("unspecified", "after cooking/prep or unspecified"):
                clock = "after cooking"
            rows.append(dict(ingredient=name, category=cat, storage=storage, shelf_life_days_low=round(lo * k),
                             shelf_life_days_high=round((hi if not pd.isna(hi) else lo) * k), source_url=FK_URL,
                             clock_starts=clock, foodkeeper_id=int(fkid), foodkeeper_name=fk_name,
                             original=met if met.lower() == "indefinitely" else f"{lo:g}-{hi:g} {met}", canonical_id=canonical_id,
                             shelf_life_days=round(((lo + (hi if not pd.isna(hi) else lo)) / 2) * k, 1),
                             confidence=confidence, primary_storage=int(storage == primary) if primary else "",
                             note=note))

    for s in S:
        for fkid in s["fk"]:
            if fkid in COOKED_FK:
                emit(f"{s['i']} (cooked)", "prepared", fkid, cooked=True)
            else:
                emit(s["i"], s["c"], fkid)
    for fkid, label in PREPARED_FK.items():
        if not any(r["foodkeeper_id"] == fkid for r in rows):
            emit(label, "prepared", fkid, cooked=True)
    for r in rows:  # Why: generic "canned goods" stands in for canned beans, so it is not a direct match.
        if r["foodkeeper_id"] == 372:
            r["confidence"] = "med"

    recipe = {}
    if RECIPE_ING.exists():
        with RECIPE_ING.open() as f:
            recipe = {r["id"]: r for r in csv.DictReader(f)}
    for m in load_canonical_map():
        cid, rec = m["canonical_id"], recipe.get(m["canonical_id"], {})
        primary = PRIMARY_STORAGE.get(rec.get("storage", ""), "")
        for fkid in [int(x) for x in m["foodkeeper_ids"].split(";") if x]:
            n0 = len(rows)
            emit(rec.get("name", cid), rec.get("category", ""), fkid, cooked=fkid in COOKED_FK or fkid in PREPARED_FK,
                 canonical_id=cid, confidence=m["shelf_confidence"], note=m["note"], primary=primary)
            if len(rows) == n0 and fkid not in NUMERICLESS_FK:
                print(f"  note: FoodKeeper {fkid} has no numeric storage value ({cid})")
    # Why: some items (dressing, mayo) list only an after-opening fridge value; flag it primary when nothing better exists.
    fallback = {"refrigerator": "refrigerator_after_opening", "pantry": "pantry_after_opening"}
    for cid in {r["canonical_id"] for r in rows if r["canonical_id"]}:
        mine = [r for r in rows if r["canonical_id"] == cid]
        if not any(r["primary_storage"] == 1 for r in mine):
            prim = PRIMARY_STORAGE.get(recipe.get(cid, {}).get("storage", ""), "")
            for r in mine:
                if r["storage"] == fallback.get(prim):
                    r["primary_storage"] = 1
    covered = {r["canonical_id"] for r in rows if r["canonical_id"]}
    print("  canonical ids with no shelf-life row:", sorted({m["canonical_id"] for m in load_canonical_map()} - covered))
    return rows


def lafa_latest(f, sheet):
    d = pd.read_excel(LAFA_DIR / f, sheet_name=sheet, header=None)
    hdr = [str(v).lower() for v in d.iloc[1].tolist()]
    num = lambda c: pd.to_numeric(d[c], errors="coerce")
    if ("loss from primary" in hdr[2] or "gain from primary" in hdr[2]) and "loss from retail" in hdr[4]:
        r = d[num(0).notna() & num(4).notna()].iloc[-1]
        gain = "gain from primary" in hdr[2]  # Why: canned items gain weight (added liquid) before retail.
        return dict(year=int(r[0]), primary_to_retail_loss_pct=-float(r[2]) if gain else float(r[2]),
                    retail_loss_pct=float(r[4]), consumer_nonedible_pct=float(r[6]), consumer_loss_pct=float(r[8]),
                    total_loss_pct=float(r[9]), lafa_layout="gain_pct_columns" if gain else "loss_pct_columns")
    if hdr[1].startswith("primary weight") and hdr[2].startswith("retail weight") and "total loss" in hdr[4]:
        r = d[num(0).notna() & num(1).notna()].iloc[-1]
        P, R, C, A = (float(r[i]) for i in (1, 2, 3, 5))
        return dict(year=int(r[0]), primary_to_retail_loss_pct=100 * (P - R) / P, retail_loss_pct=100 * (R - C) / R,
                    consumer_nonedible_pct=0.0, consumer_loss_pct=100 * (C - A) / C, total_loss_pct=float(r[4]),
                    lafa_layout="derived_from_weights")
    if hdr[1].startswith("primary weight") and hdr[2].startswith("retail weight") and "total loss" in hdr[5]:
        # Why: aggregate sweetener sheets publish only weights; derive stage losses from successive weights.
        r = d[num(0).notna() & num(1).notna()].iloc[-1]
        P, R, C, E, A = (float(r[i]) for i in (1, 2, 3, 4, 6))
        return dict(year=int(r[0]), primary_to_retail_loss_pct=100 * (P - R) / P, retail_loss_pct=100 * (R - C) / R,
                    consumer_nonedible_pct=100 * (C - E) / C, consumer_loss_pct=100 * (E - A) / E,
                    total_loss_pct=float(r[5]), lafa_layout="derived_from_weights")
    raise ValueError("unrecognized LAFA layout")


def build_loss_rates():
    rows = []
    for f in sorted(LAFA_DIR.glob("*.xls*")):
        x = pd.ExcelFile(f)
        for sh in x.sheet_names[1:]:
            try:
                v = lafa_latest(f.name, sh)
            except Exception as e:  # noqa: BLE001  # Why: a few aggregate sheets have no numeric year rows.
                print(f"  skip {f.name}:{sh} ({e})")
                continue
            rows.append(dict(commodity=sh, retail_loss_pct=round(v["retail_loss_pct"], 2),
                             consumer_loss_pct=round(v["consumer_loss_pct"], 2), source_url=LAFA_URL,
                             year=v["year"], consumer_nonedible_pct=round(v["consumer_nonedible_pct"], 2),
                             primary_to_retail_loss_pct=round(v["primary_to_retail_loss_pct"], 2),
                             total_loss_pct=round(v["total_loss_pct"], 2), lafa_workbook=f.name,
                             lafa_layout=v["lafa_layout"], canonical_id="", confidence="med", note=""))
    by_name = {r["commodity"]: r for r in rows}
    canon = []
    for m in load_canonical_map():
        if not m["lafa_commodity"]:
            continue
        base = by_name.get(m["lafa_commodity"])
        assert base, f"LAFA commodity not found: {m['lafa_commodity']}"
        canon.append({**base, "canonical_id": m["canonical_id"], "confidence": m["loss_confidence"], "note": m["note"]})
    return rows + canon


def load_fbg():
    frames = []
    for f in sorted(FBG_DIR.glob("*.xlsx")):
        d = pd.read_excel(f, sheet_name=0)
        d.columns = [c.strip() for c in d.columns]
        d["file"] = f.name
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    for c in ["Food As Purchased (AP)", "Purchase Unit", "Serving Size per Meal Contribution", "Additional Information"]:
        d[c] = d[c].fillna("").astype(str).str.strip()
    return d


def unit_lb(unit: str):
    u = unit.lower()
    if u.startswith("pound"):
        return 1.0
    if u.startswith("gallon"):
        return 8.62  # AH-697 milk gallon
    m = re.search(r"\(([\d\-/ ]+) oz\)", unit) or re.search(r"([\d\-/ ]+) oz", unit)
    return round(parse_mixed(m.group(1)) / 16, 4) if m else None


def build_yields_and_ingredients():
    by_desc, kcal, port = load_fdc()
    fbg = load_fbg()
    ylds, ings = [], []
    for s in S:
        fid = by_desc.get(s["fdc"])
        assert fid, f"FDC description not found: {s['fdc']}"
        yrow = dict(ingredient=s["i"], category=s["c"])
        if s.get("fbg"):
            ap_re, unit_re, serv_re, method = s["fbg"]
            m = fbg[fbg["Food As Purchased (AP)"].str.contains(ap_re, regex=True)
                    & fbg["Purchase Unit"].str.contains(unit_re, regex=True)
                    & fbg["Serving Size per Meal Contribution"].str.contains(serv_re, regex=True)]
            assert len(m), f"FBG row not found for {s['i']}"
            r = m.iloc[0]
            ap_lb = unit_lb(r["Purchase Unit"])
            servings = float(r["Servings per Purchase Unit, Edible Portion (EP)"])
            note = r["Additional Information"]
            factor, basis = None, ""
            kind, _, arg = method.partition(":")
            if kind == "lb_note":
                pats = [rf"1 (?:lb|lb AP|lb dry)\s*=\s*(?:about\s*)?([\d.]+) lb[^;]*{arg}[^;]*", r"1 (?:lb|lb AP|lb dry)\s*=\s*(?:about\s*)?([\d.]+) lb([^;]*)",
                        r"([\d.]+) lb \([^)]*\) cooked[^;]*"]
                for pat in pats:
                    mm = re.search(pat, note)
                    if mm:
                        factor, basis = float(mm.group(1)), mm.group(0)
                        break
            elif kind == "can_drained":
                mm = re.search(r"=\s*(?:about\s*)?([\d.]+) oz[^;]*drained[^;]*", note)
                can_oz = ap_lb * 16
                factor, basis = round(float(mm.group(1)) / can_oz, 3), mm.group(0)
            elif kind == "servings_x_oz":
                factor, basis = round(servings * float(arg) / (ap_lb * 16), 3), f"{servings} servings x {arg} oz"
            elif kind == "servings_x_portion":
                g, lab = fdc_portion_g(port, fid, arg)
                factor, basis = round(servings * g / (ap_lb * G_PER_LB), 3), f"{servings:g} x {g:g} g ({lab}) edible"
            elif kind == "servings_x_cup_cooked":
                cid = by_desc[s["fdc_cooked"]]
                g, lab = fdc_portion_g(port, cid, r"^1(\.0)? cup")
                cups = servings * float(arg)
                factor, basis = round(cups * g / (ap_lb * G_PER_LB), 3), f"{cups:g} cups cooked x {g:g} g/cup (FDC {cid})"
            elif kind == "ready_to_serve":
                factor, basis = 1.0, "no trim or cooking loss; served as purchased"
            assert factor, f"no yield for {s['i']}"
            yrow.update(fbg_food_as_purchased=r["Food As Purchased (AP)"].replace("\n", " "), purchase_unit=r["Purchase Unit"],
                        ap_lb_per_purchase_unit=ap_lb, servings_per_purchase_unit=servings,
                        fbg_serving_size=r["Serving Size per Meal Contribution"].replace("\n", " "),
                        yield_factor_ep_per_ap=factor, yield_basis=basis.strip(), yield_method=kind,
                        fbg_additional_info=note.replace("\n", " "),
                        source_url=FBG_URL.format(r["file"]))
        else:
            yrow.update(fbg_food_as_purchased="", purchase_unit="", ap_lb_per_purchase_unit="", servings_per_purchase_unit="",
                        fbg_serving_size="", yield_factor_ep_per_ap=1.0, yield_basis="GAP: not in FBG; assumed ready-to-serve",
                        yield_method="assumed", fbg_additional_info="", source_url="")
        ylds.append(yrow)

        unit, lb, src, note = s["case"]
        if isinstance(lb, str) and lb.startswith("portion:"):
            n = int(lb.split(":")[1])
            g, lab = fdc_portion_g(port, fid, r"tortilla")
            lb, note = round(n * g / G_PER_LB, 2), note + f" ({g:g} g each per FDC '{lab}')"
        g_cup, _ = fdc_portion_g(port, fid, r"^1(\.0)? cup")
        ings.append(dict(ingredient=s["i"], category=s["c"], unit=unit, lb_per_unit=lb,
                         kcal_per_100g=kcal.get(fid), source_url=src, unit_note=note, fdc_id=fid, fdc_description=s["fdc"],
                         kcal_source_url=f"https://fdc.nal.usda.gov/food-details/{fid}/nutrients",
                         g_per_cup=g_cup if g_cup else "", lafa_commodity=s["lafa"][1] if s["lafa"] else ""))
    return ylds, ings


def write(path: Path, rows: list[dict]):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path.relative_to(ROOT)}: {len(rows)} rows")


if __name__ == "__main__":
    write(REF / "shelf_life.csv", build_shelf_life())
    write(REF / "loss_rates.csv", build_loss_rates())
    y, i = build_yields_and_ingredients()
    write(REF / "yields.csv", y)
    write(REF / "ingredients.csv", i)
