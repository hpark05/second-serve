"""PLACEHOLDER recipe derivation from Eatec ingredient text in menu_items.csv.

Used only when data/recipes/* (recipe-mapper output) is missing or leaves menu rows unmapped.
Eatec lists a menu item's ingredients in recipe-line order but gives no quantities, so the
split of a serving's weight across ingredients is a heuristic (rank-decay weights, seasonings
down-weighted). Every derived row carries source="derived_from_menu_text"."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

PORTIONS_PER_BATCH = 50          # placeholder batch size; only the per-portion ratio matters to the sim
RANK_DECAY = 0.6                 # weight of ingredient k = RANK_DECAY ** k
MINOR_CATEGORIES = {"seasonings", "oils_fats", "herbs", "sweeteners"}
MINOR_WEIGHT = 0.1
SOURCE = "derived_from_menu_text"


@dataclass
class Derived:
    ingredients: pd.DataFrame
    recipes: pd.DataFrame
    recipe_ingredients: pd.DataFrame
    menu_item_map: pd.DataFrame


def split_top_level(text: str, seps: str = ";") -> list[str]:
    """Split on separators outside parentheses (sub-ingredient lists can contain ';')."""
    out, depth, cur = [], 0, []
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch in seps and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    names = []
    for part in out:
        name = re.sub(r"\s*[\(\[].*$", "", part).strip().strip(".").strip()
        name = re.sub(r"\s+", " ", name)
        if name:
            names.append(name)
    return names


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _rules(keywords: pd.DataFrame) -> tuple:
    return tuple((str(r.keyword).lower(), r.category, r.storage) for r in keywords.itertuples())


@lru_cache(maxsize=None)
def _classify_cached(name: str, rules: tuple) -> tuple[str, str]:
    low = name.lower()

    def hit(kw: str, anchored: bool) -> bool:
        pat = (r"^" if anchored else r"\b") + re.escape(kw) + r"(s|es)?\b"
        return re.search(pat, low) is not None

    frozen = any(cat == "frozen" and hit(kw, False) for kw, cat, _ in rules)
    category, storage = None, None
    for anchored in (True, False):
        for kw, cat, sto in rules:
            if cat != "frozen" and hit(kw, anchored):
                category, storage = cat, sto
                break
        if category:
            break
    if category is None:
        category, storage = ("frozen", "frozen") if frozen else ("other", "refrigerated")
    if frozen:
        storage = "frozen"
    return category, storage


def classify(name: str, keywords: pd.DataFrame) -> tuple[str, str]:
    return _classify_cached(name, _rules(keywords))


def derive(menu: pd.DataFrame, keywords: pd.DataFrame) -> Derived:
    rows = menu[menu["ingredients"].notna() & menu["serving_lb"].notna()].copy()
    rows["recipe_id"] = "eatec-" + rows["recipe_id"].astype("Int64").astype(str)
    ing_rows: dict[str, dict] = {}
    rec_rows, ri_rows = [], []
    for rid, grp in rows.groupby("recipe_id", sort=True):
        first = grp.iloc[0]
        names = []
        for n in split_top_level(first["ingredients"]):
            if n not in names:
                names.append(n)
        comps = []
        for k, n in enumerate(names):
            cat, sto = classify(n, keywords)
            if cat == "water":
                continue
            iid = slug(n)
            ing_rows.setdefault(iid, {"ingredient_id": iid, "name": n, "category": cat, "storage": sto,
                                      "unit": "lb", "lb_per_unit": 1.0, "source": SOURCE})
            comps.append((iid, cat, RANK_DECAY ** k))
        if not comps:
            continue
        has_major = any(c not in MINOR_CATEGORIES for _, c, _ in comps)
        weights = [w * (MINOR_WEIGHT if has_major and c in MINOR_CATEGORIES else 1.0) for _, c, w in comps]
        total = sum(weights)
        portion_lb = float(grp["serving_lb"].median())
        rec_rows.append({"recipe_id": rid, "name": first["item_name"], "portions_per_batch": PORTIONS_PER_BATCH,
                         "portion_lb": portion_lb, "source": SOURCE})
        for (iid, _, _), w in zip(comps, weights):
            qty = portion_lb * PORTIONS_PER_BATCH * w / total
            ri_rows.append({"recipe_id": rid, "ingredient_id": iid, "qty": qty, "unit": "lb", "qty_lb": qty,
                            "source": SOURCE})
    mim = rows[["hall", "date", "meal_period", "station", "item_name", "recipe_id"]].copy()
    mim["source"] = SOURCE
    mim = mim[mim["recipe_id"].isin({r["recipe_id"] for r in rec_rows})]
    return Derived(
        ingredients=pd.DataFrame(sorted(ing_rows.values(), key=lambda r: r["ingredient_id"])),
        recipes=pd.DataFrame(rec_rows),
        recipe_ingredients=pd.DataFrame(ri_rows),
        menu_item_map=mim.drop_duplicates(["hall", "date", "meal_period", "station", "item_name"]).reset_index(drop=True),
    )
