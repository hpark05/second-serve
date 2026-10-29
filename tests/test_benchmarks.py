"""Simulated aggregates for the scraped week fall inside published ranges. Ranges come from
data/raw/benchmarks/waste_benchmarks.csv using the metric lists in generator/config/base.yaml (checks)."""

import pytest


@pytest.mark.parametrize("scenario", ["normal_week"])
def test_pre_consumer_pct_of_purchased_within_benchmark(outputs, base_cfg, benchmarks, scenario):
    from conftest import benchmark_union
    out = outputs[scenario]
    w = out["waste_events"]
    pre_lb = w[w.kind.isin(["pre_consumer", "expired"])].lb.sum()
    purchased = out["deliveries"].qty_lb.sum()
    pct = 100 * pre_lb / purchased
    lo, hi = benchmark_union(benchmarks, base_cfg["checks"]["pre_consumer_pct_of_purchased"]["metrics"])
    assert lo <= pct <= hi, f"pre-consumer {pct:.2f}% of purchased outside [{lo}, {hi}]"


@pytest.mark.parametrize("scenario", ["normal_week"])
def test_plate_waste_lb_per_cover_within_benchmark(outputs, base_cfg, benchmarks, scenario):
    from conftest import benchmark_union
    out = outputs[scenario]
    w = out["waste_events"]
    covers = out["diners"].diners_actual.sum()
    per_cover = w[w.kind == "post_consumer"].lb.sum() / covers
    lo, hi = benchmark_union(benchmarks, base_cfg["checks"]["plate_waste_lb_per_cover"]["metrics"])
    assert lo <= per_cover <= hi, f"plate waste {per_cover:.3f} lb/cover outside [{lo:.3f}, {hi:.3f}]"


def test_plate_waste_prior_is_not_the_checked_row(base_cfg):
    # Guard against circularity: the plate-waste prior must come from a different row than the check.
    assert base_cfg["plate_waste"]["prior_metric"] not in base_cfg["checks"]["plate_waste_lb_per_cover"]["metrics"]
