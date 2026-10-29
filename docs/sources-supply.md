# Supply and loss side: public sources

Pulled 2026-10-27. Every number below is traceable to a file under `data/raw/`. Byte-level provenance (URL, UTC pull time, sha256) is in `data/raw/MANIFEST_supply.csv`.

## Reproduce

```bash
uv run --with httpx python scripts/fetch_benchmarks.py          # downloads; --force to re-pull
uv run --python-preference only-managed --isolated \
  --with pandas --with openpyxl --with xlrd python scripts/build_reference_tables.py
```

`scripts/benchmark_doc_urls.csv` holds the extra document URLs that the fetch script reads. Use the uv-managed Python: the system Anaconda leaks NumPy 1.x modules into pandas.

## Output tables

| File | Rows | Built how |
|---|---|---|
| data/raw/benchmarks/waste_benchmarks.csv | 35 | Hand-curated from saved docs; each row checked against saved text |
| data/raw/benchmarks/uc_numbers.csv | 40 | Hand-curated; notes in data/raw/benchmarks/uc/NOTES.md |
| data/raw/reference/shelf_life.csv | 534 | Parsed from FoodKeeper. 110 reference rows plus 424 canonical rows covering 120 of 121 recipe ingredients |
| data/raw/reference/loss_rates.csv | 366 | Parsed from ERS LAFA, latest year per commodity sheet. 263 commodity rows plus 103 canonical rows |
| data/raw/reference/ingredients.csv | 40 | FDC SR Legacy kcal + case weights from AH-697 / USDA Foods list / FBG |
| data/raw/reference/yields.csv | 40 | Parsed from FBG yield-table Excel files |

Column notes:

- **loss_rates.csv.** `retail_loss_pct` is LAFA "loss from retail/institutional to consumer level", the stage closest to a campus kitchen. `consumer_loss_pct` is LAFA "Other (cooking loss and uneaten food)". The extra columns hold nonedible share, primary-to-retail loss, total loss, and the year.
- **shelf_life.csv.** `clock_starts` says whether FoodKeeper counts from purchase, after opening, or after cooking. `original` keeps the FoodKeeper text, such as "3-5 Days". Months convert at 30 days and years at 365.
- **yields.csv.** `yield_factor_ep_per_ap` is lb of edible or cooked food per lb as purchased. `yield_method` shows whether it was read from an FBG "1 lb AP = X lb" note (`lb_note`), computed from drained can weight (`can_drained`), computed from FBG servings × an FDC cup weight (`servings_x_cup_cooked`), or assumed 1.0 for no-trim items (`ready_to_serve`, `assumed`). Grain and legume factors are above 1 because they gain water.
- **ingredients.csv.** `unit` and `lb_per_unit` are an institutional case. `unit_note` flags proxies and gaps. `kcal_per_100g` is the raw form from FoodData Central (FDC), `g_per_cup` comes from FDC portions, and `lafa_commodity` joins to loss_rates.csv.

## Canonical join (recipe ingredients)

`scripts/canonical_reference_map.csv` maps every id in data/recipes/ingredients.csv to FoodKeeper product ids and one ERS loss-adjusted commodity. Each mapping carries a confidence and a note. Rows with `canonical_id` set are the ones to join on. Rows with a blank `canonical_id` are the original 40-ingredient reference rows.

- **shelf_life.csv extra columns.**
  - `canonical_id` is the join key.
  - `shelf_life_days` is the midpoint of the low and high values.
  - `confidence` is high when FoodKeeper lists the same food, med for the closest form (for example soft cheese for feta), and low for a proxy.
  - `primary_storage` is 1 on the row matching the recipe file's storage mode: cooler maps to refrigerator, dry to pantry, freezer to freezer. When FoodKeeper lists only an after-opening value, that row is used.
  - "Indefinitely" (salt, vinegar) is encoded as 3,650 days, with `original` left as "Indefinitely".
