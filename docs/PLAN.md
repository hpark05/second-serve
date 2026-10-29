# Second Serve build plan

Pitch prototype for Cal Dining. No internal data exists; every number must trace to a public source in `data/raw/`.

## Order
1. Research (demand + supply) → `data/raw/`, `docs/sources-*.md`
2. Data model → `docs/data-model.md`
3. Synthetic generator + tests → `generator/`, `data/synthetic/`
4. **Pause for Hamilton review**
5. App rebuild (Vite + React + TS + Tailwind + shadcn, static JSON, Claude recs)
6. One-page "How we built the numbers" for the deck

## Data model (contract for step 3)

| Entity | Key fields | Cadence | Grounded by |
|---|---|---|---|
| Hall | id, name, seats, stations[], hours, residents | static | halls.csv, hall_volume.csv |
| Station | id, hall_id, name, cuisine | static | menus |
| MenuItem | id, hall_id, date, meal_period, station_id, name, recipe_id | per meal | menu_items.csv |
| Recipe | id, name, portions_per_batch, ingredients[{ingredient_id, qty, unit}] | static | yields.csv, ingredients.csv |
| Ingredient | id, name, category, unit, lb_per_unit, shelf_life_days, storage | static | ingredients.csv, shelf_life.csv |
| InventoryLot | id, hall_id, ingredient_id, qty, unit, received_date, expiry_date | daily snapshot | FIFO sim |
| ProductionRecord | hall_id, date, meal_period, menu_item_id, portions_forecast, portions_prepared, portions_served | per meal | diner counts × take rate |
| WasteEvent | hall_id, date, kind (pre_consumer\|post_consumer\|expired), ingredient_id or menu_item_id, lb, reason | per meal/day | loss_rates.csv, waste_benchmarks.csv |
| Transfer | id, from_hall, to_hall, ingredient_id, qty, date, status | event | sim output |
| Recommendation | id, hall_id, date, kind (use_first\|adjust_prep\|buy_less\|transfer\|recover), target, qty, est_lb_saved, est_usd_saved, rationale, inputs | daily | agent |

## Generator spec
- Python 3.12, `pandas`, `numpy`, `pyyaml`, `pytest`. Run with `uv run`.
- `generator/config/<scenario>.yaml`: normal_week, game_day, finals_week, holiday_short_week. Each sets seed, date range, diner multipliers per hall per meal, menu source weeks.
- Demand: diners per meal ~ Poisson(mean from hall_volume × scenario multiplier). Take rate per menu item from a station-level prior (entrée 0.35–0.55, side 0.2–0.4, etc.).
- Production: forecast = rolling mean of last same-weekday; prepared = forecast × overprep factor (1.05–1.20); served = min(prepared, demand); leftover = prepared − served.
- Ingredients: menu item → recipe → ingredient demand via yields.csv (as-purchased ÷ yield factor).
- Inventory: weekly deliveries sized to forecast demand × safety stock; lots age FIFO; `expiry = received + shelf_life`; expired lots become WasteEvent(kind=expired).
- Waste: pre_consumer = trim loss (loss_rates) + overprep leftover not reused; post_consumer = served × plate-waste-per-cover prior.
- Transfers: when hall A has a lot expiring in ≤2 days and hall B's menu needs that ingredient within the window, emit Transfer candidate.
- Output: `data/synthetic/<scenario>/*.csv` + `bundle.json` (what the app loads) + `summary.json` (aggregates vs benchmarks).

## Tests (must pass)
- Mass balance per hall-week: received + opening = served_lb + closing + waste_lb + transferred_out − transferred_in (tolerance 1%).
- Pre-consumer waste % of purchased within benchmark range from `waste_benchmarks.csv`.
- Plate waste lb/cover within benchmark range.
- Every synthetic menu item for a scraped week exists in `menu_items.csv` for that hall/date/meal.
- Determinism: same seed → identical output.
- Every ingredient referenced has shelf_life and yield rows.

## Evidence it's right (not us)
- Tests above pass against published ranges.
- `docs/how-we-built-the-numbers.md` table: our aggregate vs source range vs source URL.
- Replay: run on a real scraped menu week; recs reference only real menu items.

## Naming
Product name is **Second Serve** everywhere (app title, docs, bundle). Do not use the old name "SurplusSense".
