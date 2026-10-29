"""Input loading. Every loader prefers the real file named in config/paths.yaml and falls back
(with a WARNING) to generator/fallback/ or a derived placeholder when it is missing.

Ingredient attributes resolve per ingredient in this order:
  1. recipe-mapper link columns in data/recipes/ingredients.csv (reference_ingredient, shelf_life_ref, loss_rate_ref)
  2. generator/config/ingredient_crosswalk.csv
  3. category rows in generator/fallback/{shelf_life,yields}.csv (PLACEHOLDER)
Each resolved value records its source row so tests can verify it exists."""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from . import menu_text_recipes

log = logging.getLogger("generator")

REPO_ROOT = Path(__file__).resolve().parent.parent
GEN_DIR = Path(__file__).resolve().parent
CONFIG_DIR = GEN_DIR / "config"

MEAL_NORMALIZE = {"breakfast": "breakfast", "brunch": "brunch", "lunch": "lunch", "dinner": "dinner"}
UNIT_TO_LB = {"lb": 1.0, "lbs": 1.0, "pound": 1.0, "oz": 1 / 16, "g": 1 / 453.592, "kg": 2.20462}
STORAGE_NORMALIZE = {"cooler": "refrigerated", "refrigerated": "refrigerated", "refrigerator": "refrigerated",
                     "freezer": "frozen", "frozen": "frozen", "dry": "dry", "pantry": "dry", "none": "none"}
# Reference shelf_life.csv uses FoodKeeper storage words.
# LAFA rows that sum other rows; their nonedible "pct" is not a share.
LAFA_AGGREGATES = {"Fresh vegetables", "Fresh fruit", "Fresh noncitrus", "Fresh citrus"}
STORAGE_TO_FOODKEEPER = {"refrigerated": "refrigerator", "frozen": "freezer", "dry": "pantry"}


@dataclass
class Inputs:
    menu: pd.DataFrame
    hall_attrs: pd.DataFrame
    hall_volume: pd.DataFrame
    benchmarks: pd.DataFrame
    uc_numbers: pd.DataFrame
    ingredients: pd.DataFrame          # one row per ingredient_id with resolved shelf life / yield
    recipes: pd.DataFrame              # recipe_id, name, portions_per_batch, portion_lb
    recipe_ingredients: pd.DataFrame   # recipe_id, ingredient_id, qty, unit, qty_lb (per batch, as-served basis)
    menu_recipe: pd.Series             # menu_row -> recipe_id
    provenance: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reference_files: dict = field(default_factory=dict)   # name -> DataFrame actually used (for tests)


def load_paths(path: Path | None = None) -> dict:
    with open(path or CONFIG_DIR / "paths.yaml") as f:
        return yaml.safe_load(f)


class _Ctx:
    def __init__(self, paths: dict):
        self.paths = paths
        self.prov: list[dict] = []
        self.warnings: list[str] = []

    def warn(self, msg: str) -> None:
        log.warning(msg)
        self.warnings.append(msg)

    def resolve(self, name: str, required: bool = True) -> tuple[Path | None, bool]:
        spec = self.paths[name]
        real = REPO_ROOT / spec["path"]
        if real.exists():
            self.prov.append({"input": name, "path": spec["path"], "status": "real"})
            return real, False
        fb = spec.get("fallback")
        if fb and (REPO_ROOT / fb).exists():
            self.warn(f"{name}: {spec['path']} missing, using PLACEHOLDER {fb}")
            self.prov.append({"input": name, "path": fb, "status": "fallback", "missing": spec["path"]})
            return REPO_ROOT / fb, True
        if required:
            raise FileNotFoundError(f"required input {name} not found at {spec['path']}")
        self.prov.append({"input": name, "path": spec["path"], "status": "missing"})
        return None, False


def read_fallback(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, comment="#")


def normalize_meal(raw: str) -> str:
    tail = str(raw).split("-")[-1].strip().lower()
    return MEAL_NORMALIZE.get(tail, tail)


