import type { Bundle, Recommendation } from './bundle'
import { hallName, idx, relDay } from './bundle-selectors'

/** The four things a chef needs to judge a recommendation, derived from the rec and its inputs. */
export interface Proposal {
  quantity: string
  intendedUse: string
  neededBy: string
  review: string[]
}

const num = (v: unknown) => (typeof v === 'number' ? v : Number(v))
const qty = (n: number, unit: string) => `${n.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${unit}`

export function proposalFor(b: Bundle, r: Recommendation): Proposal {
  const asOf = b.meta.as_of
  const i = r.inputs as Record<string, unknown>
  const ing = idx(b).ingredient.get(r.target.split('->')[0])
  const storage = ing?.storage ? `Storage: ${ing.storage}; check quality before use` : 'Check quality before use'

  switch (r.kind) {
    case 'use_first': {
      const planned = num(i.planned_use_lb ?? 0)
      return {
        quantity: `${qty(r.qty, r.unit)} beyond the ${qty(planned, 'lb')} already planned`,
        intendedUse: `Feature in a dish at ${hallName(b, r.hall_id)} (e.g. a While It Lasts station)`,
        neededBy: i.expiry_date ? `Before it expires ${relDay(String(i.expiry_date), asOf).toLowerCase()}` : 'Soon',
        review: [storage, 'Chef picks the dish; recipe and allergen labels must match'],
      }
    }
    case 'adjust_prep': {
      const item = idx(b).menuItem.get(r.target)
      const prepared = num(i.portions_prepared ?? 0)
      return {
        quantity: `Prep ${qty(prepared - r.qty, 'portions')} instead of ${qty(prepared, 'portions')}`,
        intendedUse: item ? `${item.name}, ${item.meal_period}` : r.target_name,
        neededBy: item ? `Before ${item.meal_period} prep, ${relDay(item.date, asOf).toLowerCase()}` : 'Next prep',
        review: [
          'Forecast is synthetic; chef confirms against expected headcount',
          'Keep a batch-cook buffer for late demand',
        ],
      }
    }
    case 'buy_less': {
      return {
        quantity: `Cut the standing order by ${qty(r.qty, r.unit)}`,
        intendedUse: `Next ${r.target_name.toLowerCase()} order for ${hallName(b, r.hall_id)}`,
        neededBy: 'Before the next order cutoff',
        review: ['Purchasing checks vendor case minimums', 'One week of expiry is a small sample'],
      }
    }
    case 'transfer': {
      const t = b.transfers.find((x) => x.transfer_id === i.transfer_id)
      return {
        quantity: qty(r.qty, r.unit),
        intendedUse: t ? `${hallName(b, t.to_hall)} menu within 2 days` : 'Receiving kitchen menu',
        neededBy: t ? `Picked up before it expires ${relDay(t.expiry_date, asOf).toLowerCase()}` : 'Before expiry',
        review: [storage, 'Receiving chef must accept; a coordinator must schedule pickup'],
      }
    }
    case 'recover': {
      return {
        quantity: qty(r.qty, r.unit),
        intendedUse: i.partner ? `Pickup by ${String(i.partner)}` : 'Campus food recovery pickup',
        neededBy: 'Same day, within safe holding time',
        review: ['Time and temperature logs required for donation', 'Only food never served to a diner'],
      }
    }
  }
}
