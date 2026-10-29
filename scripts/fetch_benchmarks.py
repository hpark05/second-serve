"""Download raw public sources for Second Serve supply/loss calibration.

Every file lands under data/raw/ and is recorded in data/raw/MANIFEST_supply.csv
with source URL, pull timestamp (UTC), bytes and sha256, so numbers in the
derived tables can be traced back to a byte-identical copy.

Run:  uv run --with httpx python scripts/fetch_benchmarks.py [--force]
"""
from __future__ import annotations

import csv
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "MANIFEST_supply.csv"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
DELAY_S = 1.5

ERS = "https://www.ers.usda.gov/media"
FBG = "https://foodbuyingguide.fns.usda.gov/Content/TablesFBG"

# (relative path under data/raw, url)
SOURCES: list[tuple[str, str]] = [
    # USDA ERS Loss-Adjusted Food Availability (LAFA) workbooks.
    ("reference/ers_lafa/dairy.xlsx", f"{ERS}/5382/dairy-fluid-milk-cream-and-other-products.xlsx"),
    ("reference/ers_lafa/fats-and-oils.xls", f"{ERS}/5384/fats-and-oils-added.xls"),
    ("reference/ers_lafa/fruit.xlsx", f"{ERS}/5388/fruit.xlsx"),
    ("reference/ers_lafa/grains.xlsx", f"{ERS}/5390/grains.xlsx"),
    ("reference/ers_lafa/meat-poultry-fish-eggs-nuts.xls", f"{ERS}/5392/meat-poultry-fish-eggs-and-nuts.xls"),
    ("reference/ers_lafa/vegetables.xlsx", f"{ERS}/5396/vegetables.xlsx"),
    ("reference/ers_lafa/sugar-and-sweeteners.xlsx", f"{ERS}/5394/sugar-and-sweeteners-added.xlsx"),
    # USDA FNS Food Buying Guide for Child Nutrition Programs (yield tables).
    ("reference/fbg/USDA_FBG_Introduction.pdf", f"{FBG}/USDA_FBG_Introduction.pdf"),
    ("reference/fbg/USDA_FBG_Section1_MeatsAndMeatAlternates.pdf", f"{FBG}/USDA_FBG_Section1_MeatsAndMeatAlternates.pdf"),
    ("reference/fbg/USDA_FBG_Section2_Vegetables.pdf", f"{FBG}/USDA_FBG_Section2_Vegetables.pdf"),
    ("reference/fbg/USDA_FBG_Section3_Fruits.pdf", f"{FBG}/USDA_FBG_Section3_Fruits.pdf"),
    ("reference/fbg/USDA_FBG_Section4_Grains.pdf", f"{FBG}/USDA_FBG_Section4_Grains.pdf"),
    ("reference/fbg/USDA_FBG_Section5_Milk.pdf", f"{FBG}/USDA_FBG_Section5_Milk.pdf"),
    ("reference/fbg/USDA_FBG_Section6_OtherFoods.pdf", f"{FBG}/USDA_FBG_Section6_OtherFoods.pdf"),
    # USDA FoodData Central, SR Legacy bulk CSV (kcal + household portion weights).
    ("reference/fdc/FoodData_Central_sr_legacy_food_csv_2018-04.zip",
     "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"),
    # FSIS FoodKeeper. Why: fsis.usda.gov returns 403 to scripted clients, so we
    # take a public GitHub copy of the same FSIS export and record that in the manifest.
    ("reference/foodkeeper/FoodKeeper-Data.xls",
     "https://raw.githubusercontent.com/BrandonChenze/FoodKeeperResearch/HEAD/datasets/FoodKeeper-Data.xls"),
    ("reference/foodkeeper/FoodKeeper-Data.official.xls",
     "https://www.fsis.usda.gov/shared/data/EN/FoodKeeper-Data.xls"),
    # FDA refrigerator/freezer chart: cross-check for FoodKeeper meat, egg and leftover rows.
    ("reference/fda/fda_refrigerator_freezer_chart.pdf", "https://www.fda.gov/media/74435/download"),
    # Waste benchmark documents (general, non-UC). UC docs live in benchmarks/uc/.
    ("benchmarks/docs/ers_eib121_buzby_2014.pdf",
     "https://www.ers.usda.gov/sites/default/files/_laserfiche/publications/43833/43680_eib121.pdf"),
]
EXTRA_SOURCES_FILE = ROOT / "scripts" / "benchmark_doc_urls.csv"


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


def save_manifest(rows: dict[str, dict]) -> None:
    cols = ["path", "url", "pulled_at_utc", "http_status", "bytes", "sha256", "note"]
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for k in sorted(rows):
            w.writerow({c: rows[k].get(c, "") for c in cols})


def all_sources() -> list[tuple[str, str]]:
    out = list(SOURCES)
    if EXTRA_SOURCES_FILE.exists():
        with EXTRA_SOURCES_FILE.open() as f:
            out += [(r["path"], r["url"]) for r in csv.DictReader(f)]
    return out


def main(force: bool) -> int:
    manifest = load_manifest()
    failures = 0
    with httpx.Client(headers={"User-Agent": UA, "Accept": "*/*"}, follow_redirects=True,
                      timeout=120) as client:
        for rel, url in all_sources():
            dest = RAW / rel
            if dest.exists() and not force and rel in manifest and manifest[rel].get("sha256"):
                print(f"skip  {rel}")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            try:
                r = client.get(url)
                status = r.status_code
                ok = status == 200 and len(r.content) > 1000 and b"Access Denied" not in r.content[:2000]
            except httpx.HTTPError as e:
                status, ok, r = f"error:{type(e).__name__}", False, None
            if ok:
                dest.write_bytes(r.content)
                manifest[rel] = {"path": rel, "url": url, "pulled_at_utc": now, "http_status": status,
                                 "bytes": dest.stat().st_size, "sha256": sha256(dest), "note": ""}
                print(f"ok    {rel} ({dest.stat().st_size:,} B)")
            else:
                failures += 1
                manifest[rel] = {"path": rel, "url": url, "pulled_at_utc": now, "http_status": status,
                                 "bytes": 0, "sha256": "", "note": "download failed or blocked"}
                print(f"FAIL  {rel} [{status}]")
            time.sleep(DELAY_S)
    save_manifest(manifest)
    print(f"manifest: {MANIFEST.relative_to(ROOT)}  failures: {failures}")
    return 0


if __name__ == "__main__":
    sys.exit(main(force="--force" in sys.argv))
