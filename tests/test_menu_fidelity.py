"""Every synthetic menu item exists in data/raw/menus/menu_items.csv for that hall / date / meal.
For replayed weeks (finals, holiday) the check is against the scraped source date the item came from."""

import pandas as pd
import pytest

from conftest import REPO, SCENARIOS


@pytest.fixture(scope="module")
def raw_menu():
    m = pd.read_csv(REPO / "data" / "raw" / "menus" / "menu_items.csv")
    return set(zip(m.hall, m.date, m.meal_period, m.station, m.item_name))


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_menu_items_exist_in_scrape(outputs, raw_menu, scenario):
    out = outputs[scenario]
    names = dict(zip(out["halls"]["id"], out["halls"]["name"]))
    mi = out["menu_items"]
    assert len(mi) > 0
    keys = zip(mi.hall_id.map(names), mi.source_date, mi.source_meal_period, mi.source_station, mi["name"])
    missing = [k for k in keys if k not in raw_menu]
    assert not missing, f"{len(missing)} synthetic items not in scrape, e.g. {missing[:3]}"


def test_scraped_week_uses_same_dates(outputs):
    mi = outputs["normal_week"]["menu_items"]
    assert (mi.date == mi.source_date).all()


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_source_date_has_same_weekday(outputs, scenario):
    mi = outputs[scenario]["menu_items"]
    a = pd.to_datetime(mi.date).dt.day_of_week
    b = pd.to_datetime(mi.source_date).dt.day_of_week
    assert (a == b).all()
