# Ingredient prices: sources and method

This file explains the wholesale price table the generator uses to put dollars on waste. It covers all 121 canonical ingredients and is built from public sources only.

- **Output:** `data/raw/prices/ingredient_prices.csv`, one row per `canonical_id`.
- **Audit trail:** `data/raw/prices/quotes_resolved.csv`, one row per price quote with its verified flag, $/lb and inflation factor.
- **Curated input:** `data/raw/prices/price_quotes.csv`, the hand-picked quotes.
- **Raw files:** `data/raw/prices/<source>/`, listed with URL, pull time and sha256 in `data/raw/MANIFEST_prices.csv`.
- **Sanity check:** `data/raw/prices/sanity_food_cost_per_meal.json`.

Rebuild:

```
uv run --python-preference only-managed --isolated --with httpx --with beautifulsoup4 \
  --with pandas --with pypdf python scripts/fetch_prices.py            # download missing files, rebuild
... python scripts/fetch_prices.py --offline                           # rebuild from disk only
... python scripts/fetch_prices.py --force                             # re-download everything
```

The script exits non-zero if any quote fails verification. A `--force` re-pull fetches the newest daily AMS reports, so the AMS quotes will fail until the snippets are updated to the new edition. That is deliberate.

## Unit contract for the generator

All prices are **USD per as-purchased (AP) pound**. Rice, pasta, oats, cornmeal, quinoa, noodles and dried legumes are priced dry. Recipe quantities are edible, cooked pounds, so the generator must convert with `data/raw/reference/yields.csv` before multiplying: `AP lb = edible lb / yield_factor_ep_per_ap`. Gallon and "each" ingredients are also priced per pound. Convert with `lb_per_unit` from `ingredients.csv`.

Use `usd_per_lb_mid` for headline savings and `low`/`high` for the range. All prices are in late-2026 dollars.

## Sources

