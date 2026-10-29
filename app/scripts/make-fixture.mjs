// Writes public/data/fixture/bundle.json: a small, deterministic, ILLUSTRATIVE bundle so the app runs
// before the generator ships. Numbers here are not sourced; the generator's bundles replace them.
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'

const OUT = path.join(import.meta.dirname, '..', 'public', 'data', 'fixture', 'bundle.json')

// Mulberry32: tiny seeded PRNG so reruns produce byte-identical output.
function prng(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const rand = prng(20261019)
const between = (lo, hi) => lo + (hi - lo) * rand()
const r2 = (n) => Math.round(n * 100) / 100

const DATES = ['2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22', '2026-10-23', '2026-10-24', '2026-10-25']
const AS_OF = '2026-10-21'
const addDays = (iso, n) => {
  const d = new Date(`${iso}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}
const diff = (a, b) => Math.round((new Date(`${a}T12:00:00Z`) - new Date(`${b}T12:00:00Z`)) / 86400000)

const halls = [
  { id: 'crossroads', name: 'Crossroads', seats: 750, covers_per_day: 4200 },
  { id: 'cafe-3', name: 'Café 3', seats: 400, covers_per_day: 2300 },
  { id: 'foothill', name: 'Foothill', seats: 330, covers_per_day: 1500 },
  { id: 'clark-kerr', name: 'Clark Kerr', seats: 420, covers_per_day: 1800 },
].map((h) => ({
  ...h,
  covers_source: { metric: 'fixture', formula: 'Illustrative placeholder, not sourced' },
  hours: { breakfast: '7:00-10:30', lunch: '11:00-15:00', dinner: '17:00-21:00' },
  feeder_housing: null,
  residents: null,
}))

const ingredients = [
  ['spinach', 'Spinach', 'produce', 'lb', 1, 5, 'walk-in', 3.1],
  ['chicken', 'Chicken Breast', 'protein', 'lb', 1, 4, 'walk-in', 3.6],
  ['peppers', 'Bell Peppers', 'produce', 'lb', 1, 7, 'walk-in', 2.4],
  ['yogurt', 'Greek Yogurt', 'dairy', 'lb', 1, 10, 'walk-in', 2.9],
  ['rice', 'Brown Rice', 'grain', 'lb', 1, 180, 'dry', 1.1],
  ['cheddar', 'Cheddar Cheese', 'dairy', 'lb', 1, 21, 'walk-in', 4.2],
  ['tomatoes', 'Tomatoes', 'produce', 'lb', 1, 6, 'walk-in', 2.2],
  ['milk', 'Whole Milk', 'dairy', 'gal', 8.6, 9, 'walk-in', 0.55],
  ['bananas', 'Bananas', 'produce', 'lb', 1, 5, 'ambient', 0.7],
  ['quinoa', 'Quinoa', 'grain', 'lb', 1, 240, 'dry', 3.0],
  ['roll', 'Whole Grain Rolls', 'bakery', 'dozen', 1.5, 3, 'ambient', 2.6],
].map(([ingredient_id, name, category, unit, lb_per_unit, shelf_life_days, storage, usd_per_lb]) => ({
  ingredient_id,
  name,
  category,
  unit,
  lb_per_unit,
  shelf_life_days,
  storage,
  usd_per_lb,
}))
const ING = Object.fromEntries(ingredients.map((i) => [i.ingredient_id, i]))

const recipes = [
  [
    'r-grilled-chicken',
    'Grilled Chicken',
    'entree',
    [
      ['chicken', 0.33],
      ['peppers', 0.05],
    ],
  ],
  [
    'r-chicken-spinach',
    'Grilled Chicken with Spinach',
    'entree',
    [
      ['chicken', 0.3],
      ['spinach', 0.08],
    ],
  ],
  [
    'r-roasted-veg',
    'Roasted Vegetables',
    'side',
    [
      ['peppers', 0.12],
      ['tomatoes', 0.1],
    ],
  ],
  [
    'r-quinoa-salad',
    'Quinoa Salad',
    'side',
    [
      ['quinoa', 0.08],
      ['tomatoes', 0.05],
      ['spinach', 0.03],
    ],
  ],
  ['r-roll', 'Whole Grain Roll', 'side', [['roll', 0.06]]],
  [
    'r-rice-bowl',
    'Brown Rice Bowl',
    'entree',
    [
      ['rice', 0.15],
      ['peppers', 0.06],
      ['chicken', 0.12],
    ],
  ],
  [
    'r-mac',
    'Baked Mac and Cheese',
    'entree',
    [
      ['cheddar', 0.12],
      ['milk', 0.01],
    ],
  ],
  [
    'r-parfait',
    'Yogurt Parfait',
    'breakfast',
    [
      ['yogurt', 0.25],
      ['bananas', 0.1],
    ],
  ],
  [
    'r-spinach-salad',
    'Spinach and Tomato Salad',
    'side',
    [
      ['spinach', 0.12],
      ['tomatoes', 0.08],
    ],
  ],
].map(([recipe_id, name, role, lines]) => ({
  recipe_id,
  name,
  role,
  portions_per_batch: 50,
  ingredients: lines.map(([ingredient_id, qty]) => ({ ingredient_id, qty, unit: 'lb' })),
}))
const REC = Object.fromEntries(recipes.map((r) => [r.recipe_id, r]))

const MEALS = { lunch: 0.42, dinner: 0.58 }
const TAKE = { entree: 0.4, side: 0.28, breakfast: 0.3 }
const ROTATION = [
  ['r-grilled-chicken', 'r-roasted-veg', 'r-quinoa-salad', 'r-roll'],
  ['r-rice-bowl', 'r-spinach-salad', 'r-roll', 'r-parfait'],
  ['r-mac', 'r-roasted-veg', 'r-quinoa-salad', 'r-roll'],
]

const stations = []
const menu_items = []
const production = []
const diners = []
const waste = []
const usage = {} // hall|date|ingredient -> lb planned

for (const h of halls) {
  for (const s of ['Grill', 'Global', 'Salad Bar', 'Bakery']) {
    stations.push({ id: `${h.id}:${s.toLowerCase().replace(/ /g, '-')}`, hall_id: h.id, name: s, cuisine: null })
  }
  DATES.forEach((date, di) => {
    for (const [meal, share] of Object.entries(MEALS)) {
      const forecast = h.covers_per_day * share
      const actual = Math.round(forecast * between(0.85, 1.12))
      diners.push({
        hall_id: h.id,
        date,
        meal_period: meal,
        diners_forecast: r2(forecast),
        diners_actual: actual,
        multiplier: 1,
      })
      const rot = ROTATION[(di + (meal === 'dinner' ? 1 : 0)) % ROTATION.length]
      rot.forEach((recipe_id, idx) => {
        const recipe = REC[recipe_id]
        const mid = `${h.id}:${date}:${meal}:${String(idx).padStart(3, '0')}`
        const take = TAKE[recipe.role]
        const pf = forecast * take
        const prepared = Math.round(pf * between(1.05, 1.2))
        const served = Math.min(prepared, Math.round(actual * take * between(0.9, 1.05)))
        const left = prepared - served
        menu_items.push({
          menu_item_id: mid,
          hall_id: h.id,
          date,
          meal_period: meal,
          station_id: `${h.id}:${idx === 3 ? 'bakery' : idx === 0 ? 'grill' : 'global'}`,
          name: recipe.name,
          recipe_id,
          serving_lb: r2(recipe.ingredients.reduce((a, l) => a + l.qty, 0)),
          take_rate: take,
          station_role: recipe.role,
        })
        production.push({
          hall_id: h.id,
          date,
          meal_period: meal,
          menu_item_id: mid,
          portions_forecast: r2(pf),
          portions_prepared: prepared,
          portions_served: served,
          portions_wasted: Math.round(left * 0.4),
          portions_donated: Math.round(left * 0.15),
          portions_repurposed: left - Math.round(left * 0.4) - Math.round(left * 0.15),
        })
        for (const l of recipe.ingredients) {
          const k = `${h.id}|${date}|${l.ingredient_id}`
          usage[k] = (usage[k] ?? 0) + l.qty * prepared
        }
        if (left > 0) {
          const lbPer = recipe.ingredients.reduce((a, l) => a + l.qty, 0)
          waste.push({
            hall_id: h.id,
            date,
            meal_period: meal,
            kind: 'pre_consumer',
            reason: 'overproduction',
            ingredient_id: '',
            menu_item_id: mid,
            lot_id: '',
            lb: r2(Math.round(left * 0.4) * lbPer),
          })
          waste.push({
            hall_id: h.id,
            date,
            meal_period: meal,
            kind: 'post_consumer',
            reason: 'plate_waste',
            ingredient_id: '',
            menu_item_id: mid,
            lot_id: '',
            lb: r2(served * lbPer * between(0.12, 0.2)),
          })
        }
      })
    }
  })
}

// Lots: one delivery per ingredient per hall sized to ~5 days of use, a second mid-week; FIFO decay.
const inventory = []
let lotSeq = 0
const lots = []
for (const h of halls) {
  for (const ing of ingredients) {
    const daily = DATES.reduce((a, d) => a + (usage[`${h.id}|${d}|${ing.ingredient_id}`] ?? 0), 0) / DATES.length
    if (!daily) continue
    for (const recv of ['2026-10-17', '2026-10-21']) {
      const shelf = ing.shelf_life_days
      const expiry = addDays(recv, Math.min(shelf, 30) - (rand() < 0.35 ? 2 : 0))
      const qty_lb = r2(daily * 0.5 * Math.min(shelf - 1, 4) * between(0.9, 1.25))
      lots.push({
        lot_id: `L${String(++lotSeq).padStart(7, '0')}`,
        hall_id: h.id,
        ingredient_id: ing.ingredient_id,
        received_date: recv,
        expiry_date: expiry,
        qty_lb,
        daily,
      })
    }
  }
}
for (const d of [addDays(DATES[0], -1), ...DATES]) {
  for (const l of lots) {
    if (diff(d, l.received_date) < 0 || diff(l.expiry_date, d) <= 0) continue
    const used = l.daily * diff(d, l.received_date) * 0.6
    const lb = r2(Math.max(0, l.qty_lb - used))
    if (lb <= 0.05) continue
    const ing = ING[l.ingredient_id]
    inventory.push({
      snapshot_date: d,
      snapshot: d === DATES.at(-1) ? 'closing' : d < DATES[0] ? 'opening' : 'daily',
      lot_id: l.lot_id,
      hall_id: l.hall_id,
      ingredient_id: l.ingredient_id,
      qty: r2(lb / ing.lb_per_unit),
      unit: ing.unit,
      qty_lb: lb,
      received_date: l.received_date,
      expiry_date: l.expiry_date,
      origin: l.received_date === '2026-10-17' ? 'opening' : 'delivery',
      days_to_expiry: diff(l.expiry_date, d),
    })
  }
  for (const l of lots) {
    if (l.expiry_date !== d) continue
    const left = l.qty_lb - l.daily * diff(d, l.received_date) * 0.6
    if (left > 0.5)
      waste.push({
        hall_id: l.hall_id,
        date: d,
        meal_period: '',
        kind: 'expired',
        reason: 'expired_in_storage',
        ingredient_id: l.ingredient_id,
        menu_item_id: '',
        lot_id: l.lot_id,
        lb: r2(left),
      })
  }
}

// Transfers + recommendations for AS_OF, derived from the AS_OF snapshot so every card points at a real lot.
const today = inventory.filter((r) => r.snapshot_date === AS_OF)
const atRisk = today.filter((r) => r.days_to_expiry <= 2)
const need = (hall, iid) => [1, 2].reduce((a, k) => a + (usage[`${hall}|${addDays(AS_OF, k)}|${iid}`] ?? 0), 0)
const transfers = []
const recommendations = []
let recSeq = 0
const rec = (o) => recommendations.push({ id: `R${String(++recSeq).padStart(4, '0')}`, date: AS_OF, inputs: {}, ...o })

for (const lot of atRisk) {
  const ing = ING[lot.ingredient_id]
  const own = need(lot.hall_id, lot.ingredient_id) * 0.5
  const excess = lot.qty_lb - own
  rec({
    hall_id: lot.hall_id,
    kind: 'use_first',
    target: lot.ingredient_id,
    target_name: ing.name,
    qty: r2(Math.min(lot.qty_lb, Math.max(own, lot.qty_lb * 0.5))),
    unit: 'lb',
    est_lb_saved: r2(Math.min(lot.qty_lb, Math.max(own, lot.qty_lb * 0.5))),
    est_usd_saved: r2(Math.min(lot.qty_lb, Math.max(own, lot.qty_lb * 0.5)) * ing.usd_per_lb),
    rationale: `${r2(lot.qty_lb)} lb of ${ing.name.toLowerCase()} expires ${lot.expiry_date} (${lot.days_to_expiry} day${lot.days_to_expiry === 1 ? '' : 's'}). Pull it forward into tomorrow's menu before opening the newer lot.`,
    inputs: { lot_id: lot.lot_id, expiry_date: lot.expiry_date, qty_lb: r2(lot.qty_lb) },
  })
  if (excess <= 1) continue
  const taker = halls
    .filter((h) => h.id !== lot.hall_id)
    .map((h) => ({ h, n: need(h.id, lot.ingredient_id) }))
    .sort((a, b) => b.n - a.n)[0]
  let remaining = excess
  if (taker && taker.n > 1) {
    const qty = r2(Math.min(excess * 0.6, taker.n * 0.4))
    remaining = excess - qty
    const tid = `T${String(transfers.length + 1).padStart(5, '0')}`
    transfers.push({
      transfer_id: tid,
      date: AS_OF,
      from_hall: lot.hall_id,
      to_hall: taker.h.id,
      ingredient_id: lot.ingredient_id,
      qty_lb: qty,
      lot_id: lot.lot_id,
      expiry_date: lot.expiry_date,
      status: 'proposed',
      est_lb_saved: qty,
    })
    rec({
      hall_id: lot.hall_id,
      kind: 'transfer',
      target: lot.ingredient_id,
      target_name: ing.name,
      qty,
      unit: 'lb',
      est_lb_saved: qty,
      est_usd_saved: r2(qty * ing.usd_per_lb),
      rationale: `${taker.h.name} plans ${r2(taker.n)} lb of ${ing.name.toLowerCase()} in the next 2 days. Send ${qty} lb on the afternoon shuttle instead of letting it expire here.`,
      inputs: { transfer_id: tid, to_hall: taker.h.id, lot_id: lot.lot_id },
    })
  }
  if (remaining > 2) {
    rec({
      hall_id: lot.hall_id,
      kind: 'recover',
      target: lot.ingredient_id,
      target_name: ing.name,
      qty: r2(remaining),
      unit: 'lb',
      est_lb_saved: r2(remaining),
      est_usd_saved: 0,
      rationale: `No hall can use the last ${r2(remaining)} lb of ${ing.name.toLowerCase()} before ${lot.expiry_date}. Flag it for a permitted food recovery pickup.`,
      inputs: { lot_id: lot.lot_id, partner: 'Berkeley Food Pantry' },
    })
  }
}
for (const h of halls) {
  const tomorrow = production.filter((p) => p.hall_id === h.id && p.date === addDays(AS_OF, 1))
  const top = tomorrow.sort((a, b) => b.portions_prepared - a.portions_prepared)[0]
  if (top) {
    const mi = menu_items.find((m) => m.menu_item_id === top.menu_item_id)
    const cut = Math.round(top.portions_prepared * 0.12)
    const lb = r2(cut * (mi.serving_lb ?? 0.3))
    const usd = r2(REC[mi.recipe_id].ingredients.reduce((a, l) => a + l.qty * cut * ING[l.ingredient_id].usd_per_lb, 0))
    rec({
      hall_id: h.id,
      kind: 'adjust_prep',
      target: mi.menu_item_id,
      target_name: mi.name,
      qty: cut,
      unit: 'portions',
      est_lb_saved: lb,
      est_usd_saved: usd,
      rationale: `Last two ${top.meal_period}s served about 88% of what was prepped for ${mi.name.toLowerCase()}. Prep ${top.portions_prepared - cut} portions instead of ${top.portions_prepared}.`,
      inputs: { menu_item_id: mi.menu_item_id, portions_prepared: top.portions_prepared },
    })
  }
  const slow = today
    .filter((r) => r.hall_id === h.id && ING[r.ingredient_id].shelf_life_days <= 10)
    .sort((a, b) => b.qty_lb - a.qty_lb)[0]
  if (slow) {
    const ing = ING[slow.ingredient_id]
    const q = r2(slow.qty_lb * 0.25)
    rec({
      hall_id: h.id,
      kind: 'buy_less',
      target: ing.ingredient_id,
      target_name: ing.name,
      qty: q,
      unit: 'lb',
      est_lb_saved: q,
      est_usd_saved: r2(q * ing.usd_per_lb),
      rationale: `${r2(slow.qty_lb)} lb on hand covers more than the next order cycle. Trim Friday's ${ing.name.toLowerCase()} order by ${q} lb.`,
      inputs: { lot_id: slow.lot_id },
    })
  }
}

const bundle = {
  meta: {
    scenario: 'fixture',
    description:
      'Illustrative fixture for app development. Not sourced. Replaced by generator bundles in data/synthetic/<scenario>/bundle.json.',
    start_date: DATES[0],
    end_date: DATES.at(-1),
    as_of: AS_OF,
    seed: 20261019,
    generated_at: '2026-10-27T00:00:00Z',
    source: 'fixture',
    factors: { lb_per_meal: 1.2, co2e_lb_per_lb: 2.5 },
  },
  halls,
  stations,
  ingredients,
  recipes: recipes.map(({ role: _role, ...r }) => r),
  menu_items,
  inventory,
  production,
  diners,
  waste,
  transfers,
  recommendations,
}

mkdirSync(path.dirname(OUT), { recursive: true })
writeFileSync(OUT, `${JSON.stringify(bundle)}\n`)
console.log(
  `wrote ${OUT}: ${inventory.length} lots, ${menu_items.length} menu items, ${recommendations.length} recs, ${transfers.length} transfers`,
)
