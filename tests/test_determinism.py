"""Same seed -> byte-identical output; different seed -> different output."""

import filecmp

from generator.outputs import run_scenario

FILES = ["diners.csv", "menu_items.csv", "production.csv", "waste_events.csv", "inventory_lots.csv",
         "deliveries.csv", "transfers.csv", "mass_balance.csv", "summary.json", "bundle.json"]


def test_same_seed_identical(tmp_path, inputs, scenario_dirs):
    again = tmp_path / "again"
    run_scenario("normal_week", again, inputs=inputs)
    for f in FILES:
        assert filecmp.cmp(scenario_dirs["normal_week"] / f, again / f, shallow=False), f"{f} differs between runs"


def test_different_seed_differs(tmp_path, inputs, scenario_dirs):
    other = tmp_path / "other"
    run_scenario("normal_week", other, overrides={"seed": 1}, inputs=inputs)
    assert not filecmp.cmp(scenario_dirs["normal_week"] / "production.csv", other / "production.csv", shallow=False)
