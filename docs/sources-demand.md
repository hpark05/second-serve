# Demand-side sources: what Cal Dining serves and how many it feeds

Pulled 2026-10-27 (America/Los_Angeles). Everything is public. Scripts rerun the full pull:

```
uv run --python 3.12 --with httpx --with beautifulsoup4 python scripts/scrape_menus.py
uv run --python 3.12 --with httpx --with beautifulsoup4 --with pypdf python scripts/scrape_volume.py
```

## 1. Menus

**Key finding: Cal Dining does not use Nutrislice.** `caldining.api.nutrislice.com` returned nothing. The menus page at https://dining.berkeley.edu/menus/ is a WordPress plugin (`cal-dining`) that renders HTML from a per-location, per-day **Eatec XML export**. The export path is base64-encoded in each item's `data-location` attribute and is publicly readable:

```
https://dining.berkeley.edu/wp-content/uploads/menus-exportimport/<Location>_<YYYYMMDD>.xml
Location = Crossroads | Cafe_3 | Foothill | Clark_Kerr_Campus
```

Each XML holds every meal period for that day, with menu name, station (`category`), item name, serving size, 20 nutrients (calories, macros, sodium, carbon footprint kg CO2), 12 allergen flags, dietary flags (vegan, vegetarian, halal, kosher), and full ingredient text. This is richer than the HTML.

| What | Result |
|---|---|
| Halls | Crossroads, Café 3, Foothill, Clark Kerr: all succeeded |
| Dates | 2026-10-19 to 2026-11-02, 15 consecutive days per hall (2 full weeks + 1 day) |
| Meal periods | Breakfast (Mon-Fri), Brunch (Sat-Sun), Lunch, Dinner. No late night exists in the current schedule |
| Cycle menus | Named e.g. `XRDS Fall 26 Dinner 08/25/2026 - 12/19/2026`. One semester-long cycle per hall per meal |
| Raw files | `data/raw/menus/<hall>/<date>.xml` (raw), `<date>-<meal>.json` (parsed per meal), `<date>.meta.json` (source URL + pull time) |
| Normalized | `data/raw/menus/menu_items.csv` |
| Pull log | `data/raw/menus/pull_log.csv`: every URL tried and its HTTP status |

**Retention window.** The server keeps about 8 past days and 6 future days. Anything older returns 404 (tested back to 2026-08-25). History only accumulates if the script is rerun. It never deletes files already on disk, and the CSV is rebuilt from everything saved.

**menu_items.csv columns.** The requested ten columns come first: hall, date, meal_period, station, item_name, ingredients, allergens, serving_size, calories, source_url. Five extras follow: dietary_choices, carbon_kg_co2, recipe_id, menu_name, source_type.
- `allergens` lists allergens flagged Yes. Empty means none flagged, not missing.
- `serving_size` is `<amount> <unit> (<description>)`, e.g. `3.93 oz (1 SV)`.
- `calories` is kcal per serving from Eatec.
- `source_type` is `eatec_xml` or `wayback_html`.

**Wayback supplement.** Archived snapshots of /menus/ show only the day they were captured, with names, stations and allergen icons but no nutrition, serving size or ingredients. Rows from them are tagged `wayback_html`. The Internet Archive bot-walled most requests from this IP (HTTP 429). See the gaps section for which snapshots came through.

**Data quirks.** Station names are inconsistent across halls and days ("Centerplate" vs "Center Plate", trailing spaces, "Breakfast " vs "Breakfast"). Some `menu_name` values have stray text appended in the source (e.g. `...12/19/2026tarte`). These are left raw on purpose.

## 2. Volume

Table: `data/raw/volume/hall_volume.csv` with hall, metric, value, unit, period, source_url, notes, plus `quote` (verbatim text from the source) and `quote_verified` (script confirmed the quote is in the saved page). All 41 rows verified. Facts are curated in `scripts/demand_facts.py`.

**Best current figures (official Cal Dining hall pages, undated marketing copy):**

| Hall | Students per day | Source |
|---|---|---|
| Crossroads | 4,400 | dining.berkeley.edu/locations/dining-commons/crossroads/ |
| Café 3 | over 2,500 | .../cafe-3/ |
| Clark Kerr | about 1,200 | .../clark-kerr/ |
| Foothill | **not published** | .../foothill/ page body is empty |

System level: more than 12,000 meal plan holders and over 5 million meals a year across 14 facilities. This comes from a UC Berkeley Dining job posting dated August 2026. A StopWaste case study, undated and likely from about 2012-2014, says over 10,000 meals a day at the four dining halls.

Historic figures are kept with their year in the `period` column. Do not mix them with current numbers without saying so. Examples: Crossroads 800 or 850 seats (2003 vs 2008 sources disagree), 4,000-5,000 meals a day at Crossroads (about 2006), 6,750 students on campus and 10,104 meal plans (2015).

Meal plan rules that shape swipe demand (2026-27):
- Blue & Gold is the default plan for residents: 14 swipes a week, plus 300 flex dollars a semester.
- Unused swipes expire every Saturday at midnight.
- Prices with a plan vs. cash are breakfast $11/$14, lunch $12/$16, dinner $13/$18.

## 3. Hall facts

Table: `data/raw/halls/halls.csv` with hall, attribute, value, source_url, notes, quote, quote_verified. Three kinds of rows:
- **Quoted facts** from hall pages and the FAQ: address, station count, cuisine, all-you-care-to-eat (yes for all four), Halal and Kosher, carry-out policy, feeder residence halls.
- **Parsed hours** from https://dining.berkeley.edu/locations/hours-of-operation/, by meal and day of week.
- **Derived from scraped menus**: dates covered, meal periods seen, stations seen, distinct items, average items per day, cycle menu names.

