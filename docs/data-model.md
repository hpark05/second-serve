# Second Serve data model

This is the contract between the synthetic generator (`generator/`) and the app. It expands the entity table in `docs/PLAN.md`. Every field lists its unit, cadence, and the input that grounds it. Fields marked **ASSUMPTION** come from a modeling prior in `generator/config/base.yaml`, not from a source in `data/raw/`.

```
uv run --python-preference only-managed --isolated --python 3.12 --with pandas --with numpy --with pyyaml \
  python -m generator --scenario normal_week --out data/synthetic/normal_week
uv run --python-preference only-managed --isolated --python 3.12 --with pandas --with numpy --with pyyaml --with pytest pytest
```

Scenarios live in `generator/config/<name>.yaml` and deep-merge over `base.yaml`. Input paths live in `generator/config/paths.yaml`. To swap a placeholder for a real file, put the real file at its `path`. The loader uses the fallback only when that path is missing, and logs a WARNING when it does.

## Two kinds of pound

| Column suffix | Meaning | Used for |
|---|---|---|
| `lb` | Physical weight as weighed. Raw lots are as-purchased. Food is as served, so cooked rice is about 2.6 times its dry weight. | Waste metrics and benchmark checks. Weighed audits report this. |
| `lb_ap` | As-purchased-equivalent weight. | Inventory mass balance. Cooking gain or loss does not break the ledger. |

The yield factor is the USDA Food Buying Guide's served weight over as-purchased weight. It is split into two parts:

- **`trim_frac`** is the inedible share. It becomes pre-consumer waste.
- **`cook_factor`** is the change in mass from cooking, draining, or hydration. It is not waste.

The rule lives in `generator/loaders.py` `classify_yield`. A cooked, drained, or greater-than-1 yield counts as `cook_factor`. A ready-to-cook or ready-to-serve yield counts as trim.

## Entities

Cadence key: **static** means fixed for the run, **per meal** means one row per hall, date, and meal period, and **daily** means one row per hall and date.

### Hall — `halls.csv`, `bundle.halls[]` (static)

| Field | Type / unit | Grounded by |
|---|---|---|
| id | slug (`crossroads`, `cafe-3`, `foothill`, `clark-kerr`) | `base.yaml` halls |
| name | string, matches `menu_items.csv` hall | menus |
| covers_per_day | covers/day | `hall_volume.csv` students_served_per_day. Crossroads 4,400, Café 3 2,500, Clark Kerr 1,200. Foothill has no published figure. It is derived as 10,000, the four-commons meals_served_per_day lower bound, minus the other three, giving 1,900. `covers_source` records the formula. |
| seats | seats, nullable | `hall_volume.csv` seats. Only Crossroads is published, at 850 in 2008. |
| residents | null | No per-hall resident count exists in `data/raw`. |
| hours | `{breakfast, lunch_brunch, dinner}` strings | `halls.csv` hours_* |
| feeder_housing | string | `halls.csv` |
| stations[] | station ids | Stations observed in the menus |

### Station — `stations.csv`, `bundle.stations[]` (static)

| Field | Type | Grounded by |
|---|---|---|
| id | `<hall_id>:<normalized station name>` | menus |
| hall_id | hall id | menus |
| name | raw station name | `menu_items.csv` station |
| role | entree, bar_component, soup, dessert, bakery, breakfast_side, condiment, specialty, or entree_repurposed | **ASSUMPTION**. Assigned by substring rules in `base.yaml` station_roles. |

### MenuItem — `menu_items.csv`, `bundle.menu_items[]` (per meal)

