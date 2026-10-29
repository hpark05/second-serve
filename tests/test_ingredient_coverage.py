"""Every ingredient referenced by a simulated recipe has a shelf-life row and a yield row, and the
row each value cites actually exists in the file it names (reference file or labeled fallback)."""

import pandas as pd
import pytest

from conftest import REPO, SCENARIOS

FILES = {
    ("reference", "shelf_life.csv"): REPO / "data/raw/reference/shelf_life.csv",
    ("reference", "yields.csv"): REPO / "data/raw/reference/yields.csv",
    ("reference", "loss_rates.csv"): REPO / "data/raw/reference/loss_rates.csv",
    ("fallback", "shelf_life.csv"): REPO / "generator/fallback/shelf_life.csv",
    ("fallback", "yields.csv"): REPO / "generator/fallback/yields.csv",
}


def _load(kind, name):
    return pd.read_csv(FILES[(kind, name)], comment="#" if kind == "fallback" else None)


def _row_exists(source: str) -> bool:
    kind, name, key = source.split(":", 2)
    df = _load(kind, name)
    parts = key.split("|")
    if name == "shelf_life.csv":
        if parts[0].startswith("id="):
            return bool(((df["canonical_id"] == parts[0][3:]) & (df["storage"] == parts[1])).any())
        col = "ingredient" if kind == "reference" else "category"
        return bool(((df[col] == parts[0]) & (df["storage"] == parts[1])).any())
    if name == "yields.csv":
        col = "ingredient" if kind == "reference" else "category"
        return bool((df[col] == parts[0]).any())
    if name == "loss_rates.csv":
        if parts[0].startswith("id="):
            return bool((df["canonical_id"] == parts[0][3:]).any())
        return bool((df["commodity"] == parts[0]).any())
    return False


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_every_referenced_ingredient_has_shelf_life_and_yield(outputs, scenario):
    out = outputs[scenario]
    used_recipes = set(out["menu_items"].recipe_id)
    ri = out["recipe_ingredients"]
    used = set(ri[ri.recipe_id.isin(used_recipes)].ingredient_id)
    ing = out["ingredients"].set_index("ingredient_id")
    missing = used - set(ing.index)
    assert not missing, f"ingredients missing from ingredients.csv: {sorted(missing)[:5]}"
    for iid in sorted(used):
        row = ing.loc[iid]
        assert pd.notna(row.shelf_life_days) and row.shelf_life_days > 0, iid
        assert pd.notna(row.yield_factor) and row.yield_factor > 0, iid
        assert _row_exists(row.shelf_life_source), f"{iid}: cited shelf-life row not found ({row.shelf_life_source})"
        assert _row_exists(row.yield_source), f"{iid}: cited yield row not found ({row.yield_source})"


MIN_REFERENCE_SHELF_LIFE_COVERAGE_PCT = 95.0


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_shelf_life_reference_coverage_by_purchased_lb(outputs, scenario):
    """Share of purchased lb whose shelf life comes from the reference table rather than a placeholder.
    Category defaults fill the gap until research completes shelf_life.csv; fail only below 95%."""
    out = outputs[scenario]
    bought = out["deliveries"].groupby("ingredient_id").qty_lb.sum()
    src = out["ingredients"].set_index("ingredient_id").shelf_life_source.reindex(bought.index)
    pct = 100 * bought[src.str.startswith("reference:")].sum() / bought.sum()
    print(f"{scenario}: shelf-life reference coverage {pct:.1f}% of purchased lb")
    assert pct >= MIN_REFERENCE_SHELF_LIFE_COVERAGE_PCT, f"reference shelf-life coverage {pct:.1f}% < 95%"