## Every source

Raw copies and `.txt` text extracts are in `data/raw/volume/` and `data/raw/halls/`. `data/raw/volume/fetch_manifest.json` lists each URL, HTTP status and pull time.

| Slug | URL | Got | Notes |
|---|---|---|---|
| menus_page | https://dining.berkeley.edu/menus/ | 200 | Led to XML export discovery |
| Eatec XML (60 files) | dining.berkeley.edu/wp-content/uploads/menus-exportimport/ | 200 | Primary menu source |
| crossroads, cafe_3, foothill, clark_kerr | dining.berkeley.edu/locations/dining-commons/... | 200 | Daily student counts, stations. Foothill page has no text |
| dining_commons | .../locations/dining-commons/ | 200 | Hall list |
| hours_of_operation | .../locations/hours-of-operation/ | 200 | Weekly hours, holiday notice |
| meal_plans_on_campus_2026_27, _terms_, _faq_, _off_campus_ | dining.berkeley.edu/meal-plans/2026-2027/... | 200 | Plans, prices, swipe rules, AYCE policy |
| job_posting_insidehighered_88071 | careers.insidehighered.com/job/3539856/... | 200 | 12,000 plan holders, 5M meals a year, 14 facilities (Aug 2026) |
| stopwaste_cal_dining | https://www.stopwaste.org/node/4778 | 200 | 10,000 meals a day; 27 tons a year waste reduction. Undated |
| ucb_news_2003_crossroads_release, berkeleyan_2003_crossroads | newsarchive.berkeley.edu | 200 | 800 seats, 40,331 sq ft (2003) |
| ucb_news_2004_green | newsarchive.berkeley.edu | 200 | 8,000 meals a day; 70 tons dining-hall compost (2004) |
| berkeleyan_2007_dining | newsarchive.berkeley.edu | 200 | No usable numbers |
| fsd_colorful_next_step (2007), fsd_shawn_lapean (2008), fsd_going_green (2005), fsd_beyond_50_berkeley (2015) | foodservicedirector.com | 200 | Historic volume, seats, plans sold |
| spoon_behind_the_scenes | spoonuniversity.com (2019) | 200 | 28,000 people a day, Café 3 chicken volume. Low reliability |
| visit_berkeley_halls_ranked | visit.berkeley.edu (2021) | 200 | Qualitative only: Crossroads busiest |
| housing_compare, housing_units_1_2_3, _foothill, _clark_kerr, _blackwell, _stern, _martinez, _residence_halls | housing.berkeley.edu | 200 | Which halls feed which dining commons. **No bed counts on any page** |
| housing_construction_projects | housing site (pantheon mirror) | 200 | 2,400+ beds since 2018; planned 500-seat dining commons |
| regents_mar23_j1_housing_pdf | regents.universityofcalifornia.edu | 200 | Berkeley 9,800 beds, 99% occupied, fall 2022 |
| summer_conf_traditional_halls, summer_conf_suites | summerconferencehousing.berkeley.edu | 200 | Summer guest capacity only |
| dailycal_meal_points_to_swipes, dailycal_how_overpriced, dailycal_late_night_returns, dailycal_meal_swipe_business | dailycal.org | 200 | Swipe-resale app (Jan 2025). Others are older archive pieces with no publish date in the page |
| housing_brochure_pdf | housing.berkeley.edu/wp-content/uploads/CALH_250202_... | **404** | Removed |
| caldining_on_meal_plans_24_25_pdf, caldining_on_campus_brochure_22_23_pdf | dining / caldining PDFs | **404** | Removed |
| wikipedia_student_housing | en.wikipedia.org | **403** | Blocked even with a descriptive user agent |
| aashe_stars_2018_op8 | reports.aashe.org | 200 but **login wall** | STARS food data needs an AASHE account |
| wayback_foothill_page | web.archive.org | **429** | Internet Archive rate limit |
| Nutrislice API | caldining.api.nutrislice.com | empty | Not used by Cal Dining |

## Gaps (what we could not get)

1. **No swipe counts, per-meal headcounts, or waste by hall.** Cal Dining reads swipes on the Cal 1 Card and tracks waste with LeanPath, but publishes neither. The per-hall "students per day" figures are rounded marketing copy. For forecasting, ask Cal Dining for swipe exports by hall and meal period, and for LeanPath waste logs. That is the single most valuable request.
2. **No residents per hall or seats per hall from a current source.** Housing pages give room types but no bed counts. The only seat count is Crossroads, from 2003 and 2008 sources, and they disagree (800 vs 850). Summer conference capacities exist but undercount the academic year, because they assume doubles while first-years are mostly in triples. Foothill has no published daily headcount at all.
3. **Menu history is short and must be accumulated.** The server keeps about two weeks. We have 15 days per hall for Fall 2026 plus whatever Wayback snapshots came through. We do not yet know the cycle length, so it is unclear whether the cycle repeats weekly or over several weeks. Rerunning the scraper daily or weekly fixes this at no cost.

Smaller gaps:
- There are no production quantities (pans, portions made), only what is offered.
- The Daily Californian has no recent articles with swipe numbers.
- Late night service is not in the current hours, though the Daily Californian reported it returning at Crossroads and Foothill in an earlier year.