| Field | Type / unit | Grounded by |
|---|---|---|
| menu_item_id | `<hall>:<date>:<meal>:<idx>` | generator |
| hall_id, date, meal_period | id, ISO date, breakfast, brunch, lunch, or dinner | sim calendar |
| station_id, name | | `menu_items.csv` station and item_name, verbatim |
| recipe_id | recipe id | `data/recipes/menu_item_map.csv`. It joins on hall, date, meal, station, and item, then on normalized name, then on Eatec id. |
| source_date, source_meal_period, source_station, source_url | the scraped row this item replays | `menu_items.csv`. Replayed weeks map each sim date to the scraped date with the same weekday in `menu_source.week_start`. |
| serving_lb | lb per portion | `menu_items.csv` serving_size. Values above 1 lb are pan weights such as a 241 oz chicken salad, so the recipe portion is used instead. |
| take_rate | portions per diner | **ASSUMPTION**. Station visit rate times picks, split across the station's items by a lognormal popularity weight. Entree visit is 0.35 to 0.55 and side is 0.20 to 0.40, both from PLAN.md. |
| station_role | | from Station |

The bundle omits `source_url` from each item and serves it once per hall and date in `bundle.menu_sources["<hall_id>|<source_date>"]`.

### Recipe — `recipes.csv`, `recipe_ingredients.csv`, `bundle.recipes[]` (static)

| Field | Type / unit | Grounded by |
|---|---|---|
| id | recipe id | `data/recipes/recipes.csv` from recipe-mapper |
| name | string | recipe-mapper |
| portions_per_batch | portions | recipe-mapper |
| portion_lb | lb as served | Sum of the ingredient qty_lb divided by portions_per_batch |
| ingredients[] | `{ingredient_id, qty, unit, qty_lb}` per batch, as-served basis | `data/recipes/recipe_ingredients.csv`, built from Eatec ingredient text |

If the recipe files are missing, `generator/menu_text_recipes.py` derives PLACEHOLDER recipes from the Eatec ingredient text. Those rows carry `source=derived_from_menu_text`.

### Ingredient — `ingredients.csv`, `bundle.ingredients[]` (static)

| Field | Type / unit | Grounded by |
|---|---|---|
| ingredient_id, name, category, role | | `data/recipes/ingredients.csv` |
| storage | refrigerated, frozen, or dry | recipe-mapper (cooler, freezer, dry) |
| unit, lb_per_unit | purchase unit and lb per unit | recipe-mapper |
| usd_per_lb, usd_per_lb_low, usd_per_lb_high | USD per as-purchased lb, Sep 2026 | `data/raw/prices/ingredient_prices.csv` (mid, low, high) joined on canonical_id. All 119 used ingredients are priced. Grains, pasta, and legumes are priced dry, and our as-purchased lb for them are dry via yields. |
| price_basis, price_confidence, price_source | | the same file |
| case_lb | lb per case, nullable | `data/raw/reference/ingredients.csv` lb_per_unit, from USDA Foods and AH-697. Orders round up to whole cases for items that keep more than 7 days. |
| shelf_life_days | days | `data/raw/reference/shelf_life.csv` (FoodKeeper) `shelf_life_days`, the midpoint of low and high. It joins on `canonical_id`. It prefers the `primary_storage` row matching the ingredient's storage: refrigerator then refrigerator_after_opening, pantry, or freezer. Then any primary row, then any row. Next comes the name join through the recipe-mapper's `shelf_life_ref`. Otherwise it uses a PLACEHOLDER category row. |
| shelf_life_source | `reference:<file>:<row>` or `fallback:<file>:<row>` | Records the row used. Tests check that the row exists. |
| trim_frac_raw | fraction of as-purchased weight | `yields.csv` (FBG) for ready-to-cook items, joined through `reference_ingredient`. Otherwise `loss_rates.csv` (ERS LAFA) consumer_nonedible_pct for fresh produce, joined on `canonical_id` and then the name. LAFA is a **household proxy**, labelled as such in summary.json. Otherwise a PLACEHOLDER category row. Frozen and dry goods get zero. |
| retail_loss_pct, loss_rate_source, loss_rate_confidence | % | ERS LAFA `retail_loss_pct` joined on `canonical_id`. It is a household/retail proxy and **informational only, not a sim input**. The 17 ingredients with no ERS series get the median of covered ingredients in the same recipe category, labelled `default:category_median:<category>`. The defaults are protein 5.2, prepared 6.0, beverage 6.0, and condiment 21.0. |
| vendor_prep_share, vendor_prep_lines | fraction and count | Share of the ingredient's Eatec component lines whose names say the vendor prepped them, such as "Onion Yellow Diced 3/8 in" or "Garlic Peeled". Lines map to ingredients with recipe-mapper's `ingredient_rules.csv`. |
| trim_frac | fraction | trim_frac_raw times (1 minus vendor_prep_share) |
| cook_factor | served over edible-raw | `yields.csv` cooked, drained, or hydrated yields, for example rice at 2.612 and chicken thigh at 0.63. Recipe quantities are cooked edible weight, so the FBG yield is applied exactly once: as-purchased = qty ÷ yield_factor. |
| yield_factor | served over as-purchased | (1 minus trim_frac) times cook_factor |
| yield_source | as for shelf_life_source | |
| reference_ingredient, fallback_category | link keys | recipe-mapper link columns first, then `generator/config/ingredient_crosswalk.csv` |

