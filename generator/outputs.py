"""Scenario runner: config merge, CSV/JSON outputs, mass-balance ledger, benchmark summary."""

from __future__ import annotations

import copy
import datetime as dt
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import recommendations
from .loaders import CONFIG_DIR, REPO_ROOT, Inputs, benchmark_range, load_inputs, load_paths
from .sim import Simulation, as_date

log = logging.getLogger("generator")
SCHEMA_VERSION = "1.0"


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def load_config(scenario: str) -> dict:
    with open(CONFIG_DIR / "base.yaml") as f:
        base = yaml.safe_load(f)
    path = Path(scenario)
    if not path.exists():
        path = CONFIG_DIR / f"{scenario}.yaml"
    with open(path) as f:
        return deep_merge(base, yaml.safe_load(f))


# ------------------------------------------------------------ mass balance

def mass_balance(frames: dict[str, pd.DataFrame], start: dt.date, end: dt.date) -> pd.DataFrame:
    """Per hall-week, in as-purchased-equivalent lb:
    received + opening = served + recovered + closing + waste + transferred_out - transferred_in."""
    inv, dlv, prod = frames["inventory"], frames["deliveries"], frames["production"]
    waste, tr = frames["waste_events"], frames["transfers"]
    rows = []
    hall_ids = sorted(set(prod["hall_id"]) | set(inv["hall_id"]))
    d = start
    weeks = []
    while d <= end:
        wk_end = min(end, d + dt.timedelta(days=6 - d.weekday()))
        weeks.append((d, wk_end))
        d = wk_end + dt.timedelta(days=1)
    for ws, we in weeks:
        dates = {x.isoformat() for x in pd.date_range(ws, we).date}
        open_day = (ws - dt.timedelta(days=1)).isoformat()
        for h in hall_ids:
            opening = inv[(inv["hall_id"] == h) & (inv["snapshot_date"] == open_day)]["qty_lb"].sum()
            closing = inv[(inv["hall_id"] == h) & (inv["snapshot_date"] == we.isoformat())]["qty_lb"].sum()
            received = dlv[(dlv["hall_id"] == h) & dlv["date"].isin(dates)]["qty_lb"].sum()
            p = prod[(prod["hall_id"] == h) & prod["date"].isin(dates)]
            w = waste[(waste["hall_id"] == h) & waste["date"].isin(dates) & waste["kind"].isin(["pre_consumer", "expired"])]
            done = tr[tr["status"] == "completed"] if len(tr) else tr
            t_out = done[(done["from_hall"] == h) & done["date"].isin(dates)]["qty_lb"].sum() if len(done) else 0.0
            t_in = done[(done["to_hall"] == h) & done["date"].isin(dates)]["qty_lb"].sum() if len(done) else 0.0
            lhs = received + opening + t_in
            rhs = p["served_lb_ap"].sum() + p["recovered_lb_ap"].sum() + closing + w["lb_ap"].sum() + t_out
            rows.append({"hall_id": h, "week_start": ws.isoformat(), "week_end": we.isoformat(),
                         "opening_lb": opening, "received_lb": received, "transferred_in_lb": t_in,
                         "served_lb": p["served_lb_ap"].sum(), "recovered_lb": p["recovered_lb_ap"].sum(),
                         "waste_lb": w["lb_ap"].sum(), "transferred_out_lb": t_out, "closing_lb": closing,
                         "imbalance_lb": lhs - rhs, "imbalance_pct": 100 * (lhs - rhs) / lhs if lhs else 0.0})
    return pd.DataFrame(rows)


# ------------------------------------------------------------ summary

