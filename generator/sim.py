"""Simulation: demand, production, FIFO inventory, waste, transfers.

Mass is tracked two ways:
  * lb      physical weight as weighed (cooked/as-served for food, as-purchased for raw lots)
  * lb_ap   as-purchased-equivalent weight, used for the inventory mass balance
Cooking gain/loss (rice absorbing water, meat losing moisture) changes lb but not lb_ap, so the
balance closes exactly in lb_ap while waste benchmarks are compared in physical lb."""

from __future__ import annotations

import datetime as dt
import math
import zlib
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .loaders import Inputs, normalize_station

MEAL_ORDER = {"breakfast": 0, "brunch": 0, "lunch": 1, "dinner": 2}


def rng_for(seed: int, *key) -> np.random.Generator:
    # Why: Python's hash() is salted per process; crc32 keeps streams stable across runs.
    h = zlib.crc32("|".join(map(str, key)).encode())
    return np.random.default_rng([int(seed), h])


def as_date(v) -> dt.date:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v))


def daterange(a: dt.date, b: dt.date):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def _matches(rule_val, value) -> bool:
    if rule_val in (None, "all"):
        return True
    vals = rule_val if isinstance(rule_val, list) else [rule_val]
    return value in [as_date(v) if isinstance(value, dt.date) else v for v in vals]


@dataclass
class Lot:
    lot_id: str
    hall_id: str
    ingredient_id: str
    qty_lb: float
    received: dt.date
    expiry: dt.date
    origin: str