### InventoryLot — `inventory_lots.csv`, `bundle.inventory` (daily snapshot)

| Field | Type / unit | Grounded by |
|---|---|---|
| snapshot_date, snapshot | ISO date; opening, daily, or closing | The opening snapshot is the day before the start. |
| lot_id, hall_id, ingredient_id | | sim |
| qty, unit, qty_lb | purchase unit and lb as-purchased | FIFO sim |
| received_date, expiry_date | ISO dates. expiry = received + shelf_life_days. A lot is usable while date < expiry. | Ingredient |
| origin | opening, delivery, or transfer_in | sim |
| days_to_expiry | days | sim |

The bundle carries every snapshot's lot rows in `inventory`. It also carries `inventory_daily`, which is lb, lot count, and minimum days to expiry per snapshot, hall, and ingredient.

### Delivery — `deliveries.csv`, `bundle.deliveries[]` (event)

This is the PLAN's "received" term, made explicit.

| Field | Type / unit | Grounded by |
|---|---|---|
| lot_id, hall_id, ingredient_id, date | | sim |
| qty_lb | lb as-purchased | Forecast need over the cover window times (1 + safety stock), minus usable stock on hand, rounded to the case. Safety stock of 10% is an **ASSUMPTION**. |
| kind | delivery or emergency | emergency means a same-day top-up when FIFO stock runs short |
| expiry_date | ISO date | |

Delivery days are an **ASSUMPTION**:

- Refrigerated items arrive Monday, Wednesday, and Friday.
- Frozen and dry items arrive Monday.
- Items keeping 3 days or less arrive Monday through Saturday.

The cover window never exceeds shelf life.

### Diners — `diners.csv`, `bundle.diners[]` (per meal)

| Field | Type / unit | Grounded by |
|---|---|---|
| hall_id, date, meal_period | | |
| diners_actual | covers | Poisson(covers_per_day × meal share × weekend factor × scenario multiplier). Meal shares and the 0.85 weekend factor are **ASSUMPTION**s. |
| diners_forecast | covers | Mean of the last `history_weeks` (2) same-weekday actuals, drawn at baseline from their own RNG stream |
| multiplier | | scenario YAML |
| plate_waste_frac | fraction of food served | Sampled per meal from the `plate_waste_pct_of_food_selected` range, 11.8 to 15.8% (Illinois). The per-cover check uses different rows, so the check is not circular. |

### ProductionRecord — `production.csv`, `bundle.production[]` (per meal)

