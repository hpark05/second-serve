"""Shared fixtures: each scenario runs once per session into a temp dir, so tests never depend on
whatever happens to be in data/synthetic/."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from generator.loaders import load_inputs  # noqa: E402
from generator.outputs import run_scenario  # noqa: E402

SCENARIOS = ["normal_week", "game_day", "finals_week", "holiday_short_week"]
CSV_NAMES = ["diners", "menu_items", "production", "waste_events", "inventory_lots", "deliveries", "transfers",
             "halls", "ingredients", "recipe_ingredients"]


@pytest.fixture(scope="session")
def inputs():
    return load_inputs()


def _read(out: Path) -> dict[str, pd.DataFrame]:
    return {n: pd.read_csv(out / f"{n}.csv", keep_default_na=False, na_values=[""]) for n in CSV_NAMES}


@pytest.fixture(scope="session")
def scenario_dirs(tmp_path_factory, inputs):
    dirs = {}
    for s in SCENARIOS:
        out = tmp_path_factory.mktemp(s)
        run_scenario(s, out, inputs=inputs)
        dirs[s] = out
    out = tmp_path_factory.mktemp("normal_week_transfers")
    run_scenario("normal_week", out, overrides={"transfers": {"execute": True}}, inputs=inputs)
    dirs["normal_week_transfers"] = out
    return dirs


@pytest.fixture(scope="session")
def outputs(scenario_dirs):
    return {k: _read(v) for k, v in scenario_dirs.items()}


@pytest.fixture(scope="session")
def base_cfg():
    with open(REPO / "generator" / "config" / "base.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def benchmarks():
    return pd.read_csv(REPO / "data" / "raw" / "benchmarks" / "waste_benchmarks.csv")


def benchmark_union(benchmarks: pd.DataFrame, metrics: dict[str, float]) -> tuple[float, float]:
    """Union of value_low..value_high across the named rows, unit-converted. Read straight from the CSV."""
    rows = benchmarks[benchmarks["metric"].isin(list(metrics))]
    assert len(rows), f"no benchmark rows for {list(metrics)}"
    lo = min(float(r.value_low) * metrics[r.metric] for r in rows.itertuples())
    hi = max(float(r.value_high) * metrics[r.metric] for r in rows.itertuples())
    return lo, hi
