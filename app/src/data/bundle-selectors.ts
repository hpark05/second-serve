import type {
  Bundle,
  Hall,
  Ingredient,
  InventoryLot,
  MenuItem,
  Recipe,
  Recommendation,
  Transfer,
  WasteKind,
} from './bundle'
import type { HallFilter } from './useBundle'

/** Lots at or under this many days to expiry get the "Use First" flag. */
export const USE_FIRST_DAYS = 2
/** Campus Network looks this far ahead for surplus. */
export const SURPLUS_HORIZON_DAYS = 3

export const addDays = (iso: string, n: number) => {
  const d = new Date(`${iso}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

const DAY_MS = 86_400_000
/** Whole days from asOf to iso (positive = future). */
export const dayOffset = (iso: string, asOf: string) =>
  Math.round((Date.parse(`${iso}T12:00:00Z`) - Date.parse(`${asOf}T12:00:00Z`)) / DAY_MS)

// Why: the demo is a fictional scenario; calendar dates read as stale or real, so every date is shown relative to "today".
export function relDay(iso: string, asOf: string): string {
  const d = dayOffset(iso, asOf)
  if (d === 0) return 'Today'
  if (d === 1) return 'Tomorrow'
  if (d === -1) return 'Yesterday'
  return d > 0 ? `+${d}d` : `${-d}d ago`
}

/** Rewrites ISO dates inside generator prose (rec rationales) as relative days. */
export const relText = (text: string, asOf: string) =>
  text.replace(/\b\d{4}-\d{2}-\d{2}\b/g, (iso) => relDay(iso, asOf).replace(/^\+/, 'in ').toLowerCase())

export const lb = (n: number) => `${n >= 100 ? Math.round(n).toLocaleString() : n.toFixed(1)} lb`
export const usd = (n: number) => `$${Math.round(n).toLocaleString()}`
export const int = (n: number) => Math.round(n).toLocaleString()

interface Index {
  hall: Map<string, Hall>
  ingredient: Map<string, Ingredient>
  recipe: Map<string, Recipe>
  menuItem: Map<string, MenuItem>
}
const indexes = new WeakMap<Bundle, Index>()
export function idx(b: Bundle): Index {
  let i = indexes.get(b)
  if (!i) {
    i = {
      hall: new Map(b.halls.map((h) => [h.id, h])),
      ingredient: new Map(b.ingredients.map((x) => [x.ingredient_id, x])),
      recipe: new Map(b.recipes.map((x) => [x.recipe_id, x])),
      menuItem: new Map(b.menu_items.map((x) => [x.menu_item_id, x])),
    }
    indexes.set(b, i)
  }
  return i
}

export const inHall = (filter: HallFilter, hallId: string) => filter === 'all' || filter === hallId
export const hallName = (b: Bundle, id: string) => idx(b).hall.get(id)?.name ?? id
export const ingredientName = (b: Bundle, id: string) => idx(b).ingredient.get(id)?.name ?? id
export const dates = (b: Bundle) => {
  const out: string[] = []
  for (let d = b.meta.start_date; d <= b.meta.end_date; d = addDays(d, 1)) out.push(d)
  return out
}

export function inventoryOn(b: Bundle, date: string, hall: HallFilter): InventoryLot[] {
  return b.inventory.filter((r) => r.snapshot_date === date && inHall(hall, r.hall_id))
}

export function dinersOn(b: Bundle, date: string, hall: HallFilter) {
  const rows = b.diners.filter((r) => r.date === date && inHall(hall, r.hall_id))
  return { forecast: rows.reduce((a, r) => a + r.diners_forecast, 0), meals: rows.length }
}

export function recsOn(b: Bundle, date: string, hall: HallFilter): Recommendation[] {
  return b.recommendations.filter((r) => r.date === date && inHall(hall, r.hall_id))
}

export const sum = <T>(xs: T[], f: (x: T) => number) => xs.reduce((a, x) => a + f(x), 0)

export function menuOn(b: Bundle, date: string, hall: HallFilter): MenuItem[] {
  return b.menu_items.filter((m) => m.date === date && inHall(hall, m.hall_id))
}

/** Ingredients in this menu item's recipe that have a Use First lot at its hall. */
export function expiringIngredientsIn(b: Bundle, item: MenuItem, lots: InventoryLot[]): Ingredient[] {
  const recipe = idx(b).recipe.get(item.recipe_id)
  if (!recipe) return []
  const risky = new Set(
    lots.filter((l) => l.hall_id === item.hall_id && l.days_to_expiry <= USE_FIRST_DAYS).map((l) => l.ingredient_id),
  )
  return recipe.ingredients
    .filter((l) => risky.has(l.ingredient_id))
    .map((l) => idx(b).ingredient.get(l.ingredient_id))
    .filter((x): x is Ingredient => Boolean(x))
}

export interface DayWaste {
  date: string
  expired: number
  pre_consumer: number
  post_consumer: number
  total: number
}
export function wasteByDay(b: Bundle, hall: HallFilter): DayWaste[] {
  const by = new Map<string, DayWaste>(
    dates(b).map((d) => [d, { date: d, expired: 0, pre_consumer: 0, post_consumer: 0, total: 0 }]),
  )
  for (const w of b.waste) {
    if (!inHall(hall, w.hall_id)) continue
    const row = by.get(w.date)
    if (!row) continue
    row[w.kind as WasteKind] += w.lb
    row.total += w.lb
  }
  return [...by.values()]
}

export function avoidedByDay(b: Bundle, hall: HallFilter) {
  return dates(b).map((d) => ({ date: d, ...dedupedSavings(recsOn(b, d, hall)) }))
}

export interface HallNetworkRow {
  hall: Hall
  surplus: { ingredient: Ingredient; lb: number; expiry: string }[]
  outgoing: Transfer[]
  incoming: Transfer[]
  recover: Recommendation[]
}
export function campusNetwork(b: Bundle, date: string): HallNetworkRow[] {
  const lots = inventoryOn(b, date, 'all').filter((l) => l.days_to_expiry <= SURPLUS_HORIZON_DAYS)
  const transfers = b.transfers.filter((t) => t.date === date)
  const recover = recsOn(b, date, 'all').filter((r) => r.kind === 'recover')
  return b.halls.map((hall) => {
    const agg = new Map<string, { lb: number; expiry: string }>()
    for (const l of lots.filter((x) => x.hall_id === hall.id)) {
      const cur = agg.get(l.ingredient_id) ?? { lb: 0, expiry: l.expiry_date }
      cur.lb += l.qty_lb
      if (l.expiry_date < cur.expiry) cur.expiry = l.expiry_date
      agg.set(l.ingredient_id, cur)
    }
    const surplus = [...agg.entries()]
      .map(([id, v]) => ({ ingredient: idx(b).ingredient.get(id) as Ingredient, ...v }))
      .filter((s) => s.ingredient)
      .sort((a, b2) => b2.lb - a.lb)
    return {
      hall,
      surplus,
      outgoing: transfers.filter((t) => t.from_hall === hall.id),
      incoming: transfers.filter((t) => t.to_hall === hall.id),
      recover: recover.filter((r) => r.hall_id === hall.id),
    }
  })
}

const STOCK_KINDS = new Set(['use_first', 'transfer', 'buy_less'])

/**
 * Week totals with the generator's dedupe (generator/outputs.py): use_first, transfer and buy_less can all
 * target the same expiring stock, so cap them at what actually expired. Matches summary.json when hall = 'all'.
 */
export function weekSavings(b: Bundle, hall: HallFilter) {
  const recs = b.recommendations.filter((r) => inHall(hall, r.hall_id))
  const price = (iid: string) => idx(b).ingredient.get(iid)?.usd_per_lb ?? 0
  const expired = b.waste.filter((w) => w.kind === 'expired' && inHall(hall, w.hall_id))
  const stock = recs.filter((r) => STOCK_KINDS.has(r.kind))
  const rest = recs.filter((r) => !STOCK_KINDS.has(r.kind))
  return {
    lb:
      sum(rest, (r) => r.est_lb_saved) +
      Math.min(
        sum(expired, (w) => w.lb),
        sum(stock, (r) => r.est_lb_saved),
      ),
    usd:
      sum(rest, (r) => r.est_usd_saved) +
      Math.min(
        sum(expired, (w) => w.lb * price(w.ingredient_id)),
        sum(stock, (r) => r.est_usd_saved),
      ),
  }
}

const recLots = (r: Recommendation): string[] => {
  const i = r.inputs as Record<string, unknown>
  const out: string[] = []
  for (const k of ['lots', 'expired_lots']) if (Array.isArray(i[k])) out.push(...(i[k] as string[]))
  if (typeof i.lot_id === 'string') out.push(i.lot_id)
  return out
}

/** Same-day totals: count each lot once, keeping the most valuable rec that targets it. */
export function dedupedSavings(recs: Recommendation[]) {
  const seen = new Set<string>()
  let lbTotal = 0
  let usdTotal = 0
  for (const r of [...recs].sort((a, b) => b.est_usd_saved - a.est_usd_saved)) {
    const lots = recLots(r)
    if (lots.some((l) => seen.has(l))) continue
    for (const l of lots) seen.add(l)
    lbTotal += r.est_lb_saved
    usdTotal += r.est_usd_saved
  }
  return { lb: lbTotal, usd: usdTotal }
}

/** Days of forecast production that count as "allocated" stock in Inventory. */
export const ALLOCATION_DAYS = 2

/**
 * Allocated lb per lot: forecast production for today and tomorrow, converted to ingredient lb through the
 * recipe, drawn from each hall's lots soonest-expiry first. Fixture recipes lack qty_lb and allocate nothing.
 */
export function allocationsOn(b: Bundle, date: string, hall: HallFilter): Map<string, number> {
  const until = addDays(date, ALLOCATION_DAYS - 1)
  const need = new Map<string, number>()
  const { menuItem, recipe } = idx(b)
  for (const p of b.production) {
    if (p.date < date || p.date > until || !inHall(hall, p.hall_id)) continue
    const r = recipe.get(menuItem.get(p.menu_item_id)?.recipe_id ?? '')
    if (!r?.portions_per_batch) continue
    for (const line of r.ingredients) {
      if (!line.qty_lb) continue
      const k = `${p.hall_id}|${line.ingredient_id}`
      need.set(k, (need.get(k) ?? 0) + (p.portions_forecast / r.portions_per_batch) * line.qty_lb)
    }
  }
  const out = new Map<string, number>()
  const lots = inventoryOn(b, date, hall).sort((x, y) => x.expiry_date.localeCompare(y.expiry_date))
  for (const l of lots) {
    const k = `${l.hall_id}|${l.ingredient_id}`
    const left = need.get(k) ?? 0
    const take = Math.min(left, l.qty_lb)
    out.set(l.lot_id, take)
    need.set(k, left - take)
  }
  return out
}
