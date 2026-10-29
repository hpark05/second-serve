"""Fetch public wholesale/institutional food prices and build ingredient_prices.csv.

Every raw file lands under data/raw/prices/ and is recorded in
data/raw/MANIFEST_prices.csv (URL, pull time UTC, bytes, sha256).

Prices come from data/raw/prices/price_quotes.csv, a hand-curated table. Each row
points at one raw file and quotes a snippet of it. This script re-reads the raw
file and refuses any quote whose snippet or price is not literally present, so
every number in the output traces to bytes on disk.

Outputs (all under data/raw/prices/):
  quotes_resolved.csv        one row per quote: verified flag, $/lb, inflation factor
  ingredient_prices.csv      one row per canonical ingredient (all 121 ids)
  sanity_food_cost_per_meal.json   implied food cost per meal vs campus benchmark

Prices are USD per as-purchased (AP) pound. Rice, pasta, oats and dried legumes are
dry weight. The generator converts recipe (edible, cooked) pounds to AP with
data/raw/reference/yields.csv before multiplying.

Run:
  uv run --python-preference only-managed --isolated --with httpx --with beautifulsoup4 \
      --with pandas --with pypdf python scripts/fetch_prices.py [--force] [--offline]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import httpx
import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = RAW / "prices"
MANIFEST = RAW / "MANIFEST_prices.csv"
QUOTES = OUT / "price_quotes.csv"
INGREDIENTS = ROOT / "data" / "recipes" / "ingredients.csv"
DEMAND = ROOT / "data" / "recipes" / "ingredient_demand_weights.csv"
YIELDS = RAW / "reference" / "yields.csv"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
DELAY_S = 1.5
AMS = "https://www.ams.usda.gov/mnreports"

# NYC DCAS bid tabulations (Socrata). Only the item families we quote are pulled.
NYC_ITEMS = ["OLIVE OIL", "COCONUT MILK", "QUINOA", "LENTILS, GREEN", "SALMON FILLETS",
             "VINEGAR, CIDER", "CHEESE, PARMESAN"]
NYC_URL = "https://data.cityofnewyork.us/resource/9k82-ys7w.json?" + urlencode({
    "$where": " OR ".join(f"upper(bid_item) like '{i}%'" for i in NYC_ITEMS),
    "$order": "bid_opening_date DESC, bid_item, bid_price",
    "$limit": "2000",
})

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_SERIES = [
    # Index series used to bring dated quotes to the latest month.
    "CUUR0000SAF11",  # CPI-U food at home
    "WPU02",          # PPI processed foods and feeds
    "WPU023",         # PPI dairy products
    "WPU0211",        # PPI meats, poultry and fish
    # BLS average retail prices, US city average (retail ceiling only). Unregistered API caps a request at 25 series.
    "APU0000701111", "APU0000701312", "APU0000701322", "APU0000702111",
    "APU0000703112", "APU0000703432", "APU0000704111", "APU0000706111",
    "APU0000FF1101", "APU0000708111", "APU0000709112", "APU0000710212",
    "APU0000FS1101", "APU0000711211", "APU0000711311",
    "APU0000711412", "APU0000712112", "APU0000712211", "APU0000712311",
    "APU0000715211", "APU0000717311",
]
BLS_BODY = {"seriesid": BLS_SERIES, "startyear": "2018", "endyear": "2026"}

# key -> (path under data/raw/prices, url, note). POST/JSON sources are handled by key.
SOURCES: dict[str, tuple[str, str, str]] = {
    "usda_lom": ("usda_foods/usdafis_ListofMaterials_sy26-27.xlsx",
                 "https://www.fns.usda.gov/sites/default/files/resource-files/usdafis-ListofMaterials-sy26-27.xlsx",
                 "USDA FNS List of Materials SY2026-27 (Nov 3 2025 price file): est. $/lb paid by USDA"),
    "la_fruit": ("ams_terminal/hc_fv010.pdf", f"{AMS}/hc_fv010.pdf",
                 "AMS Los Angeles Terminal Market Fruit Prices (latest daily edition)"),
    "la_veg": ("ams_terminal/hc_fv020.pdf", f"{AMS}/hc_fv020.pdf",
               "AMS Los Angeles Terminal Market Vegetables Prices (latest daily edition)"),
    "la_onpot": ("ams_terminal/hc_fv030.pdf", f"{AMS}/hc_fv030.pdf",
                 "AMS Los Angeles Terminal Market Onions and Potatoes Prices (latest)"),
    "la_nuts": ("ams_terminal/hc_fv040.pdf", f"{AMS}/hc_fv040.pdf",
                "AMS Los Angeles Terminal Market Nuts Prices (latest)"),
    "ams_beef": ("ams_lpgmn/ams_2453_boxed_beef_daily_pm.pdf", f"{AMS}/ams_2453.pdf",
                 "AMS LM_XB403 National Daily Boxed Beef Cutout and Cuts, $/cwt FOB plant"),
    "ams_pork": ("ams_lpgmn/ams_2498_pork_daily_pm.pdf", f"{AMS}/ams_2498.pdf",
                 "AMS LM_PK602 National Daily Pork Report FOB Plant, $/cwt"),
    "ams_dairy": ("ams_dairy/dairy_market_news_weekly.pdf", f"{AMS}/dywweeklyreport.pdf",
                  "AMS Dairy Market News weekly (CME cash butter/cheese)"),
    "sysco_ar": ("distributor/arkansas_S35_sysco_statewide_groceries_2026q3.pdf",
                 "https://sas.arkansas.gov/wp-content/uploads/4600053586-Price-Changes-Q3-2026-for-Posting.pdf",
                 "Arkansas Office of State Procurement, Sysco statewide groceries contract price sheet Q3 2026"),
    "mcps_groc": ("bids/mcps_9103_groceries_staples_2022-23.pdf",
                  "https://ww2.montgomeryschoolsmd.org/departments/procurement/uploads/9103.12/Bid%20Tab.pdf",
                  "Montgomery County Public Schools (MD) bid 9103 Groceries & Staples, cycle 12, Aug 2022-Jul 2023"),
    "mcps_dairy": ("bids/mcps_9120_dairy_juice_2021-23.pdf",
                   "https://ww2.montgomeryschoolsmd.org/departments/procurement/uploads/9120.6/9120.6%20Bidtab.pdf",
                   "Montgomery County Public Schools (MD) bid 9120 Dairy Products & Fruit Juices, Jul 2021-Jun 2023"),
    "nyc_bids": ("bids/nyc_dcas_bid_tabulations_food_subset.json", NYC_URL,
                 "NYC DCAS Bid Tabulations (Historical) open data, filtered to quoted item families"),
    "bls": ("bls/bls_cpi_ppi_avgprice_2018-2026.json", BLS_URL,
            "BLS API v2 POST body: " + json.dumps(BLS_BODY, separators=(",", ":"))),
    "uf_plan": ("campus/uf_food_service_master_plan_2019.pdf",
                "https://businessservices.ufl.edu/wp-content/uploads/2020/01/Food-Svcs-Master-Plan-Report_Final_December-2019.pdf",
                "University of Florida Food Service Master Plan, Brailsford & Dunlavey, Dec 2019 (plate cost)"),
}

FAMILY = {"usda_lom": "usda_foods", "la_fruit": "ams_terminal", "la_veg": "ams_terminal",
          "la_onpot": "ams_terminal", "la_nuts": "ams_terminal", "ams_beef": "ams_lpgmn",
          "ams_pork": "ams_lpgmn", "ams_dairy": "ams_dairy", "sysco_ar": "distributor",
          "mcps_groc": "school_bid", "mcps_dairy": "school_bid", "nyc_bids": "city_bid",
          "bls": "bls_retail", "computed": "computed"}

DELIVERED = {"distributor", "school_bid", "city_bid"}

MANIFEST_COLS = ["path", "url", "pulled_at_utc", "http_status", "bytes", "sha256", "note"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    with MANIFEST.open() as f:
        return {r["path"]: r for r in csv.DictReader(f)}


def write_manifest(rows: dict[str, dict]) -> None:
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        w.writeheader()
        for k in sorted(rows):
            w.writerow({c: rows[k].get(c, "") for c in MANIFEST_COLS})


def fetch_all(force: bool) -> None:
    man = load_manifest()
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=90) as cx:
        for key, (rel, url, note) in SOURCES.items():
            dest = OUT / rel
            mkey = f"prices/{rel}"
            if dest.exists() and not force and mkey in man:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if key == "bls":
                r = cx.post(url, json=BLS_BODY)
            else:
                r = cx.get(url)
            ok = r.status_code == 200 and len(r.content) > 1000
            if key == "bls":
                ok = ok and r.json().get("status") == "REQUEST_SUCCEEDED"
            print(f"{'ok ' if ok else 'ERR'} {r.status_code} {len(r.content):>9} {rel}")
            if not ok:
                continue
            dest.write_bytes(r.content)
            man[mkey] = {"path": mkey, "url": url,
                         "pulled_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "http_status": r.status_code, "bytes": len(r.content),
                         "sha256": sha256(dest), "note": note}
            write_manifest(man)
            time.sleep(DELAY_S)
    write_manifest(man)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


_text_cache: dict[str, str] = {}


def source_text(key: str) -> str:
    if key not in _text_cache:
        p = OUT / SOURCES[key][0]
        if p.suffix == ".pdf":
            r = PdfReader(str(p))
            _text_cache[key] = norm(" ".join((pg.extract_text() or "") for pg in r.pages))
        else:
            _text_cache[key] = norm(p.read_text())
    return _text_cache[key]


def load_bls() -> dict[str, dict[str, float]]:
    d = json.loads((OUT / SOURCES["bls"][0]).read_text())
    out: dict[str, dict[str, float]] = {}
    for s in d["Results"]["series"]:
        vals = {}
        for row in s["data"]:
            if row["period"].startswith("M") and row["period"] != "M13" and row["value"] not in ("-", ""):
                vals[f"{row['year']}-{row['period'][1:]}"] = float(row["value"])
        out[s["seriesID"]] = vals
    return out


def _read_xlsx_first_sheet(p: Path) -> pd.DataFrame:
    """Minimal xlsx reader so the run command does not need openpyxl."""
    import zipfile
    import xml.etree.ElementTree as ET
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(p) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")))
        sheet = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
        rows = []
        for row in ET.fromstring(z.read(sheet)).iter(f"{{{ns['m']}}}row"):
            cells = {}
            for c in row.findall("m:c", ns):
                col = re.match(r"[A-Z]+", c.get("r")).group(0)
                v = c.find("m:v", ns)
                val = v.text if v is not None else (c.findtext(".//m:t", default="", namespaces=ns))
                if c.get("t") == "s" and v is not None:
                    val = shared[int(v.text)]
                cells[col] = val
            rows.append(cells)
    cols = sorted({k for r in rows for k in r}, key=lambda s: (len(s), s))
    data = [[r.get(c, "") for c in cols] for r in rows]
    return pd.DataFrame(data[1:], columns=[str(x) for x in data[0]])


def load_lom() -> pd.DataFrame:
    try:
        df = pd.read_excel(OUT / SOURCES["usda_lom"][0])
    except ImportError:
        df = _read_xlsx_first_sheet(OUT / SOURCES["usda_lom"][0])
    df.columns = [str(c).strip() for c in df.columns]
    df["Material Number"] = df["Material Number"].astype(str).str.strip()
    return df.set_index("Material Number")


def parse_price(s: str) -> tuple[float, float]:
    s = s.strip().replace("$", "").replace(",", "")
    if "-" in s:
        a, b = s.split("-", 1)
        return float(a), float(b)
    return float(s), float(s)


def verify(key: str, ref: str, price: str) -> tuple[bool, str]:
    """Snippet parts joined by '||' must appear in order within a 4 kB window, with the price."""
    text = source_text(key)
    parts = [norm(p) for p in ref.split("||")]
    start = text.find(parts[0])
    while start != -1:
        win = text[start:start + 4000]
        prices = [p for p in re.split(r"(?<=\d)-(?=[\d.])", price.replace("$", "")) if p]
        if all(p in win for p in parts[1:]) and all(p in win for p in prices):
            return True, win[:160]
        start = text.find(parts[0], start + 1)
    return False, ""


def resolve_quotes(bls: dict, lom: pd.DataFrame) -> list[dict]:
    latest = max(m for m in bls["WPU02"] if m in bls["WPU023"] and m in bls["CUUR0000SAF11"])
    rows = []
    with QUOTES.open() as f:
        for q in csv.DictReader(f):
            if not q["canonical_id"] or q["canonical_id"].startswith("#"):
                continue
            src = q["source"]
            r = dict(q)
            r["family"] = FAMILY[src]
            r["url"] = SOURCES[src][1] if src in SOURCES else ""
            pack = float(q["pack_lb"])
            as_of = q["as_of"]
            if src == "usda_lom":
                row = lom.loc[q["ref"]]
                lo = hi = float(row["Estimated Price per Pound"])
                r["desc"] = norm(str(row["USDA Foods Description"]))
                r["verified"] = "yes"
            elif src == "bls":
                ser = bls.get(q["ref"], {})
                if not ser:
                    r.update(verified="no", desc="series missing")
                    rows.append(r)
                    continue
                as_of = max(ser)
                lo = hi = ser[as_of]
                r["desc"] = f"BLS {q['ref']} {as_of}"
                r["verified"] = "yes"
            else:
                ok, ctx = verify(src, q["ref"], q["price_usd"])
                lo, hi = parse_price(q["price_usd"])
                r["desc"] = ctx
                r["verified"] = "yes" if ok else "no"
            factor = 1.0
            if q["adj"] and q["adj"] != "none":
                idx = bls[q["adj"]]
                base = idx.get(as_of) or idx[min(idx, key=lambda m: abs(_months(m) - _months(as_of)))]
                factor = idx[latest] / base
            r["as_of"] = as_of
            r["adj_factor"] = round(factor, 4)
            r["usd_per_lb_low"] = round(lo / pack * factor, 4)
            r["usd_per_lb_high"] = round(hi / pack * factor, 4)
            r["index_latest"] = latest
            rows.append(r)
    return rows


def _months(ym: str) -> int:
    y, m = ym.split("-")
    return int(y) * 12 + int(m)


def aggregate(quotes: list[dict], ingredients: list[dict]) -> list[dict]:
    good = [q for q in quotes if q.get("verified") == "yes"]
    by_id: dict[str, list[dict]] = {}
    for q in good:
        by_id.setdefault(q["canonical_id"], []).append(q)

    def mid(q: dict) -> float:
        return (q["usd_per_lb_low"] + q["usd_per_lb_high"]) / 2

    # Wholesale-to-retail ratio, measured on ids that have both kinds of quote.
    ratios = []
    for qs in by_id.values():
        nr = [mid(q) for q in qs if q["basis"] != "retail"]
        rt = [mid(q) for q in qs if q["basis"] == "retail"]
        if nr and rt:
            ratios.append(statistics.median(nr) / statistics.median(rt))
    ratios.sort()
    r_med = statistics.median(ratios) if ratios else 0.6
    r_p25 = ratios[len(ratios) // 4] if ratios else 0.5

    # Delivered/source ratio per upstream family, measured on ids quoted by both.
    fam_ratio: dict[str, float] = {}
    fam_pairs: dict[str, list[str]] = {}
    for fam in ("ams_terminal", "usda_foods", "ams_lpgmn", "ams_dairy"):
        rs = []
        for iid, qs in by_id.items():
            up = [mid(q) for q in qs if q["family"] == fam and q["match"] == "exact"]
            dl = [mid(q) for q in qs if q["family"] in DELIVERED and q["match"] == "exact"]
            if up and dl:
                rs.append(statistics.median(dl) / statistics.median(up))
                fam_pairs.setdefault(fam, []).append(iid)
        if rs:
            fam_ratio[fam] = statistics.median(rs)

    out = []
    for ing in ingredients:
        iid = ing["id"]
        qs = by_id.get(iid, [])
        nr = [q for q in qs if q["basis"] != "retail"]
        rt = [q for q in qs if q["basis"] == "retail"]
        note_bits = []
        if nr:
            lows = [q["usd_per_lb_low"] for q in nr]
            highs = [q["usd_per_lb_high"] for q in nr]
            mids = [mid(q) for q in nr]
            low, high = min(lows), max(highs)
            # Why: campus buys delivered; commodity, packer-FOB and terminal quotes sit below that.
            deliv = [mid(q) for q in nr if q["family"] in DELIVERED]
            if deliv:
                mid_v = statistics.median(deliv)
                note_bits.append("mid = delivered-price median")
            else:
                lifted = [mid(q) * fam_ratio.get(q["family"], 1.0) for q in nr]
                mid_v = statistics.median(lifted)
                high = max(high, mid_v)
                rs = sorted({f"{q['family']} x{fam_ratio.get(q['family'], 1.0):.2f}" for q in nr})
                note_bits.append("mid = source price x measured delivered/source ratio (" + ", ".join(rs) + ")")
            fams = {q["family"] for q in nr}
            exact = [q for q in nr if q["match"] == "exact"]
            exact_fams = {q["family"] for q in exact}
            if all(q["match"] == "proxy" for q in nr):
                basis = "proxy"
            elif any(q["basis"] == "wholesale" for q in nr):
                basis = "wholesale"
            else:
                basis = "bid"
            if len(exact_fams) >= 2 and high / max(low, 1e-9) <= 4:
                conf = "high"
            elif exact or len(fams) >= 2:
                conf = "med"
            else:
                conf = "low"
            if rt:
                note_bits.append(f"retail ceiling {statistics.median([mid(q) for q in rt]):.2f}")
            used = nr
        elif rt:
            ret = statistics.median([mid(q) for q in rt])
            low, mid_v, high = ret * r_p25, ret * r_med, ret
            basis, conf, used = "retail", "low", rt
            note_bits.append(f"retail only; wholesale = retail x {r_med:.2f} (p25 {r_p25:.2f}) from overlap items")
        else:
            out.append({"canonical_id": iid, "usd_per_lb_low": "", "usd_per_lb_high": "",
                        "usd_per_lb_mid": "", "price_basis": "", "source_url": "", "year": "",
                        "confidence": "", "note": "NO SOURCE"})
            continue
        src_count: dict[str, int] = {}
        for q in used:
            src_count[q["url"]] = src_count.get(q["url"], 0) + 1
        urls = [u for u, _ in sorted(src_count.items(), key=lambda kv: -kv[1])][:3]
        year = max(int(q["as_of"][:4]) for q in used)
        fam_list = sorted({q["family"] for q in used})
        notes = sorted({q["note"] for q in used if q.get("note")})
        note_bits = [f"{len(used)} quotes ({', '.join(fam_list)})"] + note_bits + notes
        out.append({"canonical_id": iid, "usd_per_lb_low": round(low, 2),
                    "usd_per_lb_high": round(high, 2), "usd_per_lb_mid": round(mid_v, 2),
                    "price_basis": basis, "source_url": " ; ".join(urls), "year": year,
                    "confidence": conf, "note": "; ".join(note_bits)})

    # Computed proxies: buckets with no product of their own.
    priced = {r["canonical_id"]: r for r in out if r["usd_per_lb_mid"] != ""}
    storage = {i["id"]: i["storage"] for i in ingredients}
    for r in out:
        if r["canonical_id"] == "misc_dry":
            dry = [priced[k] for k in priced if storage.get(k) == "dry" and k != "misc_dry"]
            r.update(usd_per_lb_low=round(statistics.median([d["usd_per_lb_low"] for d in dry]), 2),
                     usd_per_lb_mid=round(statistics.median([d["usd_per_lb_mid"] for d in dry]), 2),
                     usd_per_lb_high=round(statistics.median([d["usd_per_lb_high"] for d in dry]), 2),
                     price_basis="proxy", source_url="computed from this file", confidence="low",
                     year=max(int(d["year"]) for d in dry),
                     note=f"median of {len(dry)} dry-storage ingredients; unmatched component bucket")
    return out, r_med, r_p25, len(ratios), fam_ratio, fam_pairs


def sanity(prices: list[dict], ingredients: list[dict], bls: dict) -> dict:
    pr = {r["canonical_id"]: r for r in prices if r["usd_per_lb_mid"] != ""}
    ref = {i["id"]: i.get("reference_ingredient", "") for i in ingredients}
    yields = {}
    with YIELDS.open() as f:
        for y in csv.DictReader(f):
            try:
                yields[y["ingredient"]] = float(y["yield_factor_ep_per_ap"])
            except ValueError:
                pass
    dem = pd.read_csv(DEMAND)
    ep_tot = 0.0
    cost = {"low": 0.0, "mid": 0.0, "high": 0.0}
    missing = 0.0
    for _, d in dem.iterrows():
        iid, ep = d["ingredient_id"], float(d["demand_lb_per_menu_window"])
        if iid not in pr:
            missing += ep
            continue
        y = yields.get(ref.get(iid, ""), 1.0) or 1.0
        ap = ep / y
        ep_tot += ep
        for k in cost:
            cost[k] += ap * float(pr[iid][f"usd_per_lb_{k}"])
    per_ep = {k: v / ep_tot for k, v in cost.items()}
    # EP lb of food per diner per meal: Missouri audit (24.6 g pre-consumer = 5.6% of food
    # reaching retail -> 439 g) and the 1.2 lb FRN/USDA meal-equivalent convention.
    ep_low, ep_high = 24.6 / 0.056 / 453.592, 1.2
    cpi = bls["CUUR0000SAF11"]
    latest = max(cpi)
    fall18 = statistics.mean(cpi[m] for m in ("2018-09", "2018-10", "2018-11", "2018-12"))
    infl = cpi[latest] / fall18
    uf_2018 = 2.81
    uf_ok, _ = verify("uf_plan", "Fall 2018 meal plan utilization of 48% corresponds to an approximate AYCTE plate cost of", "2.81")
    top_ok, _ = verify("uf_plan", "Top residential dining programs can have AYCTE plate costs between 30% and 50% higher", "30")
    res = {
        "weighted_usd_per_edible_lb": {k: round(v, 3) for k, v in per_ep.items()},
        "edible_lb_per_meal": [round(ep_low, 3), ep_high],
        "implied_food_cost_per_meal_usd": {
            "low": round(per_ep["low"] * ep_low, 2),
            "mid": round(per_ep["mid"] * (ep_low + ep_high) / 2, 2),
            "high": round(per_ep["high"] * ep_high, 2)},
        # Missouri pre-consumer waste (5.6% of food reaching retail) is bought but never served.
        "implied_food_cost_per_meal_incl_preconsumer_usd": {
            "low": round(per_ep["low"] * ep_low * 1.056, 2),
            "mid": round(per_ep["mid"] * (ep_low + ep_high) / 2 * 1.056, 2),
            "high": round(per_ep["high"] * ep_high * 1.056, 2)},
        "demand_lb_unpriced_share": round(missing / (missing + ep_tot), 4),
        "benchmark": {
            "uf_aycte_plate_cost_fall2018_usd": uf_2018,
            "uf_quote_verified": uf_ok and top_ok,
            "cpi_food_at_home_factor": round(infl, 4), "cpi_latest_month": latest,
            "uf_plate_cost_inflated_usd": round(uf_2018 * infl, 2),
            "top_programs_plus_30_50pct_usd": [round(uf_2018 * infl * 1.3, 2), round(uf_2018 * infl * 1.5, 2)],
        },
    }
    return res


def main() -> int:
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--force", action="store_true", help="re-download every source")
    ap_.add_argument("--offline", action="store_true", help="skip downloads, rebuild from disk")
    args = ap_.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if not args.offline:
        fetch_all(args.force)

    bls = load_bls()
    lom = load_lom()
    quotes = resolve_quotes(bls, lom)
    qcols = ["canonical_id", "source", "family", "ref", "desc", "verified", "price_usd", "pack_lb",
             "as_of", "adj", "adj_factor", "index_latest", "usd_per_lb_low", "usd_per_lb_high",
             "basis", "match", "url", "note"]
    with (OUT / "quotes_resolved.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=qcols, extrasaction="ignore")
        w.writeheader()
        w.writerows(quotes)
    bad = [q for q in quotes if q.get("verified") != "yes"]
    for q in bad:
        print(f"UNVERIFIED {q['canonical_id']:<22} {q['source']:<10} {q['ref'][:70]}")

    with INGREDIENTS.open() as f:
        ingredients = list(csv.DictReader(f))
    prices, r_med, r_p25, n_ratio, fam_ratio, fam_pairs = aggregate(quotes, ingredients)
    cols = ["canonical_id", "usd_per_lb_low", "usd_per_lb_high", "usd_per_lb_mid", "price_basis",
            "source_url", "year", "confidence", "note"]
    with (OUT / "ingredient_prices.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(prices)

    san = sanity(prices, ingredients, bls)
    san["delivered_to_source_ratio"] = {f: {"ratio": round(r, 3), "n_items": len(fam_pairs[f]),
                                            "items": sorted(fam_pairs[f])} for f, r in fam_ratio.items()}
    san["wholesale_to_retail_ratio"] = {"median": round(r_med, 3), "p25": round(r_p25, 3), "n_items": n_ratio}
    conf: dict[str, int] = {}
    basis: dict[str, int] = {}
    for p in prices:
        conf[p["confidence"] or "none"] = conf.get(p["confidence"] or "none", 0) + 1
        basis[p["price_basis"] or "none"] = basis.get(p["price_basis"] or "none", 0) + 1
    san["coverage"] = {"ingredients": len(prices), "by_confidence": conf, "by_basis": basis,
                       "quotes": len(quotes), "quotes_unverified": len(bad)}
    (OUT / "sanity_food_cost_per_meal.json").write_text(json.dumps(san, indent=2) + "\n")
    print(json.dumps(san, indent=2))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
