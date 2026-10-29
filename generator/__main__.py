"""CLI: python -m generator --scenario normal_week --out data/synthetic/normal_week"""

from __future__ import annotations

import argparse
import logging
import sys

from .outputs import run_scenario


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="generator", description="Second Serve synthetic data generator")
    ap.add_argument("--scenario", required=True, help="scenario name in generator/config/ or a YAML path")
    ap.add_argument("--out", help="output directory (default data/synthetic/<scenario>)")
    ap.add_argument("--seed", type=int, help="override the scenario seed")
    ap.add_argument("--execute-transfers", action="store_true", help="move proposed transfers instead of only proposing")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    overrides = {}
    if args.seed is not None:
        overrides["seed"] = args.seed
    if args.execute_transfers:
        overrides["transfers"] = {"execute": True}
    out = args.out or f"data/synthetic/{args.scenario}"
    res = run_scenario(args.scenario, out, overrides)
    s = res["summary"]
    h = s["headline"]
    print(f"{s['scenario']}: covers={h['covers']:.0f} purchased={h['purchased_lb']:.0f} lb "
          f"pre={h['pre_consumer_pct_of_purchased']:.2f}% plate={h['plate_waste_lb_per_cover']:.3f} lb/cover "
          f"mass_balance_max={s['mass_balance']['max_abs_imbalance_pct']:.4f}% -> {res['out_dir']}")
    for c in s["checks"]:
        lo = "-" if c["range_low"] is None else f"{c['range_low']:.3f}"
        hi = "-" if c["range_high"] is None else f"{c['range_high']:.3f}"
        print(f"  {'PASS' if c['pass'] else 'FAIL'} {c['check']}: {c['value']:.3f} in [{lo}, {hi}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
