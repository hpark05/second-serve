"""Rule-based Recommendation candidates for the Second Serve app, derived from sim output.

These are deterministic baselines the app (or its Claude agent) can rank, explain or replace. Every
recommendation carries the numbers it was computed from in `inputs`."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd


def _rec(recs: list, **kw) -> None:
    kw["id"] = f"R{len(recs) + 1:05d}"
    recs.append(kw)


def build(sim, frames: dict[str, pd.DataFrame], cfg: dict) -> list[dict]:
    rcfg = cfg.get("recommendations", {})
    min_lb = float(rcfg.get("min_lb_saved", 2.0))
    top_n = int(rcfg.get("adjust_prep_top_n_per_hall_day", 5))
    low_overprep = float(cfg["forecast"]["overprep_range"][0])
    price = sim.inp.ingredients.set_index("ingredient_id")["usd_per_lb"].to_dict()

    def usd(lb: float, iid: str) -> float | None:
        p = price.get(iid)
        return None if p is None or pd.isna(p) else round(lb * float(p), 2)
    recs: list[dict] = []
    halls = {h["id"]: h for h in sim.halls}
    names = sim.inp.ingredients.set_index("ingredient_id")["name"].to_dict()

    # use_first: lots that will expire before the hall's own plan uses them.
    inv = frames["inventory"]
    inv = inv[(inv["snapshot"] != "opening") & (inv["days_to_expiry"] <= 2)]
    flagged: set[str] = set()
    for (d, hid, iid), g in inv.groupby(["snapshot_date", "hall_id", "ingredient_id"], sort=True):
        # Why: a lot stays "at risk" for several snapshots; recommend it once, on the first day it is flagged.
        g = g[~g["lot_id"].isin(flagged)]
        if not len(g):
            continue
        day = dt.date.fromisoformat(d)
        expiry = dt.date.fromisoformat(g["expiry_date"].min())
        need = sum(sim.planned_need(halls[hid], day + dt.timedelta(days=k)).get(iid, 0.0)
                   for k in range(1, (expiry - day).days))
        at_risk = float(g["qty_lb"].sum()) - need
        if at_risk >= min_lb:
            flagged.update(g["lot_id"])
            _rec(recs, hall_id=hid, date=d, kind="use_first", target=iid, qty=round(at_risk, 2), unit="lb",
                 est_lb_saved=round(at_risk, 2), est_usd_saved=usd(at_risk, iid),
                 rationale=f"{at_risk:.0f} lb of {names.get(iid, iid)} expires {expiry.isoformat()} and the plan uses only {need:.0f} lb before then. Feature it on a While It Lasts station.",
                 inputs={"lots": g["lot_id"].tolist(), "on_hand_lb": round(float(g["qty_lb"].sum()), 2),
                         "planned_use_lb": round(need, 2), "expiry_date": expiry.isoformat()})

    # adjust_prep: prepare at the low end of the overprep band where overproduction was wasted.
    prod = frames["production"].merge(frames["menu_items"][["menu_item_id", "name"]], on="menu_item_id")
    cands = []
    for r in prod.itertuples():
        target = math.ceil(r.portions_forecast * low_overprep)
        cut = r.portions_prepared - target
        saved = min(cut, r.portions_wasted) * r.serving_lb
        if cut > 0 and saved >= min_lb:
            cands.append((r.hall_id, r.date, saved, r, target, cut))
    cdf = pd.DataFrame([{"hall_id": h, "date": d, "saved": s, "i": i} for i, (h, d, s, *_rest) in enumerate(cands)])
    if len(cdf):
        keep = cdf.sort_values(["hall_id", "date", "saved", "i"], ascending=[True, True, False, True]).groupby(["hall_id", "date"]).head(top_n)
        for i in sorted(keep["i"]):
            h, d, saved, r, target, cut = cands[i]
            _rec(recs, hall_id=h, date=d, kind="adjust_prep", target=r.menu_item_id, qty=int(cut), unit="portions",
                 # Why: menu-item savings are priced at the item's as-purchased ingredient cost per portion.
                 est_lb_saved=round(saved, 2), est_usd_saved=round(min(cut, r.portions_wasted) * r.usd_per_portion, 2),
                 rationale=f"Prep {target} portions of {r.name} ({r.meal_period}) instead of {r.portions_prepared}: forecast {r.portions_forecast:.0f}, {r.portions_wasted} portions were binned.",
                 inputs={"portions_forecast": r.portions_forecast, "portions_prepared": r.portions_prepared,
                         "portions_served": r.portions_served, "portions_wasted": r.portions_wasted,
                         "overprep_factor": r.overprep_factor, "serving_lb": r.serving_lb,
                         "usd_per_portion": round(r.usd_per_portion, 4),
                         "usd_per_portion_low": round(r.usd_per_portion_low, 4), "usd_per_portion_high": round(r.usd_per_portion_high, 4)})

    # buy_less: ingredients that expired in storage at a hall over the scenario.
    w = frames["waste_events"]
    exp = w[w["kind"] == "expired"]
    for (hid, iid), g in exp.groupby(["hall_id", "ingredient_id"], sort=True):
        lb = float(g["lb"].sum())
        if lb >= min_lb:
            _rec(recs, hall_id=hid, date=g["date"].min(), kind="buy_less", target=iid, qty=round(lb, 2), unit="lb",
                 est_lb_saved=round(lb, 2), est_usd_saved=usd(lb, iid),
                 rationale=f"{lb:.0f} lb of {names.get(iid, iid)} expired unused across {len(g)} lot(s); cut the standing order by that much.",
                 inputs={"expired_lots": g["lot_id"].tolist(), "dates": sorted(g["date"].unique().tolist())})

    # transfer: one per transfer candidate.
    for t in frames["transfers"].itertuples():
        _rec(recs, hall_id=t.from_hall, date=t.date, kind="transfer", target=f"{t.ingredient_id}->{t.to_hall}",
             qty=round(t.qty_lb, 2), unit="lb", est_lb_saved=round(t.est_lb_saved, 2), est_usd_saved=usd(t.est_lb_saved, t.ingredient_id),
             rationale=f"Send {t.qty_lb:.0f} lb of {names.get(t.ingredient_id, t.ingredient_id)} (expires {t.expiry_date}) to {halls[t.to_hall]['name']}, which plans to use it within {cfg['transfers']['horizon_days']} days.",
             inputs={"transfer_id": t.transfer_id, "lot_id": t.lot_id, "status": t.status})

    # recover: overproduction still binned per hall-day that could go to food recovery instead.
    over = w[w["reason"] == "overproduction"]
    for (hid, d), g in over.groupby(["hall_id", "date"], sort=True):
        lb = float(g["lb"].sum())
        if lb >= min_lb:
            _rec(recs, hall_id=hid, date=d, kind="recover", target="food_recovery", qty=round(lb, 2), unit="lb",
                 est_lb_saved=round(lb, 2), est_usd_saved=None,
                 rationale=f"{lb:.0f} lb of prepared food was binned at {halls[hid]['name']}; route it to the campus food recovery pickup instead.",
                 inputs={"menu_items": int(g["menu_item_id"].nunique())})
    return recs