def aggregates(frames: dict[str, pd.DataFrame], hall_id: str | None = None) -> dict:
    def f(df):
        return df[df["hall_id"] == hall_id] if hall_id is not None and len(df) else df
    din, dlv, prod, waste = f(frames["diners"]), f(frames["deliveries"]), f(frames["production"]), f(frames["waste_events"])
    covers = float(din["diners_actual"].sum())
    purchased = float(dlv["qty_lb"].sum())
    pre = waste[waste["kind"].isin(["pre_consumer", "expired"])]
    post = waste[waste["kind"] == "post_consumer"]
    by_reason = pre.groupby("reason")["lb"].sum().to_dict()
    pre_lb, post_lb = float(pre["lb"].sum()), float(post["lb"].sum())
    days = frames["diners"]["date"].nunique()
    return {
        "covers": covers, "days": int(days), "purchased_lb": purchased,
        "emergency_purchased_lb": float(dlv[dlv["kind"] == "emergency"]["qty_lb"].sum()),
        "served_lb": float(prod["served_lb"].sum()),
        "served_lb_per_cover": float(prod["served_lb"].sum()) / covers if covers else None,
        "pre_consumer_lb": pre_lb, "post_consumer_lb": post_lb,
        "trim_lb": float(by_reason.get("trim", 0.0)), "overproduction_lb": float(by_reason.get("overproduction", 0.0)),
        "expired_lb": float(by_reason.get("expired_in_storage", 0.0)),
        "donated_lb": float(prod["donated_lb"].sum()), "repurposed_lb": float(prod["repurposed_lb"].sum()),
        "portions_prepared": int(prod["portions_prepared"].sum()), "portions_short": int(prod["portions_short"].sum()),
        "metrics": {
            "pre_consumer_pct_of_purchased": 100 * pre_lb / purchased if purchased else None,
            "plate_waste_lb_per_cover": post_lb / covers if covers else None,
            "total_waste_pct_of_purchased": 100 * (pre_lb + post_lb) / purchased if purchased else None,
            "total_waste_lb_per_meal": (pre_lb + post_lb) / covers if covers else None,
            "overproduction_share_of_pre_consumer": 100 * by_reason.get("overproduction", 0.0) / pre_lb if pre_lb else None,
            "pre_consumer_lb_per_cover": pre_lb / covers if covers else None,
        },
    }


def build_summary(cfg: dict, inputs: Inputs, frames: dict, mb: pd.DataFrame) -> dict:
    checks_cfg = {k: v for k, v in cfg["checks"].items() if isinstance(v, dict)}
    tol = cfg["checks"].get("point_tolerance_pct", 50)
    overall = aggregates(frames)
    checks = []
    for key, spec in checks_cfg.items():
        rng = benchmark_range(inputs.benchmarks, spec, tol)
        val = overall["metrics"].get(key)
        ok = None if rng["low"] is None or val is None else bool(rng["low"] <= val <= rng["high"])
        checks.append({"check": key, "label": spec["label"], "unit": spec["unit"], "value": val,
                       "range_low": rng["low"], "range_high": rng["high"], "pass": ok, "sources": rng["sources"]})
    halls = {h: aggregates(frames, h) for h in sorted(frames["diners"]["hall_id"].unique())}
    uc = inputs.uc_numbers
    don = uc[uc["metric"] == "food_donated_per_semester"]
    weeks = overall["days"] / 7
    donation_ref = None
    if len(don):
        per_week = float(don["value"].iloc[0]) / cfg["leftover"]["semester_weeks"]
        donation_ref = {"sim_donated_lb_per_week": overall["donated_lb"] / weeks if weeks else None,
                        "cal_dining_reported_lb_per_week": per_week,
                        "basis": f"uc_numbers.csv food_donated_per_semester ({don['value'].iloc[0]} {don['unit'].iloc[0]}) "
                                 f"/ {cfg['leftover']['semester_weeks']} weeks (ASSUMPTION); covers all of Cal Dining",
                        "source_url": don["source_url"].iloc[0]}
    tr = frames["transfers"]
    return {
        "schema_version": SCHEMA_VERSION, "scenario": cfg["name"], "description": cfg.get("description"),
        "seed": cfg["seed"], "start_date": str(cfg["start_date"]), "end_date": str(cfg["end_date"]),
        "headline": {k: overall[k] for k in ("covers", "purchased_lb", "served_lb", "pre_consumer_lb", "post_consumer_lb",
                                              "expired_lb", "donated_lb", "portions_short")} | overall["metrics"],
        "checks": checks,
        "all_checks_pass": all(c["pass"] for c in checks if c["pass"] is not None),
        "mass_balance": {"max_abs_imbalance_pct": float(mb["imbalance_pct"].abs().max()) if len(mb) else 0.0,
                         "tolerance_pct": 1.0,
                         "pass": bool((mb["imbalance_pct"].abs() <= 1.0).all()) if len(mb) else True},
        "transfers": {"count": int(len(tr)), "lb": float(tr["qty_lb"].sum()) if len(tr) else 0.0,
                      "status": sorted(tr["status"].unique().tolist()) if len(tr) else []},
        "donation_reference": donation_ref,
        "overall": overall, "by_hall": halls,
        "inputs": inputs.provenance, "warnings": inputs.warnings,
    }


