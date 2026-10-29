# Recipes and ingredients: how menu items become ingredient demand

Built by `scripts/build_recipes.py`. Run it with `uv run --with pandas python scripts/build_recipes.py`.
It is deterministic: same `menu_items.csv` gives byte-identical outputs. Rerun it whenever the menu scrape grows. `data/recipes/coverage.json` holds every number below and is regenerated on each run.

## Outputs (`data/recipes/`)

| File | What it is |
|---|---|
| `ingredients.csv` | 121 canonical institutional ingredients: id, name, category, default_unit, lb_per_unit, storage, role, notes, crosswalk to the research tables, used_in_recipes. `ingredient_id` and `unit` repeat `id` and `default_unit` for the generator loader. |
| `recipes.csv` | 1,048 recipes: 1,041 item-specific plus 7 generic per-category fallbacks. Columns: recipe_id, name, category, portions_per_batch (100), portion_oz, portion_lb, method, occurrences |
| `recipe_ingredients.csv` | recipe_id, ingredient_id, qty_per_batch, unit, qty_lb. `qty` repeats `qty_per_batch` for the generator loader. |
| `menu_item_map.csv` | One row per menu row: hall, date, meal_period, station, item_name, item_name_normalized, eatec_recipe_id, recipe_id, method, category. Each normalized name maps to exactly one recipe_id. Our recipe_id is not the Eatec id; the Eatec id is kept in eatec_recipe_id. |
| `menu_items_unique.csv` | One row per normalized item, with recipe_id, `method`, the `rule` that fired, category, occurrences, frequency rank and all source Eatec ids |
| `ingredient_rules.csv` | Priority-ordered regex table that maps label components to canonical ingredients. The first match wins. |
| `name_rules.csv` | Regex-to-ingredient-share table for items with no ingredient list |
| `unmatched_components.csv` | Label components no rule matched. They go to `misc_dry`. |
| `ingredient_demand_weights.csv` | lb of each ingredient summed over all menu occurrences, at one batch per occurrence. Use it to prioritize research gaps. |
| `coverage.json` | Coverage stats |

## Method

1. **Normalize and dedupe item names.** Lowercase, HTML-unescape, `&` becomes "and", quotes and punctuation are stripped, whitespace is collapsed. 1,044 raw names become 1,041 unique normalized items across 8,844 menu rows.
2. **Pick one label per item.** The most common `ingredients` string across halls and dates wins, with ties broken alphabetically. The most common station drives the category.
3. **Parse the label.** The Eatec label is a `;`-separated list of purchased components in label order, such as `Garlic Peeled; Oil Cooking Blend (...)`. The parser HTML-unescapes first, because `&amp;` contains a `;`. It then splits on `;` and `,` at parenthesis depth 0 only, keeps the component head, and drops water and packaging lines like `N/F Wrap Paper`.
4. **Map components to canonical ingredients** with `ingredient_rules.csv`. 99.92% of 5,907 parsed components match a rule. The rest go to `misc_dry`, which is 0.03% of demand lb.
5. **Allocate batch weight.** The labels carry no quantities, so weight is allocated transparently:
   - The batch weight is 100 portions × `portion_oz`, in edible-portion, as-served lb.
   - Each canonical ingredient has a role. A **trace** ingredient such as salt, spices, fresh herbs or soup base gets 0.5% of the batch. A **minor** ingredient such as oil, butter, garlic, vinegar, sauce or citrus gets 3%. Fixed shares are capped at 40% in total.
   - **Major** ingredients split the remainder by 1/rank in label order, because labels list components by predominance.
   - If an item has no major ingredient, as with a dressing or olive oil at the salad bar, its minors carry the dish.
   - In mayo-bound salads (egg, tuna, chicken, potato, pasta, coleslaw), mayonnaise is promoted to a major ingredient.
6. **Items with no label anywhere** are wayback HTML rows. They use `name_rules.csv`, a hand-written share template per dish pattern such as chili, oatmeal or tamale.
7. **Generic fallback.** An item with no label and no name rule maps to `r_generic_<category>`. Items in the top 300 by frequency would instead get a category template under their own recipe id. Neither path fires on the current data.
8. **Portion size.** `portion_oz` is the median Eatec serving size for the item. Values above 16 oz are dropped, because entries like `241.52 oz` for chicken salad or `56 oz` for steamed beets are pan weights. Without a usable value the category default applies.
9. **Units.** `qty_per_batch` is in the ingredient's `default_unit`, which is lb, gal or each. `qty_lb` is always given. `lb_per_unit` converts between them, for example 7.6 lb/gal for oil, 8.6 for milk and 0.33 lb per banana. These are recipe units, not purchase case sizes. Case sizes live in `data/raw/reference/ingredients.csv`.