| Source | Basis | What it gives | Quotes | Date |
|---|---|---|---|---|
| [USDA FNS List of Materials SY2026-27](https://www.fns.usda.gov/sites/default/files/resource-files/usdafis-ListofMaterials-sy26-27.xlsx) | wholesale, federal purchase | Estimated $/lb for 184 USDA Foods: proteins, cheese, eggs, grains, canned and frozen produce | 62 | Nov 2025 price file |
| [AMS Los Angeles Terminal Market](https://www.ams.usda.gov/mnreports/hc_fv020.pdf): fruit, vegetables, onions/potatoes, nuts | wholesale, first receiver | Daily per-carton prices. Carton weights come from USDA AH-697, already in `data/raw/reference/ah697/` | 72 | Oct 26-27, 2026 |
| [AMS boxed beef cutout and cuts](https://www.ams.usda.gov/mnreports/ams_2453.pdf), [AMS daily pork](https://www.ams.usda.gov/mnreports/ams_2498.pdf) | wholesale, packer FOB | $/cwt for subprimals: tri-tip, top sirloin, clod, 81% ground beef, butt, loin, belly | 7 | Oct 26, 2026 |
| [AMS Dairy Market News weekly](https://www.ams.usda.gov/mnreports/dywweeklyreport.pdf) | wholesale, commodity | CME Grade AA butter and 40-lb cheddar blocks | 2 | Week of Oct 19-23, 2026 |
| [Arkansas statewide groceries contract, Sysco price sheet Q3 2026](https://sas.arkansas.gov/wp-content/uploads/4600053586-Price-Changes-Q3-2026-for-Posting.pdf) | wholesale, delivered broadline distributor | About 820 case prices with pack sizes, from proteins to bakery to prepared foods. This is the closest public analog to what a campus pays a broadline distributor | 152 | Jul-Sep 2026 |
| [Montgomery County Public Schools bid 9103 Groceries & Staples](https://ww2.montgomeryschoolsmd.org/departments/procurement/uploads/9103.12/Bid%20Tab.pdf) | bid | Multi-vendor bids for condiments, spices, oils, soup base, parmesan, rice | 16 | Aug 2022-Jul 2023 |
| [MCPS bid 9120 Dairy & Juice](https://ww2.montgomeryschoolsmd.org/departments/procurement/uploads/9120.6/9120.6%20Bidtab.pdf) | bid | Fluid milk by the gallon, half-and-half, sour cream, bulk yogurt, juice | 7 | Jul 2021-Jun 2023 |
| [NYC DCAS Bid Tabulations open data](https://data.cityofnewyork.us/resource/9k82-ys7w.json) | bid | Olive oil, coconut milk, quinoa, lentils, salmon, cider vinegar, parmesan | 9 | 2018-2019 |
| [BLS API](https://api.bls.gov/publicAPI/v2/timeseries/data/): average retail prices | retail | US city-average retail prices, used only as a ceiling and for the wholesale/retail ratio | 21 | Sep 2026 |
| BLS PPI and CPI (same JSON) | index | WPU02 processed foods, WPU023 dairy, WPU0211 meats/poultry/fish, CUUR0000SAF11 food at home | n/a | through Sep 2026 |
| [UF Food Service Master Plan, Dec 2019](https://businessservices.ufl.edu/wp-content/uploads/2020/01/Food-Svcs-Master-Plan-Report_Final_December-2019.pdf) | benchmark | All-you-care-to-eat plate cost per visit | n/a | Fall 2018 |

**Searched and not used.** Each of these was checked and rejected for the reason given.

- **San Francisco terminal reports.** AMS discontinued them in April-May 2025. Los Angeles is the nearest live California terminal market.
- **Escambia County (FL) 2025 bid tabs.** They price per serving without pack weights, so they cannot be converted to $/lb.
- **California district awards (Visalia, Long Beach, Riverside, Sacramento City).** Only award totals are public, not unit prices.
- **Cal Dining and UC procurement.** No public price or cost-of-goods documents were found. Cal Dining publishes only selling prices, such as $14-18 guest meals.
- **MyMarketNews API.** It needs a registered key. The public mnreports PDFs carry the same reports.

## Method

1. **Verify every quote.** Each row in `price_quotes.csv` names a raw file, a text snippet and a price. The script extracts the PDF or JSON text, collapses whitespace, and requires the snippet and price to appear literally within 4 kB of each other. USDA prices are read from the xlsx by material number. BLS values are read from the saved JSON. All 348 quotes verify.
2. **Convert to $/lb.** Divide the case price by the pack weight. Pack weights come from the source's own pack size when it gives one. Otherwise they come from AH-697 container weights, or from USDA List of Materials case weights for #10 cans: 6.6 lb on average, 6.75 lb for beans, 6.38 lb for diced tomatoes. Any other assumption is written in the quote's `note`, for example 7.5 lb/gal for mayonnaise, taken from the MCPS spec equating a 30 lb pail with 4 gallons.
3. **Inflate dated quotes to September 2026.** The factor is the BLS PPI for the quote's month divided by September 2026. WPU02 covers groceries, WPU023 covers dairy and WPU0211 covers meat and fish.

   | Quote vintage | Factor |
   |---|---|
   | WPU02, Aug 2022 (MCPS groceries) | 1.05 |
   | WPU02, 2018-19 (NYC) | 1.33 |
   | WPU023, Jul 2021 (MCPS dairy) | 1.12 |
   | WPU02, Nov 2025 (USDA Foods) | 1.01 |

4. **Set low, high and mid.** Low and high are the cheapest and dearest non-retail quotes. Mid is the median of the quotes that represent **delivered** prices: distributor contract, school bids and city bids. A campus buys delivered, and commodity, packer and terminal prices sit below that.
5. **Lift upstream-only mids.** Some ingredients have only first-receiver or commodity quotes, such as terminal produce or USDA-only items. Their mid is lifted by a delivered/source ratio measured inside this dataset, on ingredients quoted both ways.

   | Upstream source | Delivered/source ratio | Items measured |
   |---|---|---|
   | AMS terminal | 1.49 | 13 |
   | USDA Foods | 1.60 | 32 |
   | AMS packer FOB | 1.78 | 3 |
   | CME dairy | 1.63 | 2 |

6. **Retail.** Retail never sets a price where any wholesale or bid quote exists. It appears only as a `retail ceiling` in the note. On 21 overlapping items, the median ratio of wholesale mid to retail is 0.73, with a 25th percentile of 0.58. No ingredient ended up retail-only.
7. **Basis label.** `price_basis` is `wholesale` if any non-retail quote is distributor, terminal, packer or USDA. It is `bid` if all are bids. It is `proxy` if every quote is a stand-in product.
8. **Confidence.**
   - **High:** exact-match quotes from two or more independent source families, with high/low at most 4x.
   - **Med:** exact quotes from one family, or proxy quotes from two families.
   - **Low:** everything else.
9. **misc_dry.** This is the recipe builder's unmatched-component bucket. It is priced as the median of the 46 dry-storage ingredients and labelled proxy/low.

## Coverage

All 121 ingredients have a price. None is blank and none is retail-only.

| Confidence | Ingredients | Share of menu demand (lb) |
|---|---|---|
| high | 48 | 49.4% |
| med | 61 | 37.8% |
| low | 12 | 12.8% |

| Basis | Ingredients |
|---|---|
| wholesale | 95 |
| proxy | 18 |
| bid | 8 |

These are the proxies, and the generator should treat them as weaker.

- **soup_prepared:** canned chili, beef stew and condensed soup at as-served weight.
- **prepared_entree:** chicken and dumplings, cheese ravioli, stuffed peppers and au gratin casserole.
- **pizza_base:** pre-baked pizza sticks and topped slices, with bakers flour as the floor.
- **hummus_dips:** prepared deli salads, with canned garbanzo as the floor.
- **cheese_crumbled:** cheddar and Swiss, because no feta price was found.
- **cheese_vegan:** dairy mozzarella. This likely understates the real price.
- **egg_alt:** Egg Beaters, not a plant egg.
- **pasta_gf:** wheat pasta. This likely understates the real price.
- **shrimp:** breaded shrimp only.
- **oil_sesame:** olive oil.
- **wine_cooking:** cider vinegar.
- **soft_serve_mix:** finished ice cream at an assumed 4.5 lb/gal, plus whole milk as the floor.
- **bagel and bread_sliced:** French loaf.
- **pancake_mix:** cake mix and frozen pancakes.
- **croutons_crumbs:** corn-flake and graham crumbs.
- **sauce_prepared:** cheese sauce, gravy and spaghetti sauce. Pesto and curry paste cost more.
- **misc_dry:** the computed median described above.

## Hall-level sanity check: implied food cost per meal

**Benchmark.** The University of Florida master plan, written by Brailsford & Dunlavey in 2019, reports an all-you-care-to-eat plate cost of **$2.81 per visit** in Fall 2018. It defines plate cost as "cost of goods sold" and calls it low. It also says "Top residential dining programs can have AYCTE plate costs between 30% and 50% higher." The script verifies both quotes in the raw PDF.

BLS CPI food-at-home rose by a factor of 1.342 from the Fall 2018 average to September 2026, which gives these 2026 benchmarks:

| Benchmark, 2026 dollars | Plate cost per meal |
|---|---|
| UF level | $3.77 |
| Top programs | $4.90-5.65 |

The lead's working range of $2.50-4.50 per meal matches this. No other campus published a plate cost that this search could find. Meal-plan prices such as Cal Dining's $14-18 guest meals include labor and overhead, so they are not comparable.

**Our implied cost.** The calculation has four steps.

1. Ingredient mix is `data/recipes/ingredient_demand_weights.csv`, which is edible pounds across the scraped Cal Dining menu window.
2. Each ingredient's edible pounds are converted to AP pounds with `yields.csv` and priced at low, mid and high.
3. This gives a weighted cost per edible pound of food served: $1.22 low, $2.32 mid, $2.68 high.
4. Edible pounds per diner per meal run from 0.97 to 1.2. The low end comes from Missouri's audit (Costello 2015): 24.6 g pre-consumer waste per customer is 5.6% of food reaching retail, which implies 439 g per customer. The high end is the 1.2 lb meal-equivalent convention (Food Recovery Network). Both are already in `waste_benchmarks.csv`.

| Case | Food cost per meal | With 5.6% pre-consumer loss |
|---|---|---|
| low (all lows, 0.97 lb) | $1.18 | $1.25 |
| **mid (mids, 1.08 lb)** | **$2.52** | **$2.66** |
| high (all highs, 1.2 lb) | $3.21 | $3.39 |

**Verdict.** The mid case, **$2.52-2.66 per meal**, sits at the low end of the $2.50-4.50 range and below UF's inflated $3.77. That is the right direction for an ingredient-only build, because it leaves out three things.

- **Off-recipe items.** Beverages, the salad bar, condiment stations and fruit bowls are not in the recipe mix, but they are in a plate cost.
- **Overproduction.** Leftover overprep is bought but not counted in edible pounds served.
- **Brand premiums.** Cal Dining's specialty and plant-based products cost more than the proxies used here.

If the deck needs dollar totals that tie to a published plate cost, a calibration factor of about 1.4x (3.77 / 2.66) is the gap. **No calibration has been applied.** The table reports what the sources support.

## Top gaps

1. **soup_prepared:** low confidence, 8.8% of menu demand by weight, the largest single cost line. There is no public bulk frozen-soup price, so canned chili, stew and condensed soup stand in. Cal Dining's soup supplier invoice, or any district bid for frozen kettle soups, would close this.
2. **Plant-based specialty items:** egg_alt, cheese_vegan, pasta_gf, plus single-source meat_alt, milk_plant and tofu. None has a public bulk price with a pack weight. The proxies likely understate these by 1.5-2.5x. That figure comes from industry experience and is not sourced. These matter for Cal Dining's vegan stations.
3. **Fluid dairy is dated:** milk, cream and sour cream have only one source, the 2021-23 Maryland school bid, inflated by PPI. Cal Dining's dairy contract, or a current California district milk award with unit prices, would replace them. Most California districts publish only award totals.

Smaller caveats:

- **Weight assumptions.** Terminal-market carton weights are AH-697 approximations from 1992. Two are assumptions: the 20 lb 1-layer pineapple carton and the 25 lb collard carton.
- **Nuts in shell.** The nut quotes are in-shell, so shelled kernels cost more.
- **Units in two older bids.** The NYC salmon price is read as $/lb, and the MCPS 4 oz juice is priced per carton.