| Field | Unit | Definition |
|---|---|---|
| hall_id, date, meal_period, menu_item_id | | |
| portions_forecast | portions | diners_forecast × take_rate |
| overprep_factor | | U(1.05, 1.20), from PLAN.md |
| portions_prepared | portions | ceil(forecast × overprep) |
| portions_demanded | portions | Binomial(diners_actual, take_rate) |
| portions_served | portions | min(prepared, demanded) |
| portions_short | portions | demand beyond what was prepared |
| portions_repurposed | portions | leftover × U(0.35, 0.55), an **ASSUMPTION**. Every hall runs "While It Last" stations. |
| portions_donated | portions | remaining leftover × U(0.45, 0.65). This is **CALIBRATED** so simulated donations match Cal Dining's reported figure: 50,000 lb per semester over 16 weeks, about 3,125 lb a week (`uc_numbers.csv`). The sim gives 3,098 lb a week. |
| portions_wasted | portions | the rest, which becomes WasteEvent overproduction |
| serving_lb | lb | |
| served_lb, repurposed_lb, donated_lb | lb, physical | portions × serving_lb |
| served_lb_ap | lb_ap | (served + repurposed) × as-purchased food per portion |
| recovered_lb_ap | lb_ap | donated × as-purchased food per portion |
| prepared_lb_ap_food | lb_ap | prepared × as-purchased food per portion |

The bundle production rows also carry `wasted_lb` and `plate_waste_lb` for that item.

### WasteEvent — `waste_events.csv`, `bundle.waste` (per meal or day)

| Field | Unit | Definition |
|---|---|---|
| waste_event_id, hall_id, date, meal_period | | |
| kind | | pre_consumer, post_consumer, or expired |
| reason | | `trim` (per ingredient), `overproduction` (per menu item), `plate_waste` (per menu item), or `expired_in_storage` (per lot) |
| ingredient_id / menu_item_id / lot_id | | whichever applies |
| lb | lb, physical | |
| lb_ap | lb_ap | used by the mass balance |

Post-consumer plate waste is a subset of served food. It is reported but is not a separate term in the inventory balance. The bundle's aggregated `waste` list is described under bundle.json below.

### Transfer — `transfers.csv`, `bundle.transfers[]` (event)