def normalize_station(raw: str) -> str:
    return re.sub(r"\s+", " ", str(raw)).strip().lower()


def normalize_item_name(name: str) -> str:
    # Mirrors scripts/build_recipes.py normalize() so menu rows join to menu_item_map.csv.
    s = html.unescape(str(name)).lower()
    s = s.replace("’", "'").replace("&", " and ")
    s = re.sub(r"[\"'`]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_serving_lb(s) -> float | None:
    if not isinstance(s, str):
        return None
    m = re.match(r"\s*([\d.]+)\s*([a-zA-Z]+)", s)
    if not m:
        return None
    factor = UNIT_TO_LB.get(m.group(2).lower())
    return float(m.group(1)) * factor if factor else None


def load_menu(path: Path) -> pd.DataFrame:
    menu = pd.read_csv(path)
    menu["meal"] = menu["meal_period"].map(normalize_meal)
    menu["station_norm"] = menu["station"].map(normalize_station)
    menu["serving_lb"] = menu["serving_size"].map(parse_serving_lb)
    menu["menu_row"] = range(len(menu))
    return menu


# ---------------------------------------------------------------- recipes

def _load_real_recipes(ctx: _Ctx, menu: pd.DataFrame, keywords: pd.DataFrame):
    p = {n: REPO_ROOT / ctx.paths[n]["path"] for n in ("recipe_ingredients_master", "recipes", "recipe_ingredients", "menu_item_map")}
    for n in p:
        ctx.prov.append({"input": n, "path": ctx.paths[n]["path"], "status": "real"})
    def alias(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
        # Rename only when the contract column is absent (the mapper may ship both spellings).
        return df.rename(columns={k: v for k, v in mapping.items() if k in df.columns and v not in df.columns})

    ing = alias(pd.read_csv(p["recipe_ingredients_master"]), {"id": "ingredient_id", "default_unit": "unit"})
    recipes = pd.read_csv(p["recipes"])
    ri = alias(pd.read_csv(p["recipe_ingredients"]), {"qty_per_batch": "qty"})
    mim = pd.read_csv(p["menu_item_map"])
    ing["ingredient_id"] = ing["ingredient_id"].astype(str)
    ri["ingredient_id"] = ri["ingredient_id"].astype(str)
    ri["recipe_id"] = ri["recipe_id"].astype(str)
    recipes["recipe_id"] = recipes["recipe_id"].astype(str)
    ing["storage"] = ing["storage"].map(lambda s: STORAGE_NORMALIZE.get(str(s).lower(), "refrigerated"))
    ing["unit"] = ing["unit"].fillna("lb")
    ing["lb_per_unit"] = pd.to_numeric(ing["lb_per_unit"], errors="coerce").fillna(1.0)
    if "qty_lb" not in ri.columns:
        lbpu = ing.set_index("ingredient_id")["lb_per_unit"]
        factor = ri["unit"].str.lower().map(UNIT_TO_LB).fillna(ri["ingredient_id"].map(lbpu)).fillna(1.0)
        ri["qty_lb"] = ri["qty"].astype(float) * factor
    if "portion_lb" not in recipes.columns or recipes["portion_lb"].isna().all():
        recipes["portion_lb"] = recipes["portion_oz"].astype(float) / 16 if "portion_oz" in recipes.columns else float("nan")
    ri = ri[ri["qty_lb"] > 0]

    # Menu row -> recipe: exact per-row key if the map has one, else normalized item name, else Eatec id.
    key = ["hall", "date", "meal_period", "station", "item_name"]
    by_row: dict[tuple, str] = {}
    if all(k in mim.columns for k in key):
        for t, rid in zip(mim[key].astype(str).itertuples(index=False, name=None), mim["recipe_id"].astype(str)):
            by_row.setdefault(t, rid)
    name_col = "item_name_normalized" if "item_name_normalized" in mim.columns else None
    by_name = dict(zip(mim[name_col].astype(str), mim["recipe_id"].astype(str))) if name_col else {}
    by_eatec: dict[str, str] = {}
    for c in ("eatec_recipe_ids", "eatec_recipe_id"):
        if c in mim.columns:
            for ids, rid in zip(mim[c].astype(str), mim["recipe_id"].astype(str)):
                for e in re.split(r"[;|, ]+", ids.replace(".0", "")):
                    if e and e != "nan":
                        by_eatec.setdefault(e, rid)
    names = menu["item_name"].map(normalize_item_name)
    eatec = menu["recipe_id"].map(lambda v: str(int(v)) if pd.notna(v) else "")
    rowkeys = menu[key].astype(str).itertuples(index=False, name=None)
    menu_recipe = pd.Series([by_row.get(t) or by_name.get(n) or by_eatec.get(e) for t, n, e in zip(rowkeys, names, eatec)],
                            index=menu["menu_row"])
    valid = set(ri["recipe_id"])
    menu_recipe = menu_recipe.where(menu_recipe.isin(valid))

    unmapped = menu[menu_recipe.isna().values & menu["ingredients"].notna().values & menu["serving_lb"].notna().values]
    if len(unmapped):
        ctx.warn(f"menu_item_map: {len(unmapped)} menu rows unmapped; deriving placeholder recipes for them from menu text")
        d = menu_text_recipes.derive(unmapped, keywords)
        d.ingredients["fallback_category"] = d.ingredients["category"]
        ing = pd.concat([ing, d.ingredients[~d.ingredients["ingredient_id"].isin(ing["ingredient_id"])]], ignore_index=True)
        recipes = pd.concat([recipes, d.recipes], ignore_index=True)
        ri = pd.concat([ri, d.recipe_ingredients], ignore_index=True)
        for row, rid in zip(unmapped["menu_row"], "eatec-" + unmapped["recipe_id"].astype("Int64").astype(str)):
            if rid in set(d.recipes["recipe_id"]):
                menu_recipe.loc[row] = rid
    return ing, recipes, ri, menu_recipe


def _load_recipes(ctx: _Ctx, menu: pd.DataFrame, keywords: pd.DataFrame):
    names = ["recipe_ingredients_master", "recipes", "recipe_ingredients", "menu_item_map"]
    if all((REPO_ROOT / ctx.paths[n]["path"]).exists() for n in names):
        return _load_real_recipes(ctx, menu, keywords)
    missing = [ctx.paths[n]["path"] for n in names if not (REPO_ROOT / ctx.paths[n]["path"]).exists()]
    ctx.warn(f"recipe files missing ({', '.join(missing)}); deriving PLACEHOLDER recipes from menu_items.csv "
             "ingredient text (generator/menu_text_recipes.py)")
    for n in names:
        ctx.prov.append({"input": n, "path": ctx.paths[n]["path"], "status": "fallback",
                         "missing": ctx.paths[n]["path"], "derived_from": ctx.paths["menu_items"]["path"]})
    d = menu_text_recipes.derive(menu, keywords)
    d.ingredients["fallback_category"] = d.ingredients["category"]
    rid = "eatec-" + menu["recipe_id"].astype("Int64").astype(str)
    menu_recipe = pd.Series(rid.values, index=menu["menu_row"]).where(lambda s: s.isin(set(d.recipes["recipe_id"])))
    return d.ingredients, d.recipes, d.recipe_ingredients, menu_recipe


# ---------------------------------------------------------------- reference attributes

VENDOR_PREP = re.compile(
    r"\b(diced|dice|chopped|peeled|shredded|sliced|slices|julienned?|cut|florets?|spears?|baby|iqf|frz|frozen|"
    r"trimmed|cleaned|shaved|wedges?|chunks?|halves|segments|minced|cubed?|riced|spiral|coins|matchsticks?|"
    r"ribbons?|cored|sticks?|pre.?cut|ready|mix|blend|puree|crumbles?)\b|\d+/\d+ ?in\b", re.I)


def vendor_prep_share(menu: pd.DataFrame, rules_path: Path | None) -> dict[str, tuple[float, int]]:
    """Share of each ingredient's Eatec component lines whose name says the vendor already prepped it
    ("Onion Yellow Diced 3/8 in", "Garlic Peeled"). Trim applies only to the remainder.
    Components are matched to ingredient ids with the recipe-mapper's own ingredient_rules.csv."""
    if rules_path is None or not rules_path.exists():
        return {}
    rules = pd.read_csv(rules_path).sort_values("priority")
    compiled = [(re.compile(str(p), re.I), str(i)) for p, i in zip(rules["pattern"], rules["ingredient_id"])]
    counts: dict[str, list[int]] = {}
    cache: dict[str, str | None] = {}
    for text in menu["ingredients"].dropna():
        for part in menu_text_recipes.split_top_level(text, seps=";,"):
            if part not in cache:
                cache[part] = next((i for rx, i in compiled if rx.search(part)), None)
            iid = cache[part]
            if iid is None:
                continue
            c = counts.setdefault(iid, [0, 0])
            c[0] += 1
            c[1] += bool(VENDOR_PREP.search(part))
    return {i: (pre / n, n) for i, (n, pre) in counts.items()}


SHELF_MODES = {"refrigerated": ["refrigerator", "refrigerator_after_opening"], "dry": ["pantry", "pantry_after_opening"],
               "frozen": ["freezer"]}


def _shelf_days(row, pick: str) -> float | None:
    """FoodKeeper gives a low-high range; `midpoint` uses the research agent's shelf_life_days column."""
    lo, hi = row.get("shelf_life_days_low"), row.get("shelf_life_days_high")
    mid = row.get("shelf_life_days")
    if pick == "midpoint" and mid is not None and pd.notna(mid):
        return float(mid)
    v = hi if pick == "high" and pd.notna(hi) else lo
    v = hi if pd.isna(v) else v
    return float(v) if pd.notna(v) else None


def classify_yield(value: float, method: str, basis: str) -> tuple[float, float]:
    """Split an FBG served/AP yield into (trim_frac, cook_factor). Trim is inedible waste;
    cooking/draining/hydration changes mass but is not food waste."""
    method, basis = str(method).lower(), str(basis).lower()
    cooked = (value > 1.0 or "cooked" in method or "drained" in basis or "can_drained" in method
              or ("cooked" in basis and "ready-to-cook" not in basis))
    if cooked:
        return 0.0, value
    return max(0.0, 1.0 - value), 1.0


def _attach_prices(ctx: _Ctx, ing: pd.DataFrame) -> pd.DataFrame:
    """USD per as-purchased lb (low/mid/high) by canonical_id. Prices are AP, so they apply to
    delivered lb directly (grains/pasta/legumes are priced dry and our AP lb are dry via yields)."""
    ing = ing.copy()
    for c in ("usd_per_lb", "usd_per_lb_low", "usd_per_lb_high"):
        ing[c] = float("nan")
    ing["price_basis"], ing["price_confidence"], ing["price_source"] = "", "", ""
    spec = ctx.paths.get("ingredient_prices")
    path = REPO_ROOT / spec["path"] if spec else None
    if path is None or not path.exists():
        ctx.warn("ingredient_prices: missing; USD fields stay null")
        return ing
    ctx.prov.append({"input": "ingredient_prices", "path": spec["path"], "status": "real"})
    pr = pd.read_csv(path).drop_duplicates("canonical_id").set_index("canonical_id")
    hit = ing["ingredient_id"].isin(pr.index)
    for c in ("usd_per_lb", "usd_per_lb_low", "usd_per_lb_high"):
        src = "usd_per_lb_mid" if c == "usd_per_lb" else c
        ing.loc[hit, c] = ing.loc[hit, "ingredient_id"].map(pr[src]).astype(float)
    ing.loc[hit, "price_basis"] = ing.loc[hit, "ingredient_id"].map(pr["price_basis"]).fillna("")
    ing.loc[hit, "price_confidence"] = ing.loc[hit, "ingredient_id"].map(pr["confidence"]).fillna("")
    ing.loc[hit, "price_source"] = "reference:ingredient_prices.csv:id=" + ing.loc[hit, "ingredient_id"]
    miss = ~hit
    if miss.any():
        # Unpriced ingredients get the demand-unweighted median so totals are not silently understated.
        for c in ("usd_per_lb", "usd_per_lb_low", "usd_per_lb_high"):
            ing.loc[miss, c] = float(ing.loc[hit, c].median())
        ing.loc[miss, "price_source"] = "default:median_of_priced"
        ing.loc[miss, "price_confidence"] = "default"
        ctx.warn(f"ingredient_prices: {int(miss.sum())}/{len(ing)} ingredients unpriced; using median price")
    return ing


def _attach_loss_rates(ctx: _Ctx, ing: pd.DataFrame, loss_real: pd.DataFrame | None) -> pd.DataFrame:
    """Per-ingredient ERS LAFA retail_loss_pct (household/retail proxy; informational, not a sim input).
    Ingredients with no ERS series get the median of covered ingredients in the same recipe category."""
    ing = ing.copy()
    ing["retail_loss_pct"], ing["loss_rate_source"], ing["loss_rate_confidence"] = float("nan"), "", ""
    if loss_real is None or "canonical_id" not in loss_real.columns:
        return ing
    by_id = loss_real.dropna(subset=["canonical_id"]).drop_duplicates("canonical_id").set_index("canonical_id")
    hit = ing["ingredient_id"].isin(by_id.index)
    ing.loc[hit, "retail_loss_pct"] = ing.loc[hit, "ingredient_id"].map(by_id["retail_loss_pct"]).astype(float)
    ing.loc[hit, "loss_rate_source"] = "reference:loss_rates.csv:id=" + ing.loc[hit, "ingredient_id"]
    ing.loc[hit, "loss_rate_confidence"] = ing.loc[hit, "ingredient_id"].map(by_id.get("confidence", pd.Series(dtype=str))).fillna("")
    cat = ing["category"].fillna("other")
    medians = ing[hit].groupby(cat[hit])["retail_loss_pct"].median()
    overall = float(ing.loc[hit, "retail_loss_pct"].median())
    miss = ~hit
    ing.loc[miss, "retail_loss_pct"] = cat[miss].map(medians).fillna(overall)
    ing.loc[miss, "loss_rate_source"] = "default:category_median:" + cat[miss]
    ing.loc[miss, "loss_rate_confidence"] = "default"
    if miss.any():
        ctx.warn(f"loss_rates: {int(miss.sum())}/{len(ing)} ingredients have no ERS series; "
                 "using DEFAULT category-median retail_loss_pct (informational only)")
    return ing


def _resolve_attributes(ctx: _Ctx, ing: pd.DataFrame, keywords: pd.DataFrame, settings: dict,
                        ref_ing: pd.DataFrame | None, prep: dict) -> tuple[pd.DataFrame, dict]:
    p, fb = ctx.resolve("shelf_life")
    shelf_real = None if fb else pd.read_csv(p)
    p, fb = ctx.resolve("yields")
    yields_real = None if fb else pd.read_csv(p)
    p, fb = ctx.resolve("loss_rates")
    loss_real = None if fb else pd.read_csv(p)
    shelf_fb = read_fallback(GEN_DIR / "fallback" / "shelf_life.csv")
    yields_fb = read_fallback(GEN_DIR / "fallback" / "yields.csv")
    xwalk = read_fallback(CONFIG_DIR / "ingredient_crosswalk.csv").set_index("ingredient_id")
    pick = settings.get("shelf_life_pick", "midpoint")

    def col(row, name):
        v = row.get(name)
        return None if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "" else str(v).strip()

    out = []
    n_fb_shelf = n_fb_yield = 0
    for _, r in ing.iterrows():
        iid = r["ingredient_id"]
        xw = xwalk.loc[iid] if iid in xwalk.index else None
        fb_cat = col(r, "fallback_category") or (col(xw, "fallback_category") if xw is not None else None)
        if fb_cat is None:
            fb_cat = menu_text_recipes.classify(str(r.get("name", iid)), keywords)[0]
        ref = col(r, "reference_ingredient") or (col(xw, "reference_ingredient") if xw is not None else None)
        shelf_ref = col(r, "shelf_life_ref") or ref
        lafa_options = [col(r, "loss_rate_ref"), col(xw, "lafa_commodity") if xw is not None else None]
        storage = r["storage"]

        # shelf life: canonical_id rows first (primary storage matching this ingredient's mode), then the name join.
        sl, sl_src = None, None
        if shelf_real is not None and "canonical_id" in shelf_real.columns:
            rows = shelf_real[shelf_real["canonical_id"] == iid]
            if len(rows):
                modes = SHELF_MODES.get(storage, [STORAGE_TO_FOODKEEPER.get(storage, storage)])
                prim = rows[rows.get("primary_storage", pd.Series(0, index=rows.index)) == 1]
                cand = [prim[prim["storage"] == m] for m in modes] + [rows[rows["storage"] == m] for m in modes] + [prim, rows]
                rows = next(c for c in cand if len(c))
                v = _shelf_days(rows.iloc[0], pick)
                if v is not None:
                    sl, sl_src = v, f"reference:shelf_life.csv:id={iid}|{rows.iloc[0]['storage']}"
        if sl is None and shelf_real is not None and shelf_ref:
            rows = shelf_real[(shelf_real["ingredient"] == shelf_ref) & (shelf_real["storage"] == STORAGE_TO_FOODKEEPER.get(storage, storage))]
            if len(rows):
                v = _shelf_days(rows.iloc[0], pick)
                if v is not None:
                    sl, sl_src = v, f"reference:shelf_life.csv:{shelf_ref}|{rows.iloc[0]['storage']}"
        if sl is None:
            n_fb_shelf += 1
            fbs = "frozen" if storage == "frozen" else storage
            rows = shelf_fb[(shelf_fb["category"] == fb_cat) & (shelf_fb["storage"] == fbs)]
            if not len(rows) and storage == "frozen":
                rows = shelf_fb[(shelf_fb["category"] == "frozen")]
            if not len(rows):
                rows = shelf_fb[shelf_fb["category"] == fb_cat]
            if not len(rows):
                rows = shelf_fb[(shelf_fb["category"] == "other") & (shelf_fb["storage"] == ("dry" if storage == "dry" else "refrigerated"))]
            sl = float(rows.iloc[0]["shelf_life_days"])
            sl_src = f"fallback:shelf_life.csv:{rows.iloc[0]['category']}|{rows.iloc[0]['storage']}"

        # yield
        trim, cook, y_src = None, None, None
        if yields_real is not None and ref:
            rows = yields_real[yields_real["ingredient"] == ref]
            if len(rows) and pd.notna(rows.iloc[0]["yield_factor_ep_per_ap"]):
                y = rows.iloc[0]
                trim, cook = classify_yield(float(y["yield_factor_ep_per_ap"]), y.get("yield_method", ""), y.get("yield_basis", ""))
                y_src = f"reference:yields.csv:{ref}"
        is_produce = r.get("category") == "produce" or fb_cat in ("vegetables", "fruit", "leafy_greens", "herbs")
        # LAFA inedible share only for fresh produce: aggregate rows (e.g. Poultry) count bones the boneless SKUs lack.
        # LAFA consumer_nonedible_pct is a household-level proxy (labelled as such in summary.json).
        if trim is None and loss_real is not None and is_produce and "canonical_id" in loss_real.columns:
            rows = loss_real[loss_real["canonical_id"] == iid]
            if len(rows) and str(rows.iloc[0]["commodity"]).startswith("Fresh ") and pd.notna(rows.iloc[0]["consumer_nonedible_pct"]) \
                    and float(rows.iloc[0]["consumer_nonedible_pct"]) < 100:
                trim, cook = float(rows.iloc[0]["consumer_nonedible_pct"]) / 100, 1.0
                y_src = f"reference:loss_rates.csv:id={iid}"
        for lafa in lafa_options:
            if trim is not None or loss_real is None or not is_produce:
                break
            if not lafa or not lafa.startswith("Fresh ") or lafa in LAFA_AGGREGATES:
                continue
            rows = loss_real[loss_real["commodity"] == lafa]
            if len(rows) and pd.notna(rows.iloc[0]["consumer_nonedible_pct"]) and float(rows.iloc[0]["consumer_nonedible_pct"]) < 100:
                trim, cook = float(rows.iloc[0]["consumer_nonedible_pct"]) / 100, 1.0
                y_src = f"reference:loss_rates.csv:{lafa}"
        if trim is None:
            n_fb_yield += 1
            rows = yields_fb[yields_fb["category"] == fb_cat]
            if not len(rows):
                rows = yields_fb[yields_fb["category"] == "other"]
            trim, cook = 1.0 - float(rows.iloc[0]["yield_factor"]), 1.0
            y_src = f"fallback:yields.csv:{rows.iloc[0]['category']}"
            # Why: frozen and shelf-stable goods arrive vendor-processed; category trim is for fresh product.
            if storage in ("frozen", "dry"):
                trim = 0.0
                y_src += "|no_trim_processed"
        case_lb = None
        if ref_ing is not None and ref and "ingredient" in ref_ing.columns:
            rows = ref_ing[ref_ing["ingredient"] == ref]
            # lb_per_unit == 1 means "sold by the pound": no case pack to round to.
            if len(rows) and pd.notna(rows.iloc[0].get("lb_per_unit")) and float(rows.iloc[0]["lb_per_unit"]) > 1:
                case_lb = float(rows.iloc[0]["lb_per_unit"])
        trim_raw = trim
        share, n_lines = prep.get(iid, (0.0, 0))
        if trim > 0 and n_lines >= settings.get("vendor_prep_min_lines", 5):
            trim = trim * (1 - share)
        out.append({"ingredient_id": iid, "case_lb": case_lb, "trim_frac_raw": float(trim_raw),
                    "vendor_prep_share": float(share) if n_lines else None, "vendor_prep_lines": int(n_lines), "fallback_category": fb_cat, "reference_ingredient": ref or "",
                    "shelf_life_days": int(max(2, round(sl))), "shelf_life_source": sl_src,
                    "trim_frac": float(min(max(trim, 0.0), 0.9)), "cook_factor": float(cook), "yield_source": y_src})
    res = pd.DataFrame(out)
    res["yield_factor"] = (1 - res["trim_frac"]) * res["cook_factor"]
    if n_fb_shelf:
        ctx.warn(f"shelf_life: {n_fb_shelf}/{len(ing)} ingredients not covered by the reference table; "
                 "using PLACEHOLDER category rows from generator/fallback/shelf_life.csv")
    if n_fb_yield:
        ctx.warn(f"yields: {n_fb_yield}/{len(ing)} ingredients not covered by reference yields/loss_rates; "
                 "using PLACEHOLDER category rows from generator/fallback/yields.csv")
    keep = [c for c in ["ingredient_id", "name", "category", "storage", "unit", "lb_per_unit", "role"] if c in ing.columns]
    merged = ing[keep].merge(res, on="ingredient_id", how="left")
    if "role" not in merged.columns:
        merged["role"] = ""
    merged = _attach_loss_rates(ctx, merged, loss_real)
    merged = _attach_prices(ctx, merged)
    refs = {"shelf_life_reference": shelf_real, "yields_reference": yields_real, "loss_rates_reference": loss_real,
            "shelf_life_fallback": shelf_fb, "yields_fallback": yields_fb}
    return merged, refs


def load_inputs(paths_file: Path | None = None, settings: dict | None = None) -> Inputs:
    ctx = _Ctx(load_paths(paths_file))
    settings = settings or {}
    p, _ = ctx.resolve("menu_items")
    menu = load_menu(p)
    p, _ = ctx.resolve("halls")
    hall_attrs = pd.read_csv(p)
    p, _ = ctx.resolve("hall_volume")
    hall_volume = pd.read_csv(p)
    p, _ = ctx.resolve("waste_benchmarks")
    benchmarks = pd.read_csv(p)
    p, _ = ctx.resolve("uc_numbers")
    uc_numbers = pd.read_csv(p)
    p, _ = ctx.resolve("category_keywords")
    keywords = read_fallback(p)
    p, fb = ctx.resolve("reference_ingredients")
    ref_ing = None if fb else pd.read_csv(p)
    ing, recipes, ri, menu_recipe = _load_recipes(ctx, menu, keywords)
    ing = ing.drop_duplicates("ingredient_id").reset_index(drop=True)
    used = set(ri["ingredient_id"])
    ing = ing[ing["ingredient_id"].isin(used)].reset_index(drop=True)
    rules = ctx.paths.get("ingredient_rules")
    rules_path = REPO_ROOT / rules["path"] if rules else None
    prep = vendor_prep_share(menu, rules_path) if rules_path and rules_path.exists() else {}
    if rules_path and not rules_path.exists():
        ctx.warn(f"ingredient_rules: {rules['path']} missing; trim not adjusted for vendor-prepped lines")
    ing, refs = _resolve_attributes(ctx, ing, keywords, settings, ref_ing, prep)
    counts = {"menu_items": len(menu), "recipe_ingredients_master": len(ing), "recipes": len(recipes),
              "recipe_ingredients": len(ri), "menu_item_map": int(menu_recipe.notna().sum())}
    for row in ctx.prov:
        if row["input"] in counts:
            row["rows"] = int(counts[row["input"]])
    return Inputs(menu=menu, hall_attrs=hall_attrs, hall_volume=hall_volume, benchmarks=benchmarks,
                  uc_numbers=uc_numbers, ingredients=ing, recipes=recipes, recipe_ingredients=ri,
                  menu_recipe=menu_recipe, provenance=ctx.prov, warnings=ctx.warnings, reference_files=refs)


def benchmark_range(benchmarks: pd.DataFrame, check: dict, point_tolerance_pct: float) -> dict:
    """Union range of the listed benchmark rows after unit conversion. If every listed row is a point
    estimate (low == high), the points are widened by +/- point_tolerance_pct so the check can pass/fail."""
    lows, highs, rows = [], [], []
    picked = [r for m in check["metrics"] for _, r in benchmarks[benchmarks["metric"] == m].iterrows()]
    any_ranged = any(float(r["value_low"]) != float(r["value_high"]) for r in picked)
    for metric, factor in check["metrics"].items():
        for _, r in benchmarks[benchmarks["metric"] == metric].iterrows():
            lo, hi = float(r["value_low"]) * factor, float(r["value_high"]) * factor
            point = lo == hi
            # Why: only widen when no source gives a real range; otherwise points just join the union.
            if point and not any_ranged:
                lo, hi = lo * (1 - point_tolerance_pct / 100), hi * (1 + point_tolerance_pct / 100)
            lows.append(lo)
            highs.append(hi)
            rows.append({"metric": metric, "value_low": float(r["value_low"]), "value_high": float(r["value_high"]),
                         "unit": r["unit"], "context": r.get("context"), "source_org": r["source_org"],
                         "source_url": r["source_url"], "year": r.get("year"), "point_estimate": point})
    if not rows:
        return {"low": None, "high": None, "sources": []}
    return {"low": min(lows), "high": max(highs), "sources": rows}
