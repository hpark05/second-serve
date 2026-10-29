# How we built the numbers

**Second Serve** is a pitch prototype. We have no Cal Dining internal data: no swipe counts, no production logs, no Leanpath waste exports. Every number in the demo comes from two places. The first is public information about Cal Dining itself, such as its published menus, hall pages, and sustainability pages. The second is national research on how much food campus dining halls buy, serve, and throw away. We combined the two in a simulation. The menus are real. The quantities of food made, eaten, and wasted are simulated, and tuned to match the published research ranges below.

## What's real

| What | Source | Year | Link |
|---|---|---|---|
| Menus: 4 halls (Crossroads, Café 3, Foothill, Clark Kerr), 8,844 menu rows, about 1,040 distinct items. Includes stations, serving sizes, and ingredient labels. | Cal Dining public menu exports (Eatec system, not Nutrislice) | Oct 19 – Nov 2, 2026, plus 5 archived days from 2025–26 | [dining.berkeley.edu/menus](https://dining.berkeley.edu/menus/) |
| Diners per day: Crossroads 4,400, Café 3 over 2,500, Clark Kerr about 1,200. Foothill is not published. | Cal Dining hall pages | 2026, undated | [Dining commons](https://dining.berkeley.edu/locations/dining-commons/) |
| System volume: over 12,000 meal plan holders and over 5 million meals a year | UC Berkeley Dining job posting | 2026 | [Inside Higher Ed posting](https://careers.insidehighered.com/job/3539856/cook-5523c-berkeley-dining-88071/) |
| Hall facts: hours, stations, meal plan rules, weekly swipe expiry | Cal Dining hours and meal plan pages | 2026–27 | [Hours](https://dining.berkeley.edu/locations/hours-of-operation/) |
| Shelf life by food and storage type | USDA FSIS FoodKeeper | 2018 data | [FSIS FoodKeeper](https://www.fsis.usda.gov/shared/data/EN/FoodKeeper-Data.xls) |
| Yields: pounds purchased vs pounds served, after trim or cooking | USDA FNS Food Buying Guide | 2025 | [Food Buying Guide](https://foodbuyingguide.fns.usda.gov/) |
| Loss rates by food type | USDA ERS Loss-Adjusted Food Availability | 2010–2022 | [ERS LAFA](https://www.ers.usda.gov/data-products/food-availability-per-capita-data-system/) |
| Kitchen waste 4–10% of purchases | Leanpath (vendor) | 2018 | [Leanpath blog](https://blog.leanpath.com/college-food-waste-prevention) |
| Weighed waste audit of 4 campus dining halls | Costello et al., University of Missouri | 2015 | [Journal article](https://www.cambridge.org/core/journals/renewable-agriculture-and-food-systems/article/food-waste-in-campus-dining-operations-inventory-of-pre-and-postconsumer-mass-by-food-category-and-estimation-of-embodied-greenhouse-gas-emissions/3157B7B943CB89ABDEFD763EAA10F76F) |
| Waste per meal across 6 residential halls | University of Illinois | 2021 | [Illinois ACES](https://aces.illinois.edu/node/1232) |
| Food waste per student per meal at US colleges | US EPA Wasted Food Report | 2019 data | [EPA report](https://www.epa.gov/system/files/documents/2024-04/2019-wasted-food-report_508_opt_ec_4.23correction.pdf) |
| Plate waste per guest in higher ed | Bon Appétit Management Co. and NRDC | 2019 | [Press release](https://www.bamco.com/press-releases/study-finds-college-students-waste-112-pounds-of-food-per-school-year/) |
| Cal Dining's 2012 Leanpath pilot: kitchen waste fell from over 3,000 to about 2,000 lb a week | Berkeley News; StopWaste | 2012 | [Berkeley News](https://news.berkeley.edu/2012/11/15/america-recycles-day-epa-recognizes-campus-food-waste-reduction) |
| Cal Dining donates over 50,000 lb of food a semester | Cal Dining waste reduction page | 2026, undated | [Waste reduction](https://dining.berkeley.edu/sustainability/waste-reduction/) |
| UC policy: 90% waste diversion goal, food recovery reporting from FY2027-28 | UC Office of the President | current | [UC Sustainable Practices Policy](https://policy.ucop.edu/doc/3100155/SustainablePractices) |

The full list, with confidence ratings, is in `docs/sources.json`.

## What's simulated and how

We start with how many students eat at each hall, using the published daily counts. Each day and meal gets some random variation, plus scenario changes such as a game day or finals week. Each student picks items from the real menu for that hall and meal, at typical take rates for an entrée, side, or salad. Every menu item maps to a recipe built from its real ingredient label. The recipe turns portions into pounds of each ingredient. USDA yields convert those pounds to what the kitchen must buy, adding back trim and cooking loss. The kitchen preps a little more than it expects to serve, and weekly deliveries arrive in standard case sizes. Stock is used oldest first, and anything past its FoodKeeper shelf life is counted as expired. Waste is the sum of four parts: trim, extra food prepped but not served, expired stock, and food left on plates. We tune the simulation until its totals land inside the published ranges below.

## How our numbers compare

| Metric | Published range | Source | Second Serve synthetic |
|---|---|---|---|
| Kitchen (pre-consumer) waste, % of food purchased | 4–10% by value; 5.6% by weight | Leanpath 2018; Missouri 2015 | TBD |
| Plate (post-consumer) waste, % of food received | 10.7% by weight | Missouri 2015 | TBD |
| Total waste, % of food purchased | 8–15% by value (vendor); 16.3% by weight (measured) | Leanpath 2018; Missouri 2015 | TBD |
| Total food waste per meal | 0.21–0.44 lb | Illinois 2021; EPA 2019 | TBD |
| Plate waste per diner per meal | 2.18 oz edible; 76–111 g (2.7–3.9 oz) total | Bon Appétit/NRDC 2019; American University 2009 | TBD |
| Overproduction share of kitchen waste | 50–60% | Leanpath 2018; UMass Amherst 2017 | TBD |

## What we'd ask Cal Dining for in a pilot

1. **Your own waste data.** Cal Dining has run Leanpath in 9 back-of-house sites since 2021. Nothing measured has been published since about 2013. A few weeks of Leanpath exports, plus swipe counts by hall and meal, would replace our simulated waste with real waste.
2. **A real kitchen-waste baseline.** The common "4–10% of purchases" figure comes from one vendor. The best independent measurement is one campus in 2014. Cal Dining's numbers would give the industry a second data point and give Second Serve a true baseline.
3. **Case sizes and portions.** Our case weights for some items come from a 1992 USDA handbook or from federal school-lunch packs. Your purchasing data and real portion sizes would make the ordering advice accurate.

## Honest limits

- **Quantities are inferred.** Ingredient labels list what is in a dish, not how much. Recipe weights are estimates and may be off by up to 2x for a minor ingredient.
- **Diner counts are rounded marketing figures.** Foothill has no published count, so its volume is an estimate.
- **The research is national, not Berkeley.** Missouri, Illinois, and the EPA describe other campuses. Berkeley's real waste could sit outside those ranges.
- **Menu history is short.** We have about two weeks of Fall 2026 menus. We cannot yet see the full menu cycle or other seasons.
- **Matching the range is not proof.** Landing inside published ranges shows the simulation is plausible. It does not show it matches Cal Dining's kitchens.