class Simulation:
    def __init__(self, inputs: Inputs, cfg: dict):
        self.inp = inputs
        self.cfg = cfg
        self.seed = int(cfg["seed"])
        self.start = as_date(cfg["start_date"])
        self.end = as_date(cfg["end_date"])
        self.dates = list(daterange(self.start, self.end))
        self.src_week = as_date(cfg["menu_source"]["week_start"])
        self.halls = self._build_halls()
        self.hall_by_name = {h["name"]: h for h in self.halls}
        self._index_menu()
        self._index_recipes()
        self.ing = inputs.ingredients.set_index("ingredient_id")
        self._plate_range = self._plate_prior()
        self.records = defaultdict(list)
        self.lots: dict[tuple, list[Lot]] = defaultdict(list)   # (hall_id, ingredient_id) -> FIFO list
        self.lot_seq = 0
        self.forecast_cache: dict = {}
        self.plan_cache: dict = {}
        self.proposed: set = set()

    # ------------------------------------------------------------ static entities
    def _build_halls(self) -> list[dict]:
        vol = self.inp.hall_volume
        vcfg = self.cfg["volume"]
        per_day = vol[vol["metric"] == "students_served_per_day"].set_index("hall")
        halls = []
        for h in self.cfg["halls"]:
            name = h["name"]
            rec = {"id": h["id"], "name": name, "covers_per_day": None, "covers_source": None}
            if name in per_day.index:
                row = per_day.loc[name]
                rec["covers_per_day"] = float(row["value"])
                rec["covers_source"] = {"metric": "students_served_per_day", "source_url": row["source_url"],
                                        "quote": row.get("quote")}
            halls.append(rec)
        resid = vcfg["residual_hall"]
        tot = vol[(vol["hall"] == vcfg["total_hall"]) & (vol["metric"] == vcfg["total_metric"])]
        tot = tot.assign(v=pd.to_numeric(tot["value"], errors="coerce")).dropna(subset=["v"]).sort_values("v")
        total_row = tot.iloc[-1]
        known = sum(h["covers_per_day"] for h in halls if h["covers_per_day"])
        for h in halls:
            if h["name"] == resid and h["covers_per_day"] is None:
                h["covers_per_day"] = float(total_row["v"]) - known
                h["covers_source"] = {"metric": "derived_residual",
                                      "formula": f"{vcfg['total_hall']} {vcfg['total_metric']} ({total_row['v']:.0f}) minus the other three halls ({known:.0f})",
                                      "source_url": total_row["source_url"]}
        seats = vol[vol["metric"] == "seats"]
        attrs = self.inp.hall_attrs
        for h in halls:
            s = seats[seats["hall"] == h["name"]]
            h["seats"] = int(pd.to_numeric(s["value"]).iloc[-1]) if len(s) else None
            h["seats_source"] = s["source_url"].iloc[-1] if len(s) else None
            a = attrs[attrs["hall"] == h["name"]].set_index("attribute")["value"]
            h["hours"] = {k.replace("hours_", ""): a[k] for k in a.index if str(k).startswith("hours_")}
            h["feeder_housing"] = a.get("feeder_housing")
            h["residents"] = None   # no per-hall resident count in data/raw
        return halls

    def _index_menu(self):
        m = self.inp.menu
        m = m[m["hall"].isin(self.hall_by_name) & self.inp.menu_recipe.reindex(m["menu_row"]).notna().values].copy()
        m["recipe_id"] = self.inp.menu_recipe.reindex(m["menu_row"]).values
        m["date_d"] = m["date"].map(as_date)
        self.menu = m
        self.menu_by_key = {k: g for k, g in m.groupby(["hall", "date_d"], sort=True)}
        roles = self.cfg["station_roles"]
        self.station_role = {}
        for st in sorted(m["station_norm"].unique()):
            role = roles["default_role"]
            for rule in roles["rules"]:
                if rule["match"] in st:
                    role = rule["role"]
                    break
            self.station_role[st] = role

    def _index_recipes(self):
        rec = self.inp.recipes.set_index("recipe_id")
        ri = self.inp.recipe_ingredients
        self.recipe_portion_lb = {}
        self.recipe_ep = {}   # recipe_id -> list[(ingredient_id, as-served lb per portion)]
        for rid, g in ri.groupby("recipe_id", sort=True):
            if rid not in rec.index:
                continue
            ppb = float(rec.loc[rid, "portions_per_batch"])
            comps = [(i, float(q) / ppb) for i, q in zip(g["ingredient_id"], g["qty_lb"]) if float(q) > 0]
            self.recipe_ep[rid] = comps
            self.recipe_portion_lb[rid] = sum(q for _, q in comps)

    def _plate_prior(self) -> tuple[float, float]:
        b = self.inp.benchmarks
        row = b[b["metric"] == self.cfg["plate_waste"]["prior_metric"]].iloc[0]
        return float(row["value_low"]) / 100, float(row["value_high"]) / 100

    # ------------------------------------------------------------ menus and demand
    def source_date(self, d: dt.date) -> dt.date:
        return self.src_week + dt.timedelta(days=(d.weekday() - self.src_week.weekday()) % 7)

    def menu_rows(self, hall: dict, d: dt.date) -> pd.DataFrame | None:
        return self.menu_by_key.get((hall["name"], self.source_date(d)))

    def multiplier(self, hall: dict, d: dt.date, meal: str) -> float:
        m = 1.0
        for r in self.cfg.get("diner_multipliers") or []:
            if _matches(r.get("dates"), d) and _matches(r.get("halls"), hall["name"]) and _matches(r.get("meals"), meal):
                m *= float(r["multiplier"])
        return m

    def closed(self, hall: dict, d: dt.date, meal: str) -> bool:
        for r in self.cfg.get("closures") or []:
            if _matches(r.get("dates"), d) and _matches(r.get("halls"), hall["name"]) and _matches(r.get("meals"), meal):
                return True
        return False

    def mean_covers(self, hall: dict, d: dt.date, meal: str) -> float:
        v = self.cfg["volume"]
        weekend = d.weekday() >= 5
        shares = v["meal_shares"]["weekend" if weekend else "weekday"]
        return hall["covers_per_day"] * (v["weekend_covers_factor"] if weekend else 1.0) * shares.get(meal, 0.0)

    def history_diners(self, hall: dict, d: dt.date, meal: str) -> int:
        return int(rng_for(self.seed, "hist", hall["id"], d, meal).poisson(self.mean_covers(hall, d, meal)))

    def forecast_diners(self, hall: dict, d: dt.date, meal: str) -> float:
        key = (hall["id"], d, meal)
        if key not in self.forecast_cache:
            n = self.cfg["forecast"]["history_weeks"]
            past = [self.history_diners(hall, d - dt.timedelta(days=7 * k), meal) for k in range(1, n + 1)]
            self.forecast_cache[key] = float(np.mean(past))
        return self.forecast_cache[key]

    def actual_diners(self, hall: dict, d: dt.date, meal: str) -> int:
        lam = self.mean_covers(hall, d, meal) * self.multiplier(hall, d, meal)
        return int(rng_for(self.seed, "diners", hall["id"], d, meal).poisson(lam))

    def take_rates(self, hall: dict, src: dt.date, rows: pd.DataFrame) -> np.ndarray:
        """Per-item take rate: station visit rate x picks, split across the station's items by a
        lognormal popularity weight. Keyed on the source menu day so history and forecast agree."""
        roles = self.cfg["station_roles"]["roles"]
        rates = np.zeros(len(rows))
        for (meal, st), idx in rows.groupby(["meal", "station_norm"], sort=True).indices.items():
            spec = roles[self.station_role[st]]
            r = rng_for(self.seed, "take", hall["id"], src, meal, st)
            visit = r.uniform(*spec["take"])
            w = r.lognormal(0.0, 0.35, size=len(idx))
            share = w / w.sum() * visit * spec["picks"]
            rates[idx] = np.minimum(share, visit)
        return np.minimum(rates, 0.95)

    # ------------------------------------------------------------ production plan
    def ap_per_portion(self, recipe_id: str, serving_lb: float | None) -> list[tuple[str, float, float]]:
        """[(ingredient_id, as-served lb, as-purchased lb)] per portion, scaled to the menu's serving size."""
        comps = self.recipe_ep[recipe_id]
        base = self.recipe_portion_lb[recipe_id]
        scale = serving_lb / base if serving_lb and base > 0 else 1.0
        out = []
        for iid, ep in comps:
            row = self.ing.loc[iid]
            served = ep * scale
            out.append((iid, served, served / float(row["yield_factor"])))
        return out

    def plan(self, hall: dict, d: dt.date) -> list[dict]:
        """Forecast-driven production plan for hall/day. Deterministic, so the same plan drives
        both purchasing (days ahead) and day-of production."""
        key = (hall["id"], d)
        if key in self.plan_cache:
            return self.plan_cache[key]
        rows = self.menu_rows(hall, d)
        items = []
        if rows is not None:
            rows = rows.reset_index(drop=True)
            src = self.source_date(d)
            rates = self.take_rates(hall, src, rows)
            known = self.cfg.get("forecast_known_closures", True)
            lo, hi = self.cfg["forecast"]["overprep_range"]
            for i, r in rows.iterrows():
                meal = r["meal"]
                if self.closed(hall, d, meal) and known:
                    continue
                fd = self.forecast_diners(hall, d, meal)
                fport = fd * rates[i]
                over = rng_for(self.seed, "overprep", hall["id"], d, meal, i).uniform(lo, hi)
                prepared = int(math.ceil(fport * over)) if fport > 0 else 0
                # Why: some Eatec "1 SV" sizes are whole pans (e.g. 241 oz chicken salad); use the recipe portion instead.
                cap = self.cfg["production"]["max_serving_lb"]
                serving_lb = r["serving_lb"]
                if pd.isna(serving_lb) or serving_lb > cap:
                    serving_lb = self.recipe_portion_lb[r["recipe_id"]]
                items.append({"idx": i, "row": r, "meal": meal, "take_rate": float(rates[i]),
                              "forecast_diners": fd, "portions_forecast": fport, "overprep": over,
                              "portions_prepared": prepared, "serving_lb": float(serving_lb),
                              "comps": self.ap_per_portion(r["recipe_id"], float(serving_lb))})
        self.plan_cache[key] = items
        return items

    def planned_need(self, hall: dict, d: dt.date) -> dict[str, float]:
        need: dict[str, float] = defaultdict(float)
        for it in self.plan(hall, d):
            for iid, _, ap in it["comps"]:
                need[iid] += ap * it["portions_prepared"]
        return need

    # ------------------------------------------------------------ inventory
    def new_lot(self, hall_id, iid, qty, received, origin) -> Lot:
        self.lot_seq += 1
        sl = int(self.ing.loc[iid, "shelf_life_days"])
        return Lot(f"L{self.lot_seq:07d}", hall_id, iid, qty, received, received + dt.timedelta(days=sl), origin)

    def delivery_days(self, iid: str) -> list[int]:
        inv = self.cfg["inventory"]
        row = self.ing.loc[iid]
        if int(row["shelf_life_days"]) <= inv["daily_delivery_max_shelf_life"]:
            return [0, 1, 2, 3, 4, 5]
        cat = row["fallback_category"]
        if cat in inv["delivery_days"]["category"]:
            return inv["delivery_days"]["category"][cat]
        return inv["delivery_days"]["storage"].get(row["storage"], [0])

    def cover_days(self, iid: str, d: dt.date) -> int:
        days = self.delivery_days(iid)
        gap = next(k for k in range(1, 8) if (d + dt.timedelta(days=k)).weekday() in days)
        return max(1, min(gap, int(self.ing.loc[iid, "shelf_life_days"])))

    def order_qty(self, hall, iid, d, cover, on_hand) -> float:
        inv = self.cfg["inventory"]
        need = sum(self.planned_need(hall, d + dt.timedelta(days=k)).get(iid, 0.0) for k in range(cover))
        qty = need * (1 + inv["safety_stock_pct"]) - on_hand
        if qty <= 1e-6:
            return 0.0
        case = self.ing.loc[iid, "case_lb"] if "case_lb" in self.ing.columns else None
        long_life = int(self.ing.loc[iid, "shelf_life_days"]) > inv.get("round_to_case_min_shelf_life", 0)
        if inv.get("round_to_case") and long_life and case is not None and pd.notna(case) and case > 1:
            qty = math.ceil(qty / case) * case
        return round(qty, 4)

    def usable_on_hand(self, hall_id, iid, d) -> float:
        return sum(l.qty_lb for l in self.lots[(hall_id, iid)] if l.expiry > d)

    def receive(self, hall, iid, qty, d, origin, stock: bool = True):
        lot = self.new_lot(hall["id"], iid, qty, d, origin)
        if stock:
            self.lots[(hall["id"], iid)].append(lot)
        self.records["deliveries"].append({"lot_id": lot.lot_id, "hall_id": hall["id"], "ingredient_id": iid,
                                           "date": d.isoformat(), "qty_lb": qty, "kind": origin,
                                           "expiry_date": lot.expiry.isoformat()})
        return lot

    def consume(self, hall, iid, qty, d) -> None:
        lots = self.lots[(hall["id"], iid)]
        lots.sort(key=lambda l: (l.received, l.lot_id))
        remaining = qty
        for l in lots:
            if remaining <= 1e-9:
                break
            take = min(l.qty_lb, remaining)
            l.qty_lb -= take
            remaining -= take
        self.lots[(hall["id"], iid)] = [l for l in lots if l.qty_lb > 1e-9]
        if remaining > 1e-9:
            # Short: emergency drop received and used the same day.
            self.receive(hall, iid, remaining, d, "emergency", stock=False)

    def snapshot(self, d: dt.date, label: str):
        for (hid, iid), lots in sorted(self.lots.items()):
            for l in lots:
                if l.qty_lb > 1e-9:
                    lpu = float(self.ing.loc[iid, "lb_per_unit"]) or 1.0
                    self.records["inventory"].append({
                        "snapshot_date": d.isoformat(), "snapshot": label, "lot_id": l.lot_id, "hall_id": hid,
                        "ingredient_id": iid, "qty": round(l.qty_lb / lpu, 4), "unit": self.ing.loc[iid, "unit"],
                        "qty_lb": l.qty_lb, "received_date": l.received.isoformat(),
                        "expiry_date": l.expiry.isoformat(), "origin": l.origin,
                        "days_to_expiry": (l.expiry - d).days})

    def waste(self, **kw):
        self.records["waste"].append(kw)

    # ------------------------------------------------------------ main loop
    def opening_stock(self):
        inv = self.cfg["inventory"]
        day0 = self.start - dt.timedelta(days=1)
        need: dict[tuple, float] = defaultdict(float)
        for hall in self.halls:
            iids = set()
            for k in range(7):
                iids |= set(self.planned_need(hall, self.start + dt.timedelta(days=k)))
            for iid in sorted(iids):
                days = self.delivery_days(iid)
                until = next(k for k in range(0, 7) if (self.start + dt.timedelta(days=k)).weekday() in days)
                cover = max(inv["opening_cover_days"], until)
                cover = min(cover, int(self.ing.loc[iid, "shelf_life_days"]) - 1)
                qty = sum(self.planned_need(hall, self.start + dt.timedelta(days=k)).get(iid, 0.0) for k in range(cover))
                qty *= 1 + inv["safety_stock_pct"]
                if qty > 1e-6:
                    lot = self.new_lot(hall["id"], iid, round(qty, 4), day0, "opening")
                    self.lots[(hall["id"], iid)].append(lot)
        self.snapshot(day0, "opening")

    def run(self) -> dict[str, pd.DataFrame]:
        self.opening_stock()
        lc = self.cfg["leftover"]
        for d in self.dates:
            for hall in self.halls:
                self.day(hall, d, lc)
            self.transfers(d)
            self.snapshot(d, "closing" if d == self.end else "daily")
        return {k: pd.DataFrame(v) for k, v in self.records.items()}

    def day(self, hall, d, lc):
        hid = hall["id"]
        # 1. Expire lots whose expiry date has arrived.
        for (h, iid), lots in sorted(self.lots.items()):
            if h != hid:
                continue
            keep = []
            for l in lots:
                if l.expiry <= d and l.qty_lb > 1e-9:
                    self.waste(hall_id=hid, date=d.isoformat(), meal_period="", kind="expired", reason="expired_in_storage",
                               ingredient_id=iid, menu_item_id="", lot_id=l.lot_id, lb=l.qty_lb, lb_ap=l.qty_lb)
                else:
                    keep.append(l)
            self.lots[(h, iid)] = keep
        # 2. Scheduled deliveries.
        need_iids = set()
        for k in range(7):
            need_iids |= set(self.planned_need(hall, d + dt.timedelta(days=k)))
        for iid in sorted(need_iids):
            if d.weekday() in self.delivery_days(iid):
                cover = self.cover_days(iid, d)
                q = self.order_qty(hall, iid, d, cover, self.usable_on_hand(hid, iid, d))
                if q > 0:
                    self.receive(hall, iid, q, d, "delivery")
        # 3. Meals.
        plan = self.plan(hall, d)
        meals = sorted({it["meal"] for it in plan}, key=lambda m: MEAL_ORDER.get(m, 9))
        for meal in meals:
            if self.closed(hall, d, meal):
                continue
            diners = self.actual_diners(hall, d, meal)
            fdin = self.forecast_diners(hall, d, meal)
            pr = rng_for(self.seed, "plate", hid, d, meal).uniform(*self._plate_range)
            self.records["diners"].append({"hall_id": hid, "date": d.isoformat(), "meal_period": meal,
                                           "diners_forecast": round(fdin, 2), "diners_actual": diners,
                                           "multiplier": self.multiplier(hall, d, meal), "plate_waste_frac": pr})
            for it in (x for x in plan if x["meal"] == meal):
                self.produce(hall, d, meal, it, diners, pr, lc)

    def produce(self, hall, d, meal, it, diners, plate_frac, lc):
        hid = hall["id"]
        r = it["row"]
        mid = f"{hid}:{d.isoformat()}:{meal}:{it['idx']:03d}"
        rng = rng_for(self.seed, "item", hid, d, meal, it["idx"])
        demand = int(rng.binomial(diners, it["take_rate"])) if diners > 0 else 0
        prepared = it["portions_prepared"]
        served = min(prepared, demand)
        left = prepared - served
        rep = int(round(left * rng.uniform(*lc["repurpose_frac_range"])))
        don = int(round((left - rep) * rng.uniform(*lc["donate_frac_range"])))
        wasted = left - rep - don
        food_ap = 0.0   # AP-equivalent lb of edible food per portion (after trim)
        cost = {b: sum(ap * float(self.ing.loc[iid, c]) for iid, _, ap in it["comps"])
                for b, c in (("mid", "usd_per_lb"), ("low", "usd_per_lb_low"), ("high", "usd_per_lb_high"))}
        for iid, served_lb, ap in it["comps"]:
            use = ap * prepared
            if use <= 0:
                continue
            self.consume(hall, iid, use, d)
            trim = use * float(self.ing.loc[iid, "trim_frac"])
            if trim > 0:
                self.waste(hall_id=hid, date=d.isoformat(), meal_period=meal, kind="pre_consumer", reason="trim",
                           ingredient_id=iid, menu_item_id=mid, lot_id="", lb=trim, lb_ap=trim)
            food_ap += ap * (1 - float(self.ing.loc[iid, "trim_frac"]))
        sl = it["serving_lb"]
        self.records["menu_items"].append({
            "menu_item_id": mid, "hall_id": hid, "date": d.isoformat(), "meal_period": meal,
            "station_id": f"{hid}:{r['station_norm']}", "name": r["item_name"], "recipe_id": r["recipe_id"],
            "source_date": r["date"], "source_meal_period": r["meal_period"], "source_station": r["station"],
            "source_url": r["source_url"], "serving_lb": sl, "take_rate": it["take_rate"],
            "station_role": self.station_role[r["station_norm"]]})
        self.records["production"].append({
            "hall_id": hid, "date": d.isoformat(), "meal_period": meal, "menu_item_id": mid,
            "portions_forecast": round(it["portions_forecast"], 3), "overprep_factor": round(it["overprep"], 4),
            "portions_prepared": prepared, "portions_demanded": demand, "portions_served": served,
            "portions_short": max(0, demand - prepared), "portions_repurposed": rep, "portions_donated": don,
            "portions_wasted": wasted, "serving_lb": sl,
            "served_lb": served * sl, "repurposed_lb": rep * sl, "donated_lb": don * sl,
            "served_lb_ap": (served + rep) * food_ap, "recovered_lb_ap": don * food_ap,
            "prepared_lb_ap_food": prepared * food_ap,
            "usd_per_portion": cost["mid"], "usd_per_portion_low": cost["low"], "usd_per_portion_high": cost["high"]})
        if wasted > 0:
            self.waste(hall_id=hid, date=d.isoformat(), meal_period=meal, kind="pre_consumer", reason="overproduction",
                       ingredient_id="", menu_item_id=mid, lot_id="", lb=wasted * sl, lb_ap=wasted * food_ap)
        if served > 0:
            # Plate waste is a subset of served food; reported, excluded from the inventory balance.
            self.waste(hall_id=hid, date=d.isoformat(), meal_period=meal, kind="post_consumer", reason="plate_waste",
                       ingredient_id="", menu_item_id=mid, lot_id="", lb=served * sl * plate_frac,
                       lb_ap=served * food_ap * plate_frac)

    def transfers(self, d: dt.date):
        """Lot at hall A expiring within horizon that A will not use in time, while hall B plans to use
        the ingredient within the window -> Transfer candidate (executed only if configured)."""
        tcfg = self.cfg["transfers"]
        horizon = int(tcfg["horizon_days"])
        execute = bool(tcfg["execute"])
        window = [d + dt.timedelta(days=k) for k in range(1, horizon + 1)]
        for a in self.halls:
            for (hid, iid), lots in sorted(self.lots.items()):
                if hid != a["id"]:
                    continue
                expiring = [l for l in lots if l.qty_lb > 1e-9 and (l.expiry - d).days <= horizon]
                if not expiring:
                    continue
                exp_qty = sum(l.qty_lb for l in expiring)
                own_need = sum(self.planned_need(a, w).get(iid, 0.0) for w in window if w < max(l.expiry for l in expiring))
                excess = exp_qty - own_need
                if excess <= 0.5:
                    continue
                for b in self.halls:
                    if b["id"] == a["id"] or excess <= 0.5:
                        continue
                    b_need = sum(self.planned_need(b, w).get(iid, 0.0) for w in window if w < max(l.expiry for l in expiring))
                    qty = round(min(excess, b_need), 4)
                    first = sorted(expiring, key=lambda l: l.expiry)[0]
                    if qty <= 0.5 or (first.lot_id, b["id"]) in self.proposed:
                        continue
                    self.proposed.add((first.lot_id, b["id"]))
                    excess -= qty
                    tid = f"T{len(self.records['transfers']) + 1:05d}"
                    self.records["transfers"].append({
                        "transfer_id": tid, "date": d.isoformat(), "from_hall": a["id"], "to_hall": b["id"],
                        "ingredient_id": iid, "qty_lb": qty, "lot_id": first.lot_id,
                        "expiry_date": first.expiry.isoformat(), "status": "completed" if execute else "proposed",
                        "est_lb_saved": qty})
                    if execute:
                        self._move(a, b, iid, expiring, qty)

    def _move(self, a, b, iid, expiring, qty):
        remaining = qty
        for l in sorted(expiring, key=lambda l: l.expiry):
            if remaining <= 1e-9:
                break
            take = min(l.qty_lb, remaining)
            l.qty_lb -= take
            remaining -= take
            self.lot_seq += 1
            self.lots[(b["id"], iid)].append(Lot(f"L{self.lot_seq:07d}", b["id"], iid, take, l.received, l.expiry, "transfer_in"))
        self.lots[(a["id"], iid)] = [l for l in self.lots[(a["id"], iid)] if l.qty_lb > 1e-9]