- **loss_rates.csv extra columns.** `canonical_id`, `confidence` (med for a direct ERS commodity, low for a proxy), `note` and `lafa_layout`.

Demand-weighted coverage, from data/recipes/ingredient_demand_weights.csv:

| Measure | % of demand lb |
|---|---|
| Any shelf-life row | 99.97 |
| Shelf-life row in the ingredient's own storage mode | 98.5 |
| Shelf-life confidence high or med | 97.6 |
| Loss-rate row | 82.0 |

Remaining shelf-life gaps:
- **misc_dry** is a catch-all bucket with nothing to source.
- **Milk** has only a freezer row, because FoodKeeper says "package use-by date" for the fridge.
- **Bananas** are stored dry in the recipe file, but FoodKeeper gives only "when ripe" for the pantry. The fridge and freezer rows exist.
- **Soft-serve mix** has only an ice-cream freezer row, at low confidence.
- **Sour cream and cooking wine** use proxies (sour-cream dips, white wine) at low confidence, because FoodKeeper gives only "use-by date" text.

ERS publishes no loss series for prepared soup, prepared dessert, plant-based meat, tofu, prepared entrees, plant eggs, vinegar, spices, salt, soy sauce, mustard/ketchup, hot sauce, jam, prepared sauces, soup base, plant milk, cooking wine or coffee/tea. They are left blank rather than proxied. Prepared soup alone is the largest by demand.

LAFA layout fix: the aggregate sheets ("Fresh vegetables", "Total cheese", "Total grains", sweetener totals and similar) publish only weights. The first build read the wrong column on 44 such rows. They are now derived from successive weights (`lafa_layout=derived_from_weights`). Canned items that gain weight before retail now show a negative `primary_to_retail_loss_pct`.

## Source inventory

Confidence means how far a generator can rely on the number. High is a government or peer-reviewed measured dataset. Med is a measured case study or an official extrapolation. Low is a vendor claim or a secondary relay.

### Reference data

