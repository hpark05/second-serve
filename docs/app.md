# Second Serve app

The real app lives in `app/`. It is a static React site with no backend and no auth. It reads one JSON bundle per scenario and computes every number on screen from it.

Stack: Vite, React 19, TypeScript, Tailwind v4, shadcn/ui on Radix, Lucide icons, Motion, Biome, pnpm.

## Run it

```sh
cd app
pnpm install
pnpm dev            # syncs bundles, then serves http://localhost:5173/second-serve/
pnpm build          # syncs bundles, typechecks, builds to app/dist
pnpm preview        # serves the built site
pnpm check          # Biome lint + format check (pnpm format to auto-fix)
```

## Where the data comes from

| Path | What it is |
|---|---|
| `data/synthetic/<scenario>/bundle.json` | Generator output. This is the source of truth. |
| `app/public/data/<scenario>/bundle.json` | A copy made by `pnpm data:sync`. Both `dev` and `build` run it first. It is gitignored. |
| `app/public/data/fixture/bundle.json` | A small illustrative bundle from `pnpm data:fixture`. It is committed. The app falls back to it when a scenario bundle is missing. |

The scenarios are normal_week, game_day, finals_week and holiday_short_week. The header switcher picks one. A "Fixture data" badge appears in the header whenever the fixture is being shown.

## The data contract in code

- `app/src/data/bundle.ts` holds the TypeScript types. They mirror the generator's records field for field.
- `app/src/data/normalize-bundle.ts` maps the generator's `id` keys onto the app's `ingredient_id`, `recipe_id` and `menu_item_id`. It also derives display names for recommendations. This is the only place that adapts generator output.
- `app/src/data/useBundle.ts` is the single loader and hook. Swapping data sources is a one-line change to its URL constants.
- `app/src/data/bundle-selectors.ts` holds the pure functions pages use, such as inventory on a date, recommendations for a hall, and waste by day.

The prose contract is the bundle.json section of `docs/data-model.md`. The app needs the daily inventory snapshots, because Dashboard, Inventory and Campus Network read the `meta.as_of` snapshot. Do not build bundles with `bundle.inventory_snapshots: ends`.

## What is wired and what is not

| Area | Status |
|---|---|
| All seven pages, hall switcher, scenario switcher | Read the generated bundle |
| "Today" | `meta.as_of` from the bundle. Every date is shown relative to it. |
| Impact CO₂e and meals factors | `meta.factors` from the bundle |
| Dollar figures | `est_usd_saved` from the generator, priced from per-ingredient wholesale prices (`usd_per_lb`, with `usd_per_lb_low` and `usd_per_lb_high`). Headline totals use `weekSavings`, the generator's dedupe. Impact shows the low to high range from `summary.json`, which `pnpm data:sync` now copies too. `meta.factor_sources.blended_usd_per_lb_reference` is reference only and unused. |
| Recommendation status, Apply Plan, "Request transfer", recovery pickup, the sample walkthrough | Session-only UI state. Nothing is sent or saved. |
| Meal Planning swaps | Computed in the app. A dish is swapped only for another dish the same station serves that week, and plant-based dishes are never swapped out. |
| Login | Fake. Any credentials work. The hall pick sets the default hall. |
| `/sources` ("How we built the numbers") | Renders `docs/sources.json` and the bundle's factor sources. Illustrative chips deep-link to a row. |
| Food photos | Matched by keyword from `app/public/img`. Unmatched items show a utensil icon. |

## Sample transfer walkthrough

One explicitly fictional transfer runs end to end for staff to evaluate. Spinach moves from Crossroads (Kitchen A) to Café 3 (Kitchen B). The rules are in `docs/transfer-flow.md` and the talk track is in `docs/demo-script.md`.

| Path | What it is |
|---|---|
| `app/public/data/scenario-spinach.json` | The scenario fixture. Every number, time, person and log line on the walkthrough comes from it. |
| `app/src/data/scenario.ts` | Its types. |
| `app/src/walkthrough/` | The store, steps, role switcher, action cards, tier counters, checks and activity log. |