# ------------------------------------------------------------ factors

def economic_factors(inputs: Inputs, cfg: dict) -> dict:
    """App conversion factors, each traced to a row in data/raw."""
    fcfg = cfg.get("factors", {})
    out: dict = {}
    b = inputs.benchmarks
    row = b[b["metric"] == fcfg.get("lb_per_meal_metric", "food_recovery_lb_per_meal")]
    out["lb_per_meal"] = {"value": float(row["value_low"].iloc[0]) if len(row) else None,
                          "basis": "waste_benchmarks.csv food_recovery_lb_per_meal (Food Recovery Network FY19)",
                          "source_url": row["source_url"].iloc[0] if len(row) else None}
    m = inputs.menu.dropna(subset=["carbon_kg_co2", "serving_lb"])
    m = m[m["serving_lb"] <= cfg["production"]["max_serving_lb"]]
    co2 = float(m["carbon_kg_co2"].sum()) * 2.20462 / float(m["serving_lb"].sum()) if len(m) else None
    out["co2e_lb_per_lb"] = {"value": co2,
                             "basis": f"menu_items.csv Eatec carbon_kg_co2 per serving / serving weight, {len(m)} rows (kg->lb)",
                             "source_url": "data/raw/menus/menu_items.csv"}
    uc, vol = inputs.uc_numbers, inputs.hall_volume
    cost = uc[uc["metric"] == "food_cost_avoided"]
    tons = vol[vol["metric"] == "pre_consumer_waste_reduction"]
    usd = None
    if len(cost) and len(tons):
        usd = float(cost["value"].iloc[0]) / (float(pd.to_numeric(tons["value"]).iloc[0]) * 2000)
    out["blended_usd_per_lb_reference"] = {"value": usd,
                         "basis": "REFERENCE ONLY (superseded by data/raw/prices/ingredient_prices.csv). Blended proxy: uc_numbers food_cost_avoided (USD/yr) / hall_volume pre_consumer_waste_reduction "
                                  "(tons/yr x 2000), same StopWaste Cal Dining case study (c. 2012-13 dollars). Not an ingredient price.",
                         "source_url": cost["source_url"].iloc[0] if len(cost) else None}
    return out


BANDS = (("mid", "usd_per_lb", "usd_per_portion"), ("low", "usd_per_lb_low", "usd_per_portion_low"),
         ("high", "usd_per_lb_high", "usd_per_portion_high"))


STOCK_KINDS = ("use_first", "transfer", "buy_less")


