"""With every in-progress input missing, the generator still runs on labeled placeholders and warns."""

import yaml

from conftest import REPO
from generator.loaders import load_inputs
from generator.outputs import run_scenario

SWAPPABLE = ["shelf_life", "loss_rates", "yields", "reference_ingredients", "recipe_ingredients_master",
             "recipes", "recipe_ingredients", "menu_item_map", "ingredient_rules"]


def test_runs_on_fallbacks_and_balances(tmp_path):
    with open(REPO / "generator" / "config" / "paths.yaml") as f:
        paths = yaml.safe_load(f)
    for k in SWAPPABLE:
        paths[k]["path"] = f"does/not/exist/{k}.csv"
    pf = tmp_path / "paths.yaml"
    pf.write_text(yaml.safe_dump(paths))
    inp = load_inputs(pf)
    statuses = {p["input"]: p["status"] for p in inp.provenance}
    assert all(statuses[k] == "fallback" for k in SWAPPABLE if k != "ingredient_rules")
    assert any("PLACEHOLDER" in w for w in inp.warnings)
    res = run_scenario("normal_week", tmp_path / "out", inputs=inp)
    assert res["summary"]["mass_balance"]["pass"]
    assert len(res["frames"]["production"]) > 0
