import type { Bundle, Recommendation } from './bundle'

type Raw = Record<string, unknown>
const rows = (v: unknown): Raw[] => (Array.isArray(v) ? (v as Raw[]) : [])

/**
 * Maps the generator's bundle.json onto the app types. The generator keys entities by `id` and leaves
 * display names off recommendations; the fixture already matches, so every step is a no-op for it.
 */
export function normalizeBundle(raw: Raw): Bundle {
  const meta = (raw.meta ?? {}) as Raw
  const ingredients = rows(raw.ingredients).map((i) => ({
    ...i,
    ingredient_id: (i.ingredient_id ?? i.id) as string,
    usd_per_lb: (i.usd_per_lb ?? null) as number | null,
  }))
  const recipes = rows(raw.recipes).map((r) => ({ ...r, recipe_id: (r.recipe_id ?? r.id) as string }))
  const menu_items = rows(raw.menu_items).map((m) => ({ ...m, menu_item_id: (m.menu_item_id ?? m.id) as string }))

  const ingName = new Map(rows(raw.ingredients).map((i) => [String(i.ingredient_id ?? i.id), String(i.name)]))
  const itemName = new Map(rows(raw.menu_items).map((m) => [String(m.menu_item_id ?? m.id), String(m.name)]))
  const nameFor = (r: Raw): string => {
    if (typeof r.target_name === 'string') return r.target_name
    const target = String(r.target ?? '')
    if (r.kind === 'adjust_prep') return itemName.get(target) ?? target
    if (r.kind === 'recover' && !ingName.has(target)) return 'Prepared food'
    // Why: transfer targets arrive as "<ingredient_id>-><to_hall>".
    const iid = target.split('->')[0]
    return ingName.get(iid) ?? iid
  }
  const recommendations = rows(raw.recommendations).map(
    (r): Recommendation =>
      ({
        ...r,
        target_name: nameFor(r),
        est_lb_saved: Number(r.est_lb_saved ?? 0),
        est_usd_saved: Number(r.est_usd_saved ?? 0),
        inputs: (r.inputs ?? {}) as Recommendation['inputs'],
      }) as Recommendation,
  )

  return {
    ...(raw as unknown as Bundle),
    meta: {
      ...(meta as unknown as Bundle['meta']),
      source: (meta.source as Bundle['meta']['source']) ?? 'generator',
    },
    ingredients: ingredients as unknown as Bundle['ingredients'],
    recipes: recipes as unknown as Bundle['recipes'],
    menu_items: menu_items as unknown as Bundle['menu_items'],
    inventory: rows(raw.inventory) as unknown as Bundle['inventory'],
    waste: rows(raw.waste) as unknown as Bundle['waste'],
    transfers: rows(raw.transfers) as unknown as Bundle['transfers'],
    recommendations,
  }
}