def cost_summary(inputs: Inputs, frames: dict, recs: list[dict]) -> dict:
    """Dollar figures at mid prices with low/high ranges. Prices are USD per as-purchased lb (Sep 2026)."""
    ing = inputs.ingredients.set_index("ingredient_id")
    dlv, prod, w = frames["deliveries"], frames["production"], frames["waste_events"]
    covers = float(frames["diners"]["diners_actual"].sum()) or 1.0
    pp = prod.set_index("menu_item_id")

    def band(fn) -> dict:
        return {b: round(float(fn(pc, ppc)), 2) for b, pc, ppc in BANDS}

    def by_ing(df, pc):
        return (df["lb"] if "lb" in df else df["qty_lb"]) .mul(df["ingredient_id"].map(ing[pc])).sum()

    trim, exp = w[w["reason"] == "trim"], w[w["kind"] == "expired"]
    over, plate = w[w["reason"] == "overproduction"], w[w["reason"] == "plate_waste"]

    def items(df, ppc):
        rows = pp.loc[df["menu_item_id"]]
        return (df["lb"].values / rows["serving_lb"].values * rows[ppc].values).sum()

    purchased = band(lambda pc, ppc: by_ing(dlv, pc))
    prepared = band(lambda pc, ppc: (prod["portions_prepared"] * prod[ppc]).sum())

    def rec_usd(r, pc, ppc):
        if r["kind"] == "recover":
            return 0.0
        if r["kind"] == "adjust_prep":
            return r["est_lb_saved"] / r["inputs"]["serving_lb"] * r["inputs"][ppc]
        iid = r["target"].split("->")[0]
        return r["est_lb_saved"] * float(ing.loc[iid, pc])

    sanity = {}
    sp = REPO_ROOT / load_paths()["price_sanity"]["path"] if "price_sanity" in load_paths() else None
    if sp is not None and sp.exists():
        sanity = json.loads(sp.read_text())
    per_meal = {k: round(v / covers, 3) for k, v in purchased.items()}
    implied = sanity.get("implied_food_cost_per_meal_usd")
    uf = sanity.get("benchmark", {}).get("uf_plate_cost_inflated_usd")
    priced = ing["price_source"].str.startswith("reference:")
    return {
        "price_basis": "USD per as-purchased lb, Sep 2026 dollars, data/raw/prices/ingredient_prices.csv. "
                       "Headline = mid; low/high = per-ingredient price range.",
        "priced_ingredients": {"priced": int(priced.sum()), "of": int(len(ing)),
                               "confidence": ing["price_confidence"].value_counts().to_dict()},
        "purchased_usd": purchased,
        "prepared_food_usd": prepared,
        "food_cost_per_meal": {
            **per_meal,
            "basis": "purchased_usd / covers (ingredient cost only; excludes labor, packaging, overhead)",
            "comparison": {
                "sources_prices_implied_usd": implied,
                "uf_aycte_plate_cost_2026_usd": uf,
                "sim_vs_implied_mid": round(per_meal["mid"] / implied["mid"], 3) if implied else None,
                "sim_vs_uf": round(per_meal["mid"] / uf, 3) if uf else None,
                "source": "data/raw/prices/sanity_food_cost_per_meal.json; docs/sources-prices.md",
            },
        },
        "waste_usd": {
            "pre_consumer_trim": band(lambda pc, ppc: by_ing(trim, pc)),
            "pre_consumer_overproduction": band(lambda pc, ppc: items(over, ppc)),
            "expired": band(lambda pc, ppc: by_ing(exp, pc)),
            "post_consumer_plate": band(lambda pc, ppc: items(plate, ppc)),
        },
        "recommendations_est_usd_saved": {
            "by_kind_mid": {k: round(sum(rec_usd(r, "usd_per_lb", "usd_per_portion") for r in recs if r["kind"] == k), 2)
                            for k in sorted({r["kind"] for r in recs})},
            "sum_of_candidates": band(lambda pc, ppc: sum(rec_usd(r, pc, ppc) for r in recs)),
            # Why: use_first, transfer and buy_less can all target the same expiring stock; cap them at what actually expired.
            "deduplicated": band(lambda pc, ppc: sum(rec_usd(r, pc, ppc) for r in recs if r["kind"] == "adjust_prep")
                                 + min(by_ing(exp, pc), sum(rec_usd(r, pc, ppc) for r in recs if r["kind"] in STOCK_KINDS))),
            "note": "Headline = deduplicated mid. sum_of_candidates double-counts stock that several kinds target.",
        },
    }


def fallback_counts(inputs: Inputs, frames: dict) -> dict:
    """How many ingredients (and what share of purchased lb) rely on placeholders or defaults."""
    ing = inputs.ingredients
    bought = frames["deliveries"].groupby("ingredient_id")["qty_lb"].sum() if len(frames["deliveries"]) else pd.Series(dtype=float)
    total = float(bought.sum()) or 1.0

    def block(mask: pd.Series, note: str) -> dict:
        ids = sorted(ing.loc[mask, "ingredient_id"])
        return {"ingredients": len(ids), "of": int(len(ing)), "pct_purchased_lb": round(100 * float(bought.reindex(ids).fillna(0).sum()) / total, 1),
                "ids": ids, "note": note}

    out = {"shelf_life_placeholder": block(~ing["shelf_life_source"].str.startswith("reference:"),
                                           "generator/fallback/shelf_life.csv category rows"),
           "yield_placeholder": block(~ing["yield_source"].str.startswith("reference:"),
                                      "generator/fallback/yields.csv category rows (trim 0 for frozen/dry)")}
    if "loss_rate_source" in ing.columns:
        d = ing[ing["loss_rate_source"].str.startswith("default:")]
        out["loss_rate_default"] = block(ing["loss_rate_source"].str.startswith("default:"),
                                         "DEFAULT: no ERS LAFA series; retail_loss_pct = median of covered ingredients in the same recipe category. "
                                         "Household/retail proxy, informational only (not a sim input).")
        out["loss_rate_default"]["defaults_by_category"] = {c: round(float(v), 2) for c, v in d.groupby("category")["retail_loss_pct"].first().items()}
    return out