| Source | Saved as | Used for | Confidence |
|---|---|---|---|
| USDA ERS Loss-Adjusted Food Availability (7 workbooks incl. sugar and sweeteners), latest years 1994 to 2023 | reference/ers_lafa/*.xls(x) | loss_rates.csv | High as a national series, med for an institutional kitchen |
| FSIS FoodKeeper, data version 128 (2018-09-06) | reference/foodkeeper/FoodKeeper-Data.xls | shelf_life.csv | High. fsis.usda.gov returns 403 to scripts, so the file is a public GitHub copy of the FSIS export (URL in manifest). Spot-check against the live app before quoting. |
| USDA FNS Food Buying Guide yield tables (Excel, 6 sections, FBG updated 2025) | reference/fbg/yield_tables/ | yields.csv | High for as-purchased to edible-portion yields |
| USDA FNS Food Buying Guide section PDFs | reference/fbg/*.pdf | Context only; the yield tables are in the Excel files | n/a |
| USDA FoodData Central, SR Legacy CSV (2018-04) | reference/fdc/*.zip | kcal, cup weights | High |
| USDA ERS AH-697 Weights, Measures and Conversion Factors (1992), Table 6 | reference/ah697/ | Produce, egg, milk and butter case weights | Med, because it is 1992 and pack sizes drift |
| USDA Foods Available List SY2026-27 (Dec 2025) | reference/usda_foods/ | Protein, dairy and grain case packs | High for USDA Foods packs, med as a proxy for commercial packs |

### Waste benchmarks (data/raw/benchmarks/docs/)

| Source | Key numbers | Confidence |
|---|---|---|
| Leanpath blog, Shakman, 2018-08-10 | Pre-consumer waste 4-10% of purchases by value. Total 8-15%. Overproduction 50-60% of pre-consumer. Tracking cuts it 50% or more. | Low. Vendor aggregate with no primary study, though widely repeated. |
| Leanpath blog, ASU, 2018 | 40% plate-waste cut over 5 halls serving ~12k meals/day. The headline says 39%. | Low |
| Costello et al. 2015, Renewable Agriculture and Food Systems (Univ. of Missouri, 4 AYCE halls, Feb-May 2014) | Pre-consumer 5.6% and post-consumer 10.7% of food mass reaching retail. 24.6 g pre-consumer waste per customer at one hall. Fruit and vegetables are the largest waste stream by weight, then grains. | High. Peer-reviewed and weighed. |
| US EPA 2019 Wasted Food Report (2024 corrected) | Colleges generate 0.36-0.44 lb per student per meal, 624,371 tons/yr in total. Food service sends 72% of its wasted food to landfill and composts 8%. | Med-high. Official extrapolation from 10 studies. |
| RecyclingWorks MA 2022 colleges guide; RIT NYSP2I estimator 2024 | 0.35 lb/meal. 141.75 lb/yr per residential student and 37.8 lb/yr per non-residential student (Draper/Lennon 2001 lineage). | Med |
| RecyclingWorks MA, UMass Amherst case study (2017) | Pre-consumer waste is about half trim and half overproduction. Trayless dining cut waste 30%. "9% food waste rate vs 15% national average". | Med. The 15% has no source. |
| Bon Appétit / NRDC press release 2019 | 2.18 oz edible plate waste per guest per meal in higher ed, vs 1.03 oz in corporate cafes. 112 lb per student per school year. | Med |
| University of Illinois ACES news 2021 | A 2016 audit found 3.3 oz of waste per meal served, 14,875 lb/week across 6 halls. Plate waste was 15.8% of food taken on round plates vs 11.8% on oval. | Med |
| Kim & Morawski via Pacific Standard; Aramark via Food Service Director | Trayless: 111 g to 76 g per diner (-32%). Aramark: -25 to 30%, or 1.2-1.8 oz per meal. | Med for Kim & Morawski, low for Aramark |
| ReFED / MCURC "Repurpose with a Purpose" report (Oct 2024) | Overproduction is 23% of foodservice food waste (ReFED). Foodservice surplus was 13M tons in 2022, 80.6% landfilled. Sprint savings were $19,449 in one month across 9 schools. Stanford cut purchasing by 200-300 lb/day. BU cut edible plate waste by more than 50%. | Med |
| ReFED Insights Engine key findings; ReFED problem page | 70.2% of foodservice uneaten food is plate waste (2019). | Med |
| WRAP 2013, UK Hospitality and Food Service | Food waste splits 21% spoilage, 45% preparation and 34% plate. Education waste costs £0.22 per meal. | Med, but it is UK data |
| Winnow press release, 2026-04-29, via Hotel Dive | Commercial kitchens waste 5-15% of purchases. Named customers cut waste 26-64%. | Low. Vendor claim. The site 403s scripts; read via WebFetch on 2026-10-27 and not saved locally. |
| USDA ERS EIB-121 (Buzby 2014) | 31% of US food was lost at retail plus consumer level in 2010: 10% retail and 21% consumer. | High |
| Food Recovery Network FY19 annual report | 4,565 lb recovered per chapter per year. 881,063 lb total, or 734,219 meals. | Med |

### UC Berkeley and UC system

See data/raw/benchmarks/uc/NOTES.md for page references. These four were re-verified against the saved files:

- **Donations.** Cal Dining donates over 50,000 lb, about 40,000 meals, each semester. The page is undated.
- **Diversion.** Berkeley diverted 53% of waste in FY2024-25, or 55% counting construction waste. The UC goal is 90%.
- **Landfill audit.** 41% of the audited landfill stream was compostable, but the audit dates from 2012-13. Berkeley diverted 1,721.7 tons of food waste in FY2017-18.
- **Food recovery rule.** UC policy requires campuses to report food recovered starting FY2027-28. It also puts recovery ahead of composting.

## Contradictions

1. **Plate vs kitchen share.** Leanpath assumes plate waste roughly equals kitchen waste. Missouri measured plate waste at about twice kitchen waste: 10.7% vs 5.6%. ReFED says 70% of foodservice waste is plate waste. WRAP (UK) finds 66% of waste back-of-house, from prep plus spoilage. For campus all-you-care-to-eat dining, the US measured data point to plate waste above kitchen waste. Use Missouri's split for the generator.
2. **Total waste ceiling.** Leanpath's "8-15% total" sits below Missouri's measured 16.3%.
3. **Per-meal total.** EPA and Massachusetts put food waste at 0.35-0.44 lb per meal. Illinois measured 3.3 oz, or 0.21 lb. The factors trace back to a 2001 Connecticut study. Use 0.21-0.44 lb per meal as the range, not one point.
4. **Overproduction share.** Leanpath says 50-60% of pre-consumer waste and UMass says about 50%. ReFED says 23% of total foodservice waste. These fit together if pre-consumer is roughly 30-45% of the total, which matches Missouri. They do not conflict, but quote each against its own denominator.
5. **Sector tonnage.** EPA counts 26.7M tons of food service wasted food (2019, inedible parts included). ReFED counts 13M tons of foodservice surplus (2022). The definitions differ, so never put them side by side.
6. **MCURC carbon figure.** The report's pull quote says "545,000 tons of carbon emissions" saved in one month. Its own table says 0.54 MT CO2e. The quote is an error, so do not cite it.
7. **Small internal mismatches.**
   - The ASU headline says 39% but the body says 40%.
   - The UMass case study's "15% national average" has no citation.
   - Cal Dining's early waste-tracking cut is 19% in StopWaste but "over a third" in Berkeley News, which matches 3,000 to 2,000 lb/week.
   - Berkeley's sustainable food share is 19% in UCOP FY24-25 but "about 25%" on the undated campus page. Use 19%.
8. **Potato case weight.** AH-697 (1992) lists 100 lb. Today's foodservice cartons are commonly 50 lb, but no public source for that was found. The table keeps 100 and flags it.

## Gaps

- **No Cal Dining measured waste.** There is no lb per meal, no waste by station or category, and no Leanpath export. Cal Dining has run Leanpath in 9 back-of-house sites since 2021 but publishes no figures, and campus has not audited since 2013. This is the single most useful ask for a pilot.
- **No independent kitchen-waste benchmark.** The 4-10% range traces to Leanpath alone. NACUFS benchmarking is member-only, and no public NACUFS waste report was found. Missouri is the best measured number, from a single campus in 2014.
- **No waste rate by ingredient category for institutional kitchens.** LAFA rates are national household and retail assumptions, so they are a weak proxy for which items a dining hall overproduces.
- **Case weights.**
  - Salmon, tofu, lentils, quinoa, bread, mushrooms and zucchini fall back to a 1 lb unit.
  - Chicken breast and thigh borrow the USDA Foods cut-up chicken pack.
  - Pork shoulder borrows the pork leg roast pack.
  - Produce weights come from a 1992 handbook.
- **Portion sizes.** FBG servings are child-nutrition crediting sizes, such as 1 oz of cooked meat. College portions are larger, and no public source was found. The yield factors still hold, because they are per lb.
- **FoodKeeper holes.** Fresh tomatoes and fluid milk have no numeric fridge value. Tomatoes are "pantry until ripe, then 7 days". Milk is "package use-by date". Only freezer rows were emitted for them, so the generator needs a manually sourced fridge value for both. The FoodKeeper copy is from 2018 and is a GitHub mirror.
- **Not saved locally.**
  - The Winnow release (403 to scripts).
  - The Oregon DEQ Portland State overproduction case study (link now 404). A search summary reported 10.16% of food produced was overproduced, but it is unverified and not in the tables.
  - The Kansas State signage study, reported as -15% plate waste, which is search-only.