| Field | Unit | Definition |
|---|---|---|
| transfer_id, date, from_hall, to_hall, ingredient_id, lot_id, expiry_date | | |
| qty_lb | lb | min(A's expiring stock minus A's own planned use before expiry, B's planned use in the window). The window is 2 days. |
| status | | `proposed` (default, today's operations) or `completed` (`transfers.execute: true` or `--execute-transfers`, which moves the mass) |
| est_lb_saved | lb | equal to qty_lb |

### MassBalance — `mass_balance.csv` (per hall-week)

All terms are lb_ap:

```
received + opening + transferred_in = served + recovered + closing + waste(pre_consumer + expired) + transferred_out
```

`recovered` covers donated leftovers. It extends the PLAN.md formula because donated food leaves the hall uneaten but not as waste. Tolerance is 1%. The test recomputes the balance from the CSVs.

### Recommendation — `recommendations.csv`, `bundle.recommendations[]` (daily)

`generator/recommendations.py` builds deterministic rule-based candidates. The app's Claude agent can rank them, explain them, or replace them.

| Field | Unit | Definition |
|---|---|---|
| id | `R00001` | |
| hall_id, date | | |
| kind | | See the rules below. |
| target | | ingredient_id, menu_item_id, `<ingredient>-><to_hall>`, or `food_recovery` |
| qty, unit | lb or portions | |
| est_lb_saved | lb | |
| est_usd_saved | USD, Sep 2026 | Ingredient kinds use est_lb_saved × that ingredient's mid `usd_per_lb`. adjust_prep uses saved portions × the item's as-purchased cost per portion. It is null for recover, because the food is already bought. |
| rationale | string | One sentence citing the numbers |
| inputs | object | The values the rule used, such as lot ids, forecast, prepared, and wasted |

The rules:

- **use_first:** a lot expires within 2 days and the hall's own plan won't use it first. Each lot is flagged only once, on the first day.
- **adjust_prep:** prepare at the low end of the overprep band (1.05 × forecast) where overproduction was binned. Keeps the top 5 per hall-day.
- **buy_less:** an ingredient expired unused at a hall during the scenario.
- **transfer:** one per Transfer candidate.
- **recover:** overproduction binned at a hall-day that could go to food recovery.

Candidates below 2 lb are dropped.

### Factors — `bundle.meta.factors`, `summary.factors`

| Factor | Value | Grounded by |
|---|---|---|
| lb_per_meal | 1.2 | `waste_benchmarks.csv` food_recovery_lb_per_meal (Food Recovery Network FY19) |
| co2e_lb_per_lb | about 1.61 | Eatec `carbon_kg_co2` per serving ÷ serving weight across `menu_items.csv` |
| blended_usd_per_lb_reference (in `factor_sources` only) | about 1.82 | **Reference only, superseded.** StopWaste's Cal Dining case gives $98,402 a year in avoided food cost over a 27-ton reduction. No calculation uses it. |

## Input resolution and fallbacks

| Input | Real file | Placeholder when missing |
|---|---|---|
| Menus, halls, volume, benchmarks | `data/raw/...` | none (required) |
| Recipes, ingredients, map | `data/recipes/*.csv` | derived from Eatec text (`menu_text_recipes.py`) |
| Shelf life | `data/raw/reference/shelf_life.csv` | `generator/fallback/shelf_life.csv` by category |
| Yields | `data/raw/reference/yields.csv` + `loss_rates.csv` | `generator/fallback/yields.csv` by category |
| Case sizes | `data/raw/reference/ingredients.csv` | none (no case rounding) |
| Vendor-prep share | `data/recipes/ingredient_rules.csv` | none (no adjustment) |

Partial coverage also falls back per ingredient. Each ingredient's `*_source` column shows which applied. The count is logged as a WARNING and appears in `summary.warnings`.

## bundle.json

The bundle is static and has no timestamps, so the same seed produces identical bytes. Floats are rounded to 3 decimals, and 2 for production rows.

```jsonc
{
  "schema_version": "1.0",
  "meta": {"product": "Second Serve", "scenario", "description", "start_date", "end_date", "as_of", "seed",
           "generated_at": null,            // always null: a timestamp would break same-seed byte identity
           "menu_source_week_start", "transfers_executed",
           "factors": {"lb_per_meal", "co2e_lb_per_lb"}, "factor_sources": {...}},
  "provenance": {"inputs": [{"input", "path", "status": "real|fallback|missing", "rows"?}], "warnings": [str], "reference_notes": {file: note}},
  "halls": [{"id", "name", "seats", "residents", "covers_per_day", "covers_source": {...}, "hours": {...}, "stations": [id]}],
  "stations": [{"id", "hall_id", "name", "role"}],
  "ingredients": [{"id", "name", "category", "storage", "unit", "lb_per_unit", "case_lb", "usd_per_lb", "shelf_life_days", "shelf_life_source",
                   "trim_frac", "trim_frac_raw", "vendor_prep_share", "vendor_prep_lines", "cook_factor", "yield_factor", "yield_source",
                   "retail_loss_pct", "loss_rate_source", "loss_rate_confidence", "reference_ingredient", "fallback_category", "role"}],
  "recipes": [{"id", "name", "portions_per_batch", "portion_lb", "ingredients": [{"ingredient_id", "qty", "unit", "qty_lb"}]}],
  "menu_sources": {"<hall_id>|<source_date>": "<eatec xml url>"},
  "menu_items": [{"id", "hall_id", "date", "meal_period", "station_id", "name", "recipe_id", "source_date", "serving_lb", "take_rate", "station_role"}],
  "inventory": [{"snapshot_date", "snapshot", "lot_id", "hall_id", "ingredient_id", "qty", "unit", "qty_lb", "received_date", "expiry_date", "origin", "days_to_expiry"}],
  "inventory_daily": [{"snapshot_date", "hall_id", "ingredient_id", "qty_lb", "lots", "min_days_to_expiry"}],
  "production": [{"hall_id", "date", "meal_period", "menu_item_id", "portions_forecast", "portions_prepared", "portions_served",
                  "portions_short", "portions_repurposed", "portions_donated", "portions_wasted",
                  "served_lb", "wasted_lb", "plate_waste_lb", "donated_lb"}],
  "diners": [{"hall_id", "date", "meal_period", "diners_forecast", "diners_actual", "multiplier", "plate_waste_frac"}],
  "waste": [{"waste_event_id", "hall_id", "date", "meal_period", "kind", "reason", "ingredient_id", "menu_item_id", "lot_id", "lb", "lb_ap"}],
  "transfers": [{"transfer_id", "date", "from_hall", "to_hall", "ingredient_id", "qty_lb", "lot_id", "expiry_date", "status", "est_lb_saved"}],
  "recommendations": [{"id", "hall_id", "date", "kind", "target", "qty", "unit", "est_lb_saved", "est_usd_saved", "rationale", "inputs"}],
  "deliveries": [{"lot_id", "hall_id", "ingredient_id", "date", "qty_lb", "kind", "expiry_date"}],
  "daily_totals": [{"hall_id", "date", "covers", "purchased_lb", "served_lb", "pre_consumer_lb", "expired_lb", "post_consumer_lb", "donated_lb", "portions_short"}],
  "summary": {"headline", "checks", "all_checks_pass", "mass_balance", "transfers", "donation_reference"}
}
```

The bundle `waste` list is aggregated to keep size down, in four parts:

- Trim per hall, day, meal, and ingredient, with ids starting `WT`.
- Plate waste per hall, day, and meal, with ids starting `WP`.
- Overproduction per menu item.
- Expiry per lot.

`waste_events.csv` keeps full detail. A bundle is about 5.3 MB uncompressed, and most of that is daily inventory lot rows. Setting `bundle.inventory_snapshots: ends` keeps only the opening and closing snapshots. **Do not use it for app bundles.** The app's Dashboard, Inventory and Campus Network pages read the `meta.as_of` snapshot. Gzipped, 5.3 MB is fine for static hosting.

## summary.json

The summary has these blocks:

- **headline** holds covers, purchased, served, and the waste totals in lb, plus the six benchmark metrics.
- **checks[]** holds `{check, label, unit, value, range_low, range_high, pass, sources[]}`.
- **mass_balance** holds max_abs_imbalance_pct, tolerance_pct, and pass.
- **transfers** and **donation_reference** cover transfers and the sim versus Cal Dining donation comparison.
- **overall** and **by_hall** carry the full aggregates.
- **inputs** and **warnings** carry provenance.

The `costs` block holds dollar figures at mid prices, with low and high ranges:

- **purchased_usd** and **prepared_food_usd**.
- **food_cost_per_meal**, computed as purchased dollars over covers. It is compared to the $2.52 implied cost from `docs/sources-prices.md` and to UF's $3.77, both read from `data/raw/prices/sanity_food_cost_per_meal.json`.
- **waste_usd**, split into trim, overproduction, expired, and plate.
- **recommendations_est_usd_saved**, holding `by_kind_mid`, `sum_of_candidates`, and `deduplicated`. The headline figure is the deduplicated mid. It equals adjust_prep plus the smaller of two amounts: the combined use_first, transfer, and buy_less total, or the dollar value that actually expired.

Each check's range is the union of the named `waste_benchmarks.csv` rows after unit conversion. A point estimate is widened by ±50% only when every row in the check is a point estimate.

| Check | Benchmark rows |
|---|---|
| pre_consumer_pct_of_purchased | Leanpath 4–10% and Costello 5.6% |
| plate_waste_lb_per_cover | BAMCO/NRDC 2.18 oz and American University 76–111 g |
| total_waste_pct_of_purchased | Leanpath 8–15% |
| total_waste_lb_per_meal | EPA 0.36–0.44, RecyclingWorks 0.35, and Illinois 3.3 oz |
| overproduction_share_of_pre_consumer | Leanpath 50–60% and UMass 50% |
| pre_consumer_lb_per_cover | Costello 24.6 g ±50% |

## Calibration (normal_week)

| Metric | Sim | Target | Source |
|---|---|---|---|
| Pre-consumer, % of purchased | 7.6% | 4–10%, centered on 5.6% | Leanpath; Missouri (Costello) |
| Plate waste ÷ kitchen waste | 1.8× | about 2× (10.7% vs 5.6%) | Missouri |
| Plate waste, lb per cover | 0.158 | 0.136–0.245 | BAMCO/NRDC; American University |
| Total waste, lb per meal | 0.25 | 0.21–0.44 | EPA; Illinois |
| Overproduction share of pre-consumer | 42% | 50–60% | Leanpath; UMass |
| Donations, lb per week | 3,098 | about 3,125 | Cal Dining (`uc_numbers.csv`) |
| Food cost per meal (mid) | $2.71 | $2.52 implied (sources-prices); $3.77 UF | `sanity_food_cost_per_meal.json` |

**The targets conflict.** Trim is now fully sourced from FBG yields, LAFA, and vendor-prep shares, and comes to 3.9% of purchases. Expiry adds 0.5%. So a 5.6% pre-consumer total leaves only about 1.2 points for overproduction. Reaching a 50–60% overproduction share would push pre-consumer to about 9% and the plate-to-kitchen ratio down to about 1.5×. The generator keeps the sourced trim and donation figures, so overproduction lands at 42%.

The one remaining lever is `leftover.repurpose_frac_range`, an unsourced prior. Lowering it raises the overproduction share.

### Priors that were tuned

The following priors were set so normal_week lands in published ranges. The outputs they affect are calibrated, not independent evidence.

- **Entree and specialty picks of 2.0.** Served mass comes to 1.14 lb per cover. The Illinois plate-waste share and the per-cover benchmarks together imply 1.0 to 1.8 lb.
- **The donation share**, calibrated to Cal Dining's reported donations.
- **Zero fallback trim for frozen and dry goods.**
- **Case rounding only for items keeping more than 7 days.**

The plate-waste prior (Illinois) and the per-cover check (BAMCO and American University) use different sources.

## Tests

| Test | What it checks |
|---|---|
| `test_mass_balance.py` | Per hall-week, recomputed from CSVs, within 1%. Runs all scenarios plus executed transfers. |
| `test_benchmarks.py` | Pre-consumer % and plate waste per cover for normal_week, against ranges read from `waste_benchmarks.csv` |
| `test_menu_fidelity.py` | Every synthetic item exists in `menu_items.csv` for its hall and its source date and meal |
| `test_determinism.py` | Same seed gives byte-identical files; a different seed gives different files |
| `test_ingredient_coverage.py` | Every used ingredient cites shelf-life and yield rows that exist. Shelf-life reference coverage by purchased lb is printed, and the test fails below 95%. |
| `test_fallback_mode.py` | Runs with every swappable input missing |

## Known gaps

- **Fallback counts** for normal_week. `summary.json` `fallback_counts` lists the ids.

  | Attribute | Placeholder or default | Share of purchased lb |
  |---|---|---|
  | Shelf life | 1 of 119 (`misc_dry`) | 0.0% |
  | Yield | 55 of 119 | 40.5% |
  | Loss rate | 17 of 119 | 16.5% |

  Placeholder yields are mostly sauces, prepared and frozen goods, condiments, and dairy. Their fallback trim is zero for frozen and dry goods, so the large share of purchased weight mostly means "no FBG row", not invented trim.
- **Prices are ingredient cost only.** Dollar figures leave out labor, packaging, and overhead. Twelve prices are low confidence.
- **Hypothetical dates.** Game-day, finals, and Thanksgiving dates and magnitudes are illustrative.
- **total_waste_pct_of_purchased fails**, at 21% against 8 to 15%. Leanpath assumes plate waste roughly equals kitchen waste, and Missouri measured about 2×.
- **pre_consumer_lb_per_cover fails**, at 0.089 lb against Costello's single facility figure of 24.6 g ±50%.