REFERENCE_NOTES = {
    "loss_rates.csv": "USDA ERS LAFA loss rates are national retail/household assumptions; used only as a household-level "
                      "proxy for the inedible (trim) share of fresh produce lacking an FBG yield. Not an institutional kitchen rate.",
    "shelf_life.csv": "FSIS FoodKeeper consumer storage guidance (midpoint of low-high); conservative for commercial cold chain.",
    "yields.csv": "USDA Food Buying Guide served/as-purchased yields, applied once (recipe qty is cooked edible weight).",
}


# ------------------------------------------------------------ bundle

def _records(df: pd.DataFrame, cols: list[str] | None = None, ndigits: int = 3) -> list[dict]:
    if df is None or not len(df):
        return []
    d = df[cols] if cols else df
    d = d.copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].round(ndigits)
    d = d.astype(object).where(pd.notna(d), None)
    return d.to_dict(orient="records")


def _waste_list(waste: pd.DataFrame) -> list[dict]:
    """One uniform event list: trim per hall/day/meal/ingredient, plate waste per hall/day/meal,
    overproduction per menu item, expired per lot. Full detail stays in waste_events.csv."""
    cols = ["waste_event_id", "hall_id", "date", "meal_period", "kind", "reason", "ingredient_id", "menu_item_id", "lot_id", "lb", "lb_ap"]
    trim = waste[waste["reason"] == "trim"].groupby(["hall_id", "date", "meal_period", "kind", "reason", "ingredient_id"], as_index=False)[["lb", "lb_ap"]].sum()
    trim["menu_item_id"], trim["lot_id"] = "", ""
    plate = waste[waste["reason"] == "plate_waste"].groupby(["hall_id", "date", "meal_period", "kind", "reason"], as_index=False)[["lb", "lb_ap"]].sum()
    plate["ingredient_id"], plate["menu_item_id"], plate["lot_id"] = "", "", ""
    rest = waste[waste["reason"].isin(["overproduction", "expired_in_storage"])]
    trim["waste_event_id"] = [f"WT{i + 1:05d}" for i in range(len(trim))]
    plate["waste_event_id"] = [f"WP{i + 1:05d}" for i in range(len(plate))]
    allw = pd.concat([trim[cols], plate[cols], rest[cols]], ignore_index=True).sort_values(["date", "hall_id", "waste_event_id"])
    return _records(allw, ndigits=3)


