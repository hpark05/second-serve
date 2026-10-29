"""Fetch public sources on Cal Dining diner volume and hall facts.

Step 1 (fetch): saves each source raw to data/raw/volume/ or data/raw/halls/ plus a .txt text extract.
Step 2 (tables): builds hall_volume.csv and halls.csv from the curated FACTS in scripts/demand_facts.py.
Each fact carries a verbatim quote; the script checks the quote appears in the saved text and
records quote_verified=yes/no, so nothing in the tables is unsourced.

Run:  uv run --with httpx --with beautifulsoup4 --with pypdf python scripts/scrape_volume.py [--tables-only]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
VOL = ROOT / "data" / "raw" / "volume"
HALLS_DIR = ROOT / "data" / "raw" / "halls"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
DELAY = 1.0

# (slug, url, dest) — dest "halls" or "volume"
SOURCES = [
    ("dining_commons", "https://dining.berkeley.edu/locations/dining-commons/", "halls"),
    ("crossroads", "https://dining.berkeley.edu/locations/dining-commons/crossroads/", "halls"),
    ("cafe_3", "https://dining.berkeley.edu/locations/dining-commons/cafe-3/", "halls"),
    ("foothill", "https://dining.berkeley.edu/locations/dining-commons/foothill/", "halls"),
    ("clark_kerr", "https://dining.berkeley.edu/locations/dining-commons/clark-kerr/", "halls"),
    ("hours_of_operation", "https://dining.berkeley.edu/locations/hours-of-operation/", "halls"),
    ("menus_page", "https://dining.berkeley.edu/menus/", "halls"),
    ("meal_plans_on_campus_2026_27", "https://dining.berkeley.edu/meal-plans/2026-2027/living-on-campus/", "volume"),
    ("meal_plans_terms_on_campus_2026_27", "https://dining.berkeley.edu/meal-plans/2026-2027/living-on-campus/terms-and-conditions-living-on-campus/", "volume"),
    ("meal_plans_faq_2026_27", "https://dining.berkeley.edu/meal-plans/2026-2027/faq/", "volume"),
    ("meal_plans_off_campus_2026_27", "https://dining.berkeley.edu/meal-plans/2026-2027/living-off-campus/", "volume"),
    ("housing_compare", "https://housing.berkeley.edu/compare", "volume"),
    ("housing_brochure_pdf", "https://housing.berkeley.edu/wp-content/uploads/CALH_250202_HousingBrochure_COVER_UPDATE-Web.pdf", "volume"),
    ("summer_conf_traditional_halls", "https://summerconferencehousing.berkeley.edu/host-a-conference/accommodations/traditional-residence-halls/", "volume"),
    ("summer_conf_suites", "https://summerconferencehousing.berkeley.edu/host-a-conference/accommodations/suites/", "volume"),
    ("wikipedia_student_housing", "https://en.wikipedia.org/w/index.php?title=University_of_California,_Berkeley_student_housing&action=raw", "volume"),
    ("housing_units_1_2_3", "https://housing.berkeley.edu/explore-housing-options/residence-halls/units-1-2-and-3-residence-halls/", "volume"),
    ("housing_foothill", "https://housing.berkeley.edu/explore-housing-options/residence-halls/foothill-residence-hall/", "volume"),
    ("housing_clark_kerr", "https://housing.berkeley.edu/explore-housing-options/residence-halls/clark-kerr-residence-hall/", "volume"),
    ("housing_blackwell", "https://housing.berkeley.edu/explore-housing-options/residence-halls/blackwell-residence-hall/", "volume"),
    ("housing_stern", "https://housing.berkeley.edu/explore-housing-options/residence-halls/stern-residence-hall/", "volume"),
    ("housing_martinez", "https://housing.berkeley.edu/explore-housing-options/residence-halls/martinez-commons-residence-hall/", "volume"),
    ("housing_residence_halls", "https://housing.berkeley.edu/explore-housing-options/residence-halls/", "volume"),
    ("housing_construction_projects", "https://live-wp-sa-housing-1.pantheon.berkeley.edu/resources/campus-housing-upcoming-construction-and-redevelopment-projects/", "volume"),
    ("regents_mar23_j1_housing_pdf", "https://regents.universityofcalifornia.edu/regmeet/mar23/j1.pdf", "volume"),
    ("caldining_on_meal_plans_24_25_pdf", "https://dining.berkeley.edu/wp-content/uploads/2024/04/ON-Meal-Plans-24-25.pdf", "volume"),
    ("caldining_on_campus_brochure_22_23_pdf", "https://caldining.berkeley.edu/wp-content/uploads/2022/04/On-Campus-Brochure-2022-2023.pdf", "volume"),
    ("wayback_foothill_page", "https://web.archive.org/web/2025id_/https://dining.berkeley.edu/locations/dining-commons/foothill/", "halls"),
    ("ucb_news_2003_crossroads_release", "https://newsarchive.berkeley.edu/news/media/releases/2003/01/27_dining.html", "volume"),
    ("berkeleyan_2003_crossroads", "https://newsarchive.berkeley.edu/news/berkeleyan/2003/02/12_xrd.shtml", "volume"),
    ("ucb_news_2004_green", "https://newsarchive.berkeley.edu/news/media/releases/2004/08/19_green.shtml", "volume"),
    ("berkeleyan_2007_dining", "https://newsarchive.berkeley.edu/news/berkeleyan/2007/04/12_dining.shtml", "volume"),
    ("fsd_colorful_next_step", "https://www.foodservicedirector.com/menu-trends/a-colorful-next-step-for-cal-dining", "volume"),
    ("fsd_shawn_lapean", "https://www.foodservicedirector.com/colleges-universities/shawn-lapean", "volume"),
    ("fsd_going_green", "https://www.foodservicedirector.com/foodservice-industries/going-green", "volume"),
    ("fsd_beyond_50_berkeley", "https://www.foodservicedirector.com/colleges-universities/beyond-the-50-power-players-university-of-california-berkeley", "volume"),
    ("job_posting_insidehighered_88071", "https://careers.insidehighered.com/job/3539856/cook-5523c-berkeley-dining-88071/", "volume"),
    ("stopwaste_cal_dining", "https://www.stopwaste.org/node/4778", "volume"),
    ("aashe_stars_2018_op8", "https://reports.aashe.org/institutions/university-of-california-berkeley-ca/report/2018-03-02/OP/food-dining/OP-8", "volume"),
    ("visit_berkeley_halls_ranked", "https://visit.berkeley.edu/news/crossroads-cal%E2%80%99s-dining-halls-ranked", "volume"),
    ("spoon_behind_the_scenes", "https://spoonuniversity.com/school/uc-berkeley/behind-the-scenes-of-caldining/", "volume"),
    ("dailycal_meal_points_to_swipes", "https://www.dailycal.org/archives/cal-dining-replaces-meal-points-with-meal-swipes/article_2afe3948-fc51-5d4e-b869-44e2cf2b0d3d.html", "volume"),
    ("dailycal_how_overpriced", "https://www.dailycal.org/archives/how-overpriced-is-cal-dining/article_34ee9153-bf31-582c-acdb-68fcd69854c1.html", "volume"),
    ("dailycal_late_night_returns", "https://www.dailycal.org/archives/late-night-dining-services-return-to-crossroads-and-foothill/article_b101cab3-d296-515e-ad7b-5b53ec2f1a2f.html", "volume"),
    ("dailycal_meal_swipe_business", "https://www.dailycal.org/news/campus/student-run-meal-swipe-business-shuts-down-after-uc-berkeley-dining-response/article_985402b2-4f70-4341-b4ca-6a3255d5deb5.html", "volume"),
]


def to_text(content: bytes, ctype: str) -> str:
    if "pdf" in ctype or content[:5] == b"%PDF-":
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(content)).pages)
    if "text/plain" in ctype or "x-wiki" in ctype:
        return content.decode("utf-8", "replace")
    soup = BeautifulSoup(content, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return re.sub(r"[ \t]+", " ", soup.get_text("\n", strip=True))


def fetch_all() -> None:
    pulled = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    manifest = []
    with httpx.Client(headers={"User-Agent": UA}, timeout=40, follow_redirects=True) as c:
        for slug, url, dest in SOURCES:
            d = HALLS_DIR if dest == "halls" else VOL
            d.mkdir(parents=True, exist_ok=True)
            rec = {"slug": slug, "url": url, "pulled_at": pulled, "dest": str(d.relative_to(ROOT))}
            try:
                # Why: Wikipedia rejects browser-like UAs from scripts; it asks for a descriptive one.
                hdrs = {"User-Agent": "Second Serve-research/0.1 (UC Berkeley class prototype; python-httpx)"} if "wikipedia.org" in url else None
                r = c.get(url, headers=hdrs)
                ctype = r.headers.get("content-type", "")
                ext = "pdf" if ("pdf" in ctype or r.content[:5] == b"%PDF-") else ("txt.raw" if "x-wiki" in ctype or "text/plain" in ctype else "html")
                (d / f"{slug}.{ext}").write_bytes(r.content)
                text = to_text(r.content, ctype) if r.status_code == 200 else ""
                (d / f"{slug}.txt").write_text(f"SOURCE: {url}\nPULLED: {pulled}\nHTTP: {r.status_code}\n\n{text}", encoding="utf-8")
                rec |= {"status": r.status_code, "final_url": str(r.url), "file": f"{slug}.{ext}", "text_chars": len(text)}
            except Exception as e:  # noqa: BLE001 — record any failure and keep going
                rec |= {"status": f"error: {e!r}"[:200]}
            manifest.append(rec)
            print(rec.get("status"), slug, flush=True)
            time.sleep(DELAY)
    (VOL / "fetch_manifest.json").write_text(json.dumps(manifest, indent=1))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("–", "-").replace("—", "-")).lower()


def verify(slug: str, quote: str) -> str:
    for d in (VOL, HALLS_DIR):
        p = d / f"{slug}.txt"
        if p.exists():
            return "yes" if norm(quote) in norm(p.read_text(encoding="utf-8")) else "no"
    return "no (source not saved)"


def build_tables() -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    from demand_facts import HALL_FACTS, VOLUME_FACTS  # noqa: E402

    url_of = {s: u for s, u, _ in SOURCES}
    with open(VOL / "hall_volume.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hall", "metric", "value", "unit", "period", "source_url", "notes", "quote", "quote_verified"])
        for hall, metric, value, unit, period, slug, notes, quote in VOLUME_FACTS:
            w.writerow([hall, metric, value, unit, period, url_of.get(slug, slug), notes, quote, verify(slug, quote)])
    with open(HALLS_DIR / "halls.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hall", "attribute", "value", "source_url", "notes", "quote", "quote_verified"])
        for hall, attr, value, slug, notes, quote in HALL_FACTS:
            w.writerow([hall, attr, value, url_of.get(slug, slug), notes, quote, verify(slug, quote) if quote else "derived"])
        for hall, attr, value in parse_hours():
            w.writerow([hall, attr, value, url_of["hours_of_operation"], "parsed from weekly hours table", "", "parsed"])
        for hall, attr, value in menu_derived():
            w.writerow([hall, attr, value, "data/raw/menus/menu_items.csv", "derived from scraped Eatec XML menus", "", "derived"])
    print("tables written")


DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
HOURS_HALLS = {"Crossroads": "Crossroads", "Café 3": "Café 3", "Foothill": "Foothill", "Clark Kerr": "Clark Kerr"}


def parse_hours() -> list[tuple[str, str, str]]:
    """Weekly hours table on /locations/hours-of-operation/: hall, header row of 7 days, then meal + 7 cells."""
    p = HALLS_DIR / "hours_of_operation.txt"
    if not p.exists():
        return []
    lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    out = []
    for i, l in enumerate(lines):
        if l in HOURS_HALLS and lines[i + 1:i + 9][1:8] == DAYS:
            j = i + 9
            while j + 7 < len(lines) and lines[j] in ("Breakfast", "Lunch/Brunch", "Dinner", "Late Night", "Brunch", "Lunch"):
                meal, cells = lines[j], lines[j + 1:j + 8]
                out.append((HOURS_HALLS[l], f"hours_{meal.lower().replace('/', '_')}", "; ".join(f"{d[:3]} {c}" for d, c in zip(DAYS, cells))))
                j += 8
    return out


def menu_derived() -> list[tuple[str, str, str]]:
    p = ROOT / "data" / "raw" / "menus" / "menu_items.csv"
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["source_type"] == "eatec_xml"]
    out = []
    for hall in sorted({r["hall"] for r in rows}):
        hr = [r for r in rows if r["hall"] == hall]
        dates = sorted({r["date"] for r in hr})
        out += [
            (hall, "menu_dates_scraped", f"{dates[0]} to {dates[-1]} ({len(dates)} days)"),
            (hall, "meal_periods_observed", "; ".join(sorted({r["meal_period"] for r in hr}))),
            (hall, "stations_observed", "; ".join(sorted({r["station"] for r in hr}))),
            (hall, "distinct_items_observed", str(len({r["item_name"] for r in hr}))),
            (hall, "avg_items_per_day", f"{len(hr) / len(dates):.0f}"),
            (hall, "cycle_menu_names", "; ".join(sorted({r["menu_name"] for r in hr}))),
        ]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables-only", action="store_true")
    a = ap.parse_args()
    if not a.tables_only:
        fetch_all()
    if (Path(__file__).parent / "demand_facts.py").exists():
        build_tables()
