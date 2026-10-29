"""Scrape Cal Dining residential dining hall menus.

Source: dining.berkeley.edu serves each location's daily menu as an Eatec XML export at
  https://dining.berkeley.edu/wp-content/uploads/menus-exportimport/<Location>_<YYYYMMDD>.xml
(found by base64-decoding the data-location attribute in the /menus/ page HTML).
The site does NOT use Nutrislice. Files exist for roughly the past ~10 days and ~6 days ahead;
older files return 404, so rerun this regularly to accumulate history.

Supplement: Wayback Machine snapshots of https://dining.berkeley.edu/menus/ (one day each).

Run:  uv run --python 3.12 --with httpx --with beautifulsoup4 python scripts/scrape_menus.py [--back 30] [--ahead 10]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "menus"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
XML_URL = "https://dining.berkeley.edu/wp-content/uploads/menus-exportimport/{loc}_{date}.xml"
DELAY = 0.7

# site location value -> (folder slug, display name)
HALLS = {
    "Crossroads": ("crossroads", "Crossroads"),
    "Cafe_3": ("cafe3", "Café 3"),
    "Foothill": ("foothill", "Foothill"),
    "Clark_Kerr_Campus": ("clark_kerr", "Clark Kerr"),
}
WAYBACK_HALLS = {"Crossroads": "Crossroads", "Café 3": "Café 3", "Cafe 3": "Café 3", "Foothill": "Foothill",
                 "Clark Kerr": "Clark Kerr", "Clark Kerr Campus": "Clark Kerr"}
WAYBACK_DELAY = 8.0

CSV_COLS = ["hall", "date", "meal_period", "station", "item_name", "ingredients", "allergens",
            "serving_size", "calories", "source_url",
            # extras beyond the requested schema
            "dietary_choices", "carbon_kg_co2", "recipe_id", "menu_name", "source_type"]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def parse_xml(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    menus = []
    for m in root.findall("menu"):
        nutrient_names = [n for n in (m.findtext("nutrients") or "").split("|") if n]
        recipes = []
        for r in m.findall("recipes/recipe"):
            vals = (r.get("nutrients") or "").split("|")
            nutrients = {k: (vals[i] if i < len(vals) else None) for i, k in enumerate(nutrient_names)}
            recipes.append({
                **{k: v for k, v in r.attrib.items() if k != "nutrients"},
                "nutrients": nutrients,
                "allergens": {a.get("id"): a.text for a in r.findall("allergens/allergen")},
                "dietaryChoices": {a.get("id"): a.text for a in r.findall("dietaryChoices/dietaryChoice")},
                "ingredients": " ".join((r.findtext("ingredients") or "").split()),
            })
        menus.append({"menu": dict(m.attrib), "recipes": recipes})
    return menus


def rows_from_menu(hall: str, date_iso: str, menu: dict, url: str) -> list[dict]:
    rows = []
    for r in menu["recipes"]:
        n = r["nutrients"]
        size = f'{r.get("servingSize", "")} {r.get("servingSizeUnit", "")}'.strip()
        if r.get("servingDescription"):
            size = f'{size} ({r["servingDescription"]})' if size else r["servingDescription"]
        rows.append({
            "hall": hall, "date": date_iso, "meal_period": menu["menu"].get("mealperiodname", ""),
            "station": r.get("category", ""), "item_name": (r.get("shortName") or r.get("description") or "").strip(),
            "ingredients": r["ingredients"],
            "allergens": "; ".join(k for k, v in r["allergens"].items() if v == "Yes"),
            "serving_size": size, "calories": n.get("Calories (kcal)", ""), "source_url": url,
            "dietary_choices": "; ".join(k for k, v in r["dietaryChoices"].items() if v == "Yes"),
            "carbon_kg_co2": n.get("Carbon Footprint (kg CO2)", ""), "recipe_id": r.get("id", ""),
            "menu_name": menu["menu"].get("name", ""), "source_type": "eatec_xml",
        })
    return rows


def fetch_xml(client: httpx.Client, back: int, ahead: int, pulled: str) -> list[dict]:
    log = []
    today = dt.date.today()
    for loc, (folder, hall) in HALLS.items():
        (OUT / folder).mkdir(parents=True, exist_ok=True)
        for off in range(-back, ahead + 1):
            d = today + dt.timedelta(days=off)
            url = XML_URL.format(loc=loc, date=d.strftime("%Y%m%d"))
            try:
                resp = client.get(url)
            except httpx.HTTPError as e:
                log.append({"hall": hall, "date": d.isoformat(), "status": f"error {e}", "url": url, "pulled_at": pulled})
                time.sleep(DELAY)
                continue
            time.sleep(DELAY)
            ok = resp.status_code == 200 and resp.text.lstrip().startswith("<EatecExchange")
            log.append({"hall": hall, "date": d.isoformat(), "status": resp.status_code if ok else f"{resp.status_code} (no menu)", "url": url, "pulled_at": pulled})
            if not ok:
                continue
            # Why: past days are deleted upstream after ~10 days, so never overwrite an older pull with nothing.
            (OUT / folder / f"{d.isoformat()}.xml").write_text(resp.text, encoding="utf-8")
            meta = {"source_url": url, "pulled_at": pulled}
            (OUT / folder / f"{d.isoformat()}.meta.json").write_text(json.dumps(meta))
            for menu in parse_xml(resp.text):
                meal = slug(menu["menu"].get("mealperiodname", "unknown"))
                payload = {**meta, "hall": hall, "date": d.isoformat(), **menu}
                (OUT / folder / f"{d.isoformat()}-{meal}.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"ok   {hall:12} {d}", flush=True)
    return log


def fetch_wayback(client: httpx.Client, pulled: str) -> list[dict]:
    """Archived /menus/ pages; each snapshot holds only the menu for the day it was captured."""
    log = []
    wb_dir = OUT / "wayback"
    wb_dir.mkdir(parents=True, exist_ok=True)
    try:
        cdx = client.get("https://web.archive.org/cdx/search/cdx", params={
            "url": "dining.berkeley.edu/menus/", "output": "json", "filter": "statuscode:200",
            "collapse": "timestamp:8", "from": "2025"}, timeout=60).json()
    except Exception as e:  # noqa: BLE001
        return [{"hall": "*", "date": "", "status": f"wayback cdx error {e!r}", "url": "", "pulled_at": pulled}]
    for row in cdx[1:]:
        ts = row[1]
        path = wb_dir / f"menus_{ts}.html"
        if path.exists() and path.stat().st_size > 5000:
            continue  # already have a real snapshot
        url = f"https://web.archive.org/web/{ts}id_/https://dining.berkeley.edu/menus/"
        status = "error"
        for attempt in range(3):
            time.sleep(WAYBACK_DELAY * (attempt + 1))
            try:
                resp = client.get(url, timeout=90)
            except httpx.HTTPError as e:
                status = f"error {e}"
                continue
            blocked = resp.status_code == 429 or "flagged it as suspected abusive bot traffic" in resp.text
            status = "blocked (429/bot wall)" if blocked else str(resp.status_code)
            if not blocked:
                path.write_text(resp.text, encoding="utf-8")
                break
        log.append({"hall": "*", "date": ts, "status": f"wayback {status}", "url": url, "pulled_at": pulled})
        print(f"wb   {ts} {status}", flush=True)
    return log


def rows_from_wayback(path: Path) -> list[dict]:
    ts = path.stem.split("_")[1]
    url = f"https://web.archive.org/web/{ts}id_/https://dining.berkeley.edu/menus/"
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    rows = []
    for loc in soup.select("li.location-name"):
        title = loc.select_one(".cafe-title")
        hall = WAYBACK_HALLS.get(title.get_text(strip=True) if title else "")
        if not hall:
            continue
        m = re.search(r"(\d{8})", " ".join(loc.get("class", [])))
        date_iso = dt.datetime.strptime(m.group(1), "%Y%m%d").date().isoformat() if m else ts[:8]
        for period in loc.select("li.preiod-name"):
            meal = period.find("span").get_text(" ", strip=True)
            for cat in period.select(".cat-name"):
                station = cat.find("span").get_text(strip=True)
                for li in cat.select("li.recip"):
                    icons = [i.get_text(strip=True) for i in li.select(".allg-tooltip")]
                    diet = [i for i in icons if "Option" in i or i in ("Halal", "Kosher")]
                    rows.append({
                        "hall": hall, "date": date_iso, "meal_period": meal, "station": station,
                        "item_name": li.find("span").get_text(strip=True), "ingredients": "",
                        "allergens": "; ".join(i for i in icons if i not in diet and "Carbon" not in i),
                        "serving_size": "", "calories": "", "source_url": url,
                        "dietary_choices": "; ".join(diet), "carbon_kg_co2": "",
                        "recipe_id": li.get("data-id", ""), "menu_name": "", "source_type": "wayback_html",
                    })
    return rows


def build_csv() -> int:
    """Rebuild menu_items.csv from every file on disk so history accumulates across runs."""
    rows: list[dict] = []
    xml_dates: set[tuple[str, str]] = set()
    for loc, (folder, hall) in HALLS.items():
        for xp in sorted((OUT / folder).glob("????-??-??.xml")):
            date_iso = xp.stem
            meta_p = xp.with_suffix(".meta.json")
            url = json.loads(meta_p.read_text())["source_url"] if meta_p.exists() else XML_URL.format(loc=loc, date=date_iso.replace("-", ""))
            for menu in parse_xml(xp.read_text(encoding="utf-8")):
                rows += rows_from_menu(hall, date_iso, menu, url)
            xml_dates.add((hall, date_iso))
    for wp in sorted((OUT / "wayback").glob("menus_*.html")):
        rows += [r for r in rows_from_wayback(wp) if (r["hall"], r["date"]) not in xml_dates]
    # Why: two snapshots can capture the same serve day; keep one copy per item.
    seen, uniq = set(), []
    for r in rows:
        k = (r["hall"], r["date"], r["meal_period"], r["station"], r["item_name"], r["source_type"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    with open(OUT / "menu_items.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        w.writerows(uniq)
    return len(uniq)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--back", type=int, default=30)
    ap.add_argument("--ahead", type=int, default=10)
    ap.add_argument("--no-xml", action="store_true", help="skip live XML fetch")
    ap.add_argument("--no-wayback", action="store_true")
    a = ap.parse_args()
    pulled = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    OUT.mkdir(parents=True, exist_ok=True)
    log: list[dict] = []
    with httpx.Client(headers={"User-Agent": UA}, timeout=30, follow_redirects=True) as client:
        if not a.no_xml:
            log += fetch_xml(client, a.back, a.ahead, pulled)
        if not a.no_wayback:
            log += fetch_wayback(client, pulled)
    log_p = OUT / "pull_log.csv"
    new = not log_p.exists()
    with open(log_p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["hall", "date", "status", "url", "pulled_at"])
        if new:
            w.writeheader()
        w.writerows(log)
    n = build_csv()
    print(f"menu_items.csv rows={n} pulled_at={pulled}")


if __name__ == "__main__":
    main()