def build_bundle(cfg: dict, sim: Simulation, inputs: Inputs, frames: dict, summary: dict,
                 factors: dict, recs: list[dict]) -> dict:
    mi = frames["menu_items"]
    ing_used = sorted(set(inputs.recipe_ingredients[inputs.recipe_ingredients["recipe_id"].isin(mi["recipe_id"])]["ingredient_id"]))
    rec_used = sorted(set(mi["recipe_id"]))
    ri = inputs.recipe_ingredients[inputs.recipe_ingredients["recipe_id"].isin(rec_used)]
    recipes = []
    rec = inputs.recipes.set_index("recipe_id")
    for rid in rec_used:
        g = ri[ri["recipe_id"] == rid]
        recipes.append({"id": rid, "name": rec.loc[rid, "name"], "portions_per_batch": float(rec.loc[rid, "portions_per_batch"]),
                        "portion_lb": round(float(sim.recipe_portion_lb[rid]), 4),
                        "ingredients": [{"ingredient_id": i, "qty": round(float(q), 4), "unit": u, "qty_lb": round(float(l), 4)}
                                        for i, q, u, l in zip(g["ingredient_id"], g["qty"], g["unit"], g["qty_lb"])]})
    waste = frames["waste_events"]
    trim = waste[waste["reason"] == "trim"].groupby(["hall_id", "date", "ingredient_id"], as_index=False)[["lb", "lb_ap"]].sum()
    item_waste = waste[waste["reason"].isin(["overproduction", "plate_waste"])]
    # Why: item-level waste rides on production rows in the bundle (halves its size); full events stay in waste_events.csv.
    per_item = item_waste.pivot_table(index="menu_item_id", columns="reason", values="lb", aggfunc="sum").reindex(
        columns=["overproduction", "plate_waste"]).fillna(0.0)
    prod_b = frames["production"].merge(per_item.rename(columns={"overproduction": "wasted_lb", "plate_waste": "plate_waste_lb"}),
                                        left_on="menu_item_id", right_index=True, how="left")
    prod_b[["wasted_lb", "plate_waste_lb"]] = prod_b[["wasted_lb", "plate_waste_lb"]].fillna(0.0)
    inv = frames["inventory"]
    on_hand = (inv.groupby(["snapshot_date", "hall_id", "ingredient_id"], as_index=False)
               .agg(qty_lb=("qty_lb", "sum"), lots=("lot_id", "count"), min_days_to_expiry=("days_to_expiry", "min")))
    daily = []
    for (h, d), g in frames["diners"].groupby(["hall_id", "date"]):
        w = waste[(waste["hall_id"] == h) & (waste["date"] == d)]
        p = frames["production"]
        p = p[(p["hall_id"] == h) & (p["date"] == d)]
        dl = frames["deliveries"]
        dl = dl[(dl["hall_id"] == h) & (dl["date"] == d)]
        daily.append({"hall_id": h, "date": d, "covers": int(g["diners_actual"].sum()),
                      "purchased_lb": round(float(dl["qty_lb"].sum()), 2), "served_lb": round(float(p["served_lb"].sum()), 2),
                      "pre_consumer_lb": round(float(w[w["kind"] == "pre_consumer"]["lb"].sum()), 2),
                      "expired_lb": round(float(w[w["kind"] == "expired"]["lb"].sum()), 2),
                      "post_consumer_lb": round(float(w[w["kind"] == "post_consumer"]["lb"].sum()), 2),
                      "donated_lb": round(float(p["donated_lb"].sum()), 2),
                      "portions_short": int(p["portions_short"].sum())})
    stations = (mi[["station_id", "hall_id", "source_station", "station_role"]].drop_duplicates("station_id")
                .rename(columns={"station_id": "id", "source_station": "name", "station_role": "role"}))
    ing_b = inputs.ingredients[inputs.ingredients["ingredient_id"].isin(ing_used)].rename(columns={"ingredient_id": "id"}).copy()
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": {"product": "Second Serve", "scenario": cfg["name"], "description": cfg.get("description"),
                 "start_date": str(cfg["start_date"]), "end_date": str(cfg["end_date"]),
                 "as_of": str(cfg.get("as_of", cfg["end_date"])), "seed": cfg["seed"],
                 # Why: a wall-clock timestamp would break byte-identical output for the same seed.
                 "generated_at": None,
                 "menu_source_week_start": str(cfg["menu_source"]["week_start"]),
                 "transfers_executed": bool(cfg["transfers"]["execute"]),
                 "factors": {k: v["value"] for k, v in factors.items() if k in ("lb_per_meal", "co2e_lb_per_lb")},
                 "factor_sources": factors},
        "provenance": {"inputs": inputs.provenance, "warnings": inputs.warnings, "reference_notes": REFERENCE_NOTES},
        "halls": [{"id": h["id"], "name": h["name"], "seats": h["seats"], "residents": h["residents"],
                   "covers_per_day": h["covers_per_day"], "covers_source": h["covers_source"], "hours": h["hours"],
                   "stations": sorted(stations[stations["hall_id"] == h["id"]]["id"].tolist())} for h in sim.halls],
        "stations": _records(stations.sort_values("id")),
        "ingredients": _records(ing_b),
        "recipes": recipes,
        "menu_sources": {f"{h}|{d}": u for h, d, u in mi[["hall_id", "source_date", "source_url"]].drop_duplicates(["hall_id", "source_date"]).itertuples(index=False)},
        "menu_items": _records(mi.rename(columns={"menu_item_id": "id"}),
                               ["id", "hall_id", "date", "meal_period", "station_id", "name", "recipe_id", "source_date",
                                "serving_lb", "take_rate", "station_role"]),
        "inventory": _records(inv[inv["snapshot"] != "daily"] if cfg.get("bundle", {}).get("inventory_snapshots") == "ends" else inv),
        "inventory_daily": _records(on_hand),
        "production": _records(prod_b, ["hall_id", "date", "meal_period", "menu_item_id", "portions_forecast",
                                        "portions_prepared", "portions_served", "portions_short", "portions_repurposed",
                                        "portions_donated", "portions_wasted", "served_lb", "wasted_lb", "plate_waste_lb",
                                        "donated_lb"], ndigits=2),
        "diners": _records(frames["diners"]),
        "waste": _waste_list(waste),
        "transfers": _records(frames["transfers"]),
        "recommendations": recs,
        "deliveries": _records(frames["deliveries"]),
        "daily_totals": daily,
        "summary": {k: summary[k] for k in ("headline", "checks", "all_checks_pass", "mass_balance", "transfers", "donation_reference")},
    }