- **Steps.** `/walkthrough/1` to `/walkthrough/6` follow the demo script. Next stays disabled until the step's action is done. Back rewinds to that step's finished state. Opening a step you have not reached sends you to the first open step. The login page stays at `/` and is not part of the walkthrough.
- **Roles.** Inside the walkthrough a full-width "Hand the iPad to …" card switches the role when tapped. The header role switcher appears only on the free-roam pages, where it also sets the hall filter.
- **Stage display.** The page's stage header is the only place that shows "02 Request a transfer · Step 3 of 6". At 1024px and wider the sidebar lists the three stages as navigation. Below 1024px the walkthrough has no top bar.
- **How it plays.** The store keeps an append-only list of applied events. Each click applies the fixture's next event for that role. Paths branch by event type, so Accept follows the happy path and Decline follows the decline path. A decline reason other than the fixture's writes a new log line.
- **Planned, completed, verified.** Only Kitchen B's accept sets Planned. The handoff and the use record set Completed, which shows as "Reported" and is labelled self-reported. Verified comes only from the fixture's `records_imported` events, and no button applies those. Step 6 plays them as the simulated next-morning Eatec exports. Until then the Verified tile reads "Not yet verified" and the checks list what would verify it. The three tiles are never added together.
- **Overlay.** The scenario sits on top of the generated bundle. Inventory pins the sample spinach row first with a "Sample data" badge. Campus Network shows the sample transfer for the current role above the generated network.

## Routes

| Route | What it is |
|---|---|
| `/` | Fake login |
| `/dashboard`, `/inventory`, `/recommendations`, `/campus`, `/meal-planning`, `/impact`, `/sources` | Free-roam app pages |
| `/walkthrough/1` to `/walkthrough/6` | Participant walkthrough, one step per route |
| `/walkthrough/decline`, `/walkthrough/expired` | The two variants |
| `/present` | Hands-free presenter loop with no app chrome. `/walkthrough/1?autoplay=1` redirects here. `?speed=N` speeds it up for tests. |

## Presenter mode

`/present` plays steps 1 to 6, shows a 6 second end card, restarts and loops. A caption bar at the bottom shows the stage, the step and the presenter line.

| Key or input | Effect |
|---|---|
| Space | Pause or resume |
| Left / right arrow | Previous or next step. This also pauses. |
| Any other key, or a tap outside the caption bar | Pause |
| Caption bar buttons | Previous, play or pause, next |

## iPad notes

- Built for 768×1024 portrait and 1024×768 landscape. Every control is at least 44px, and walkthrough primaries are 48px.
- The Back and Next bar is sticky at the bottom and respects the home-indicator safe area.
- Double taps are harmless because each event applies once.
- Restart sample resets the route, the role and the history together.

## Provenance rules

- Free-roam pages show dates relative to the simulated today, such as Today, Tomorrow, +2d or 3d ago. Rec rationales are rewritten the same way.
- Walkthrough and presenter screens use weekday names from the fixture's `today_weekday` instead. Fixture prose such as "day 1 lunch" or "today 14:00" is rewritten at display time.
- Inventory shows Allocated, Available, Last updated and Source. For generated lots, Allocated is the next 2 days of forecast production, drawn from the soonest-expiring lots first.
- Every Impact figure and every recommendation saving carries an "Illustrative" chip. It links to that figure's row on `/sources`, which renders `docs/sources.json` directly plus the bundle's conversion factors.
- Recommendations are proposal cards. Each shows quantity, intended use, needed-by and what needs review. Clicks move a card from Planned to Completed only. Verified always reads "Not yet verified", with the record that would verify it.
- Campus Network buttons read "Request transfer". A request is not a plan, so it does not mark the matching recommendation planned.

## Deploy

### GitHub Pages (default)

`vite.config.ts` sets the base to `/second-serve/`. The build copies `index.html` to `404.html`, so deep links like `/second-serve/walkthrough/1` and `/second-serve/present` load the app. Pages returns them with HTTP 404, which browsers still render.

The repo root `index.html` is the old static mockup. To ship the app instead:

1. In GitHub, set Settings, then Pages, then Source to "GitHub Actions".
2. Add `.github/workflows/pages.yml` that checks out the repo, sets up pnpm and Node, runs `pnpm install --frozen-lockfile` and `pnpm build` in `app/`, uploads `app/dist` with `actions/upload-pages-artifact`, and publishes with `actions/deploy-pages`.
3. The site then serves `app/dist` at `https://<owner>.github.io/second-serve/`, replacing the mockup. Keep or delete the root `index.html`; Pages no longer reads it.

`pnpm build` runs `pnpm data:sync` first, so the workflow needs `data/synthetic/` in the repo. Without it the app falls back to the fixture bundle.

### Vercel

`app/vercel.json` builds with `pnpm build:vercel`, which sets `VITE_BASE=/`, and rewrites app routes to `index.html`. Set the Vercel project root directory to `app/`. Routes then live at `/walkthrough/1` and `/present`.

Each generated bundle is about 5 MB, served compressed by both hosts.