**Quantity basis.** `qty_per_batch` is edible-portion, cooked weight. Rice, pasta, oats and legumes are therefore cooked weight. The generator must convert to as-purchased with `yields.csv`, as PLAN.md specifies: as-purchased = edible ÷ yield factor. Do not apply a cooking factor twice.

## Coverage on the current scrape (8,844 rows, 1,041 unique items)

| Method | % of menu occurrences | Unique items |
|---|---|---|
| nutrislice_ingredients | 97.77% | 934 |
| name_rule | 2.23% | 107 |
| generic_fallback | 0.00% | 0 |

- The top 300 items cover 81.86% of occurrences. 299 are mapped from their ingredient labels and 1, Mini Cinnamon Swirl Danish, from a name rule.
- Recipe categories break down as entree 492, side 239, salad 109, breakfast 77, dessert 65, soup 62 and beverage 3, plus the generics.

## Alignment with research tables

- `data/raw/reference/ingredients.csv` has 40 rows. It shares its free-text keys with `shelf_life.csv`, so one crosswalk in the script, `REF_XWALK`, aligns both.
  - 50 canonical ingredients point at a reference row. `reference_match` says whether the match is exact or a proxy.
  - Two reference rows have no direct target: `black beans, canned` and `chicken breast, boneless skinless`. The canned-bean bucket uses chickpeas and the raw-chicken bucket uses thigh.
- `shelf_life.csv` covers **67.2%** of demand lb.
- `loss_rates.csv`, from ERS LAFA, covers **81.4%** of demand lb.
- The script fails loudly if a crosswalk name disappears from either file.

**Largest shelf-life gaps by share of demand lb.** These are worth sending back to research:

| Ingredient | Share of demand lb |
|---|---|
| dressing | 3.4% |
| beets | 2.4% |
| dessert_prepared | 2.3% |
| meat_alt | 2.2% |
| potato_frozen | 1.8% |
| tomato_canned | 1.7% |
| fruit_dried | 1.2% |
| veg_other | 1.2% |
| beef_whole | 1.1% |
| nuts_seeds | 1.0% |
| cream_cheese | 0.8% |
| oil_cooking | 0.7% |

The full list is `ingredients_used_without_shelf_life_ref` in `coverage.json`.

TODO: if research adds ids to `ingredients.csv`, switch `REF_XWALK` from names to ids.

## Known weak spots

- **Quantities are inferred, not measured.** Eatec labels give order, not weights. The 1/rank and fixed-share scheme is defensible and monotone, but a specific recipe can be off by 2x on a secondary ingredient, for example coconut milk in a curry at 3%.
- **One batch per occurrence** in `ingredient_demand_weights.csv` overweights salad-bar toppings. It is a ranking aid only. Real production comes from the generator's diner counts and take rates.
- **Purchased composites stay composite.** `Pizza Cheese 16 In` is a whole frozen cheese pizza and maps to `pizza_base`. Ready-made soups map to `soup_prepared`, which is the largest single demand line. Mac & cheese and spring rolls map to `prepared_entree`. These are real purchase lines, but their waste can't be split into flour, cheese and so on.
- **Lamb has no bucket of its own.** It maps to `beef_whole`, the red-meat bucket.
- **Category buckets hide variety.** `spices` covers every spice, `dressing` covers every dressing, and `cheese_shredded_sliced` covers cheddar, jack, American and provolone. That is fine for lb and waste, but too coarse for price.
- **Category is rule-based.** Classification checks name first, then the most common station. Salad-bar proteins like Paprika Rosemary Tofu are classed as `salad`, and a few sauces are classed as `side`.
- **Name-rule items are guesses.** They cover 2.23% of occurrences and 107 items, mostly wayback-only dishes such as tamales, risotto, tri tip and caldo de pollo. Each one records its rule in `menu_item_map.csv`.
- **Serving-size outliers** above 16 oz are replaced by category defaults.
- **Normalization merges near-duplicates only by spelling.** "Halal Ground Beef" and "Ground Beef" stay distinct items, which is intentional because they are different products.