# ------------------------------------------------------------ run

def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    raise TypeError(type(o))


def run_scenario(scenario: str, out_dir: Path | str | None = None, overrides: dict | None = None,
                 inputs: Inputs | None = None) -> dict:
    cfg = deep_merge(load_config(scenario), overrides or {})
    inputs = inputs or load_inputs(settings={"shelf_life_pick": cfg.get("shelf_life_pick", "midpoint")})
    sim = Simulation(inputs, cfg)
    raw = sim.run()
    frames = {
        "diners": raw.get("diners", pd.DataFrame()),
        "menu_items": raw.get("menu_items", pd.DataFrame()),
        "production": raw.get("production", pd.DataFrame()),
        "waste_events": raw.get("waste", pd.DataFrame(columns=["hall_id", "date", "meal_period", "kind", "reason",
                                                              "ingredient_id", "menu_item_id", "lot_id", "lb", "lb_ap"])),
        "inventory": raw.get("inventory", pd.DataFrame()),
        "deliveries": raw.get("deliveries", pd.DataFrame()),
        "transfers": raw.get("transfers", pd.DataFrame(columns=["transfer_id", "date", "from_hall", "to_hall", "ingredient_id",
                                                               "qty_lb", "lot_id", "expiry_date", "status", "est_lb_saved"])),
    }
    frames["waste_events"].insert(0, "waste_event_id", [f"W{i + 1:06d}" for i in range(len(frames["waste_events"]))])
    mb = mass_balance(frames, sim.start, sim.end)
    factors = economic_factors(inputs, cfg)
    recs = recommendations.build(sim, frames, cfg)
    summary = build_summary(cfg, inputs, frames, mb)
    summary["factors"] = factors
    summary["reference_notes"] = REFERENCE_NOTES
    summary["fallback_counts"] = fallback_counts(inputs, frames)
    summary["costs"] = cost_summary(inputs, frames, recs)
    summary["recommendations"] = {"count": len(recs), "by_kind": pd.Series([r["kind"] for r in recs]).value_counts().sort_index().to_dict() if recs else {},
                                  "est_lb_saved": round(sum(r["est_lb_saved"] for r in recs), 1)}
    result = {"cfg": cfg, "frames": frames, "mass_balance": mb, "summary": summary, "sim": sim, "inputs": inputs,
              "factors": factors, "recommendations": recs}
    if out_dir is not None:
        out = Path(out_dir)
        if not out.is_absolute():
            out = REPO_ROOT / out
        out.mkdir(parents=True, exist_ok=True)
        halls = pd.DataFrame([{k: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for k, v in h.items()} for h in sim.halls])
        halls.to_csv(out / "halls.csv", index=False)
        mi = frames["menu_items"]
        (mi[["station_id", "hall_id", "source_station", "station_role"]].drop_duplicates("station_id")
         .sort_values("station_id").to_csv(out / "stations.csv", index=False))
        used = set(mi["recipe_id"])
        inputs.ingredients.to_csv(out / "ingredients.csv", index=False)
        inputs.recipes[inputs.recipes["recipe_id"].isin(used)].to_csv(out / "recipes.csv", index=False)
        inputs.recipe_ingredients[inputs.recipe_ingredients["recipe_id"].isin(used)].to_csv(out / "recipe_ingredients.csv", index=False)
        names = {"diners": "diners.csv", "menu_items": "menu_items.csv", "production": "production.csv",
                 "waste_events": "waste_events.csv", "inventory": "inventory_lots.csv", "deliveries": "deliveries.csv",
                 "transfers": "transfers.csv"}
        for k, fn in names.items():
            frames[k].to_csv(out / fn, index=False)
        mb.to_csv(out / "mass_balance.csv", index=False)
        rec_df = pd.DataFrame(recs)
        if len(rec_df):
            rec_df["inputs"] = rec_df["inputs"].map(lambda v: json.dumps(v, default=_json_default))
        rec_df.to_csv(out / "recommendations.csv", index=False)
        with open(out / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=_json_default, ensure_ascii=False)
        bundle = build_bundle(cfg, sim, inputs, frames, summary, result["factors"], result["recommendations"])
        with open(out / "bundle.json", "w") as f:
            json.dump(bundle, f, separators=(",", ":"), default=_json_default, ensure_ascii=False)
        result["out_dir"] = out
    return result
