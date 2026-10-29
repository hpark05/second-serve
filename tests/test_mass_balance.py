"""received + opening = served_lb + recovered_lb + closing + waste_lb + transferred_out - transferred_in, per hall-week.

Recomputed here from the output CSVs, independent of generator.outputs.mass_balance. All terms are
as-purchased-equivalent lb (lb_ap), so cooking gain/loss does not break the balance. recovered_lb (donated
leftovers) extends the PLAN.md formula; it is food that left the hall uneaten but not as waste."""

import datetime as dt

import pandas as pd
import pytest

from conftest import SCENARIOS

TOLERANCE_PCT = 1.0


def hall_weeks(out):
    dates = sorted(pd.to_datetime(out["diners"]["date"]).dt.date.unique())
    start, end = dates[0], dates[-1]
    d = start
    while d <= end:
        we = min(end, d + dt.timedelta(days=6 - d.weekday()))
        yield d, we
        d = we + dt.timedelta(days=1)


@pytest.mark.parametrize("scenario", SCENARIOS + ["normal_week_transfers"])
def test_mass_balance_per_hall_week(outputs, scenario):
    out = outputs[scenario]
    inv, dlv, prod, waste, tr = out["inventory_lots"], out["deliveries"], out["production"], out["waste_events"], out["transfers"]
    done = tr[tr["status"] == "completed"]
    checked = 0
    for ws, we in hall_weeks(out):
        days = {x.isoformat() for x in pd.date_range(ws, we).date}
        opening_day = (ws - dt.timedelta(days=1)).isoformat()
        for h in sorted(out["halls"]["id"]):
            opening = inv[(inv.hall_id == h) & (inv.snapshot_date == opening_day)].qty_lb.sum()
            closing = inv[(inv.hall_id == h) & (inv.snapshot_date == we.isoformat())].qty_lb.sum()
            received = dlv[(dlv.hall_id == h) & dlv.date.isin(days)].qty_lb.sum()
            p = prod[(prod.hall_id == h) & prod.date.isin(days)]
            w = waste[(waste.hall_id == h) & waste.date.isin(days) & waste.kind.isin(["pre_consumer", "expired"])]
            t_out = done[(done.from_hall == h) & done.date.isin(days)].qty_lb.sum()
            t_in = done[(done.to_hall == h) & done.date.isin(days)].qty_lb.sum()
            lhs = received + opening
            rhs = p.served_lb_ap.sum() + p.recovered_lb_ap.sum() + closing + w.lb_ap.sum() + t_out - t_in
            if lhs == 0 and rhs == 0:
                continue
            assert lhs > 0, f"{scenario} {h} {ws}: nothing received or on hand"
            err = 100 * abs(lhs - rhs) / lhs
            assert err <= TOLERANCE_PCT, f"{scenario} {h} week {ws}: imbalance {err:.3f}% (lhs {lhs:.1f}, rhs {rhs:.1f})"
            checked += 1
    assert checked >= 4


def test_transfers_actually_move_mass(outputs):
    tr = outputs["normal_week_transfers"]["transfers"]
    assert len(tr) and (tr["status"] == "completed").all()
    assert (outputs["normal_week"]["transfers"]["status"] == "proposed").all()
