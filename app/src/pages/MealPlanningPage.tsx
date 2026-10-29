import { CalendarDays, ChevronLeft, ChevronRight, Repeat } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import type { Bundle, InventoryLot, MenuItem, Recipe } from '@/data/bundle'
import {
  addDays,
  dates,
  dedupedSavings,
  expiringIngredientsIn,
  hallName,
  idx,
  inventoryOn,
  lb,
  menuOn,
  recsOn,
  relDay,
  sum,
  USE_FIRST_DAYS,
  usd,
} from '@/data/bundle-selectors'
import { useBundle } from '@/data/useBundle'
import { Chip, IllustrativeTag, LIME_BUTTON, PageTitle, QUIET_BUTTON, Surface, TEXT_LINK } from './page-surfaces'

const KEEP_VISIBLE = 6
// Why: never swap a plant-based dish out; those diners have no alternative at that station.
const PLANT_BASED = /vegan|vegetarian|gardein|tofu|impossible|beyond/i

interface PlanRow {
  item: MenuItem
  uses: string[]
  swap?: { recipe: Recipe; ingredient: string }
}

/** For each Use First ingredient the day's menu ignores, swap the lowest-take item at that hall for a recipe that uses it. */
function buildPlan(b: Bundle, items: MenuItem[], lots: InventoryLot[]): PlanRow[] {
  const rows: PlanRow[] = items.map((item) => ({
    item,
    uses: expiringIngredientsIn(b, item, lots).map((i) => i.name),
  }))
  const byHall = Map.groupBy(rows, (r) => r.item.hall_id)
  for (const [hallId, hallRows] of byHall) {
    const covered = new Set(
      hallRows.flatMap(
        (r) =>
          idx(b)
            .recipe.get(r.item.recipe_id)
            ?.ingredients.map((l) => l.ingredient_id) ?? [],
      ),
    )
    const missing = [
      ...new Set(
        lots.filter((l) => l.hall_id === hallId && l.days_to_expiry <= USE_FIRST_DAYS).map((l) => l.ingredient_id),
      ),
    ].filter((id) => !covered.has(id))
    const onMenu = new Set(hallRows.map((r) => r.item.recipe_id))
    // Why: swap within a station using a dish that station serves this week, so suggestions stay on real menus (PLAN.md).
    const weekByStation = Map.groupBy(
      b.menu_items.filter((m) => m.hall_id === hallId),
      (m) => m.station_id,
    )
    for (const iid of missing) {
      for (const slot of hallRows.filter((r) => !r.swap && r.uses.length === 0 && !PLANT_BASED.test(r.item.name))) {
        const alt = weekByStation
          .get(slot.item.station_id)
          ?.map((m) => idx(b).recipe.get(m.recipe_id))
          .find((rc) => rc && !onMenu.has(rc.recipe_id) && rc.ingredients.some((l) => l.ingredient_id === iid))
        if (!alt) continue
        slot.swap = { recipe: alt, ingredient: idx(b).ingredient.get(iid)?.name ?? iid }
        onMenu.add(alt.recipe_id)
        break
      }
    }
  }
  return rows
}

export function MealPlanningPage() {
  const { bundle, hall, approve, applyPlan, planApplied } = useBundle()
  const navigate = useNavigate()
  const all = dates(bundle)
  const firstPlannable = addDays(bundle.meta.as_of, 1)
  const [date, setDate] = useState(all.includes(firstPlannable) ? firstPlannable : bundle.meta.as_of)
  const i = all.indexOf(date)
  const lots = useMemo(() => inventoryOn(bundle, bundle.meta.as_of, hall), [bundle, hall])

  const plan = useMemo(() => {
    const seen = new Set<string>()
    const items = menuOn(bundle, date, hall).filter((m) => {
      const k = `${m.hall_id}|${m.name}`
      return !seen.has(k) && seen.add(k)
    })
    return buildPlan(bundle, items, lots)
  }, [bundle, date, hall, lots])

  const recs = recsOn(bundle, bundle.meta.as_of, hall).filter((r) => r.kind === 'use_first' || r.kind === 'adjust_prep')
  const swaps = plan.filter((p) => p.swap).length

  const apply = () => {
    for (const r of recs) approve(r.id)
    applyPlan()
    toast.success('Plan applied', { description: 'Kitchen board and prep sheet updated.' })
    setTimeout(() => navigate('/impact'), 900)
  }

  const [showAll, setShowAll] = useState(false)
  // Why: generated menus list every condiment; lead with what the agent changed and fold the rest.
  const rank = (p: PlanRow) => (p.swap ? 0 : p.uses.length ? 1 : 2)
  const grouped = Map.groupBy(
    [...plan].sort((a, b) => rank(a) - rank(b)),
    (p) => p.item.hall_id,
  )
  const hidden = showAll
    ? 0
    : sum([...grouped.values()], (rows) => rows.filter((p, n) => n >= KEEP_VISIBLE && rank(p) === 2).length)

  const savings = dedupedSavings(recs)

  return (
    <div className="max-w-[760px]">
      <PageTitle title="Meal planning" sub="Menu suggestions that use expiring stock first, by day and hall." />

      <div className="mb-6 flex items-center gap-2">
        <Button
          variant="outline"
          className={`${QUIET_BUTTON} w-11 px-0`}
          disabled={i <= 0}
          onClick={() => setDate(all[i - 1])}
          aria-label="Previous day"
        >
          <ChevronLeft />
        </Button>
        <span className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg border border-border bg-card text-[15px] font-medium">
          <CalendarDays className="size-4 text-muted-foreground" aria-hidden="true" />
          {relDay(date, bundle.meta.as_of)}
        </span>
        <Button
          variant="outline"
          className={`${QUIET_BUTTON} w-11 px-0`}
          disabled={i >= all.length - 1}
          onClick={() => setDate(all[i + 1])}
          aria-label="Next day"
        >
          <ChevronRight />
        </Button>
      </div>

      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-heading text-[18px] font-semibold text-foreground">Suggested menu</h2>
        <span className="text-[13px] text-muted-foreground">
          {swaps} swap{swaps === 1 ? '' : 's'} from expiring stock
        </span>
      </div>

      <div className="space-y-4">
        {[...grouped].map(([hallId, rows]) => (
          <Surface key={hallId} className="py-2">
            {hall === 'all' ? (
              <h3 className="pt-3 pb-1 font-heading text-[16px] font-semibold text-foreground">
                {hallName(bundle, hallId)}
              </h3>
            ) : null}
            <ul className="divide-y divide-border">
              {(showAll ? rows : rows.filter((p, n) => n < KEEP_VISIBLE || rank(p) < 2)).map(({ item, uses, swap }) => (
                <li key={item.menu_item_id} className="flex items-center gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    {swap ? (
                      <>
                        <p className="text-[15px] font-medium text-foreground">{swap.recipe.name}</p>
                        <p className="mt-0.5 flex items-center gap-1 text-[13px] text-muted-foreground">
                          <Repeat className="size-3.5 shrink-0" aria-hidden="true" />
                          Replaces {item.name}. Uses {swap.ingredient.toLowerCase()}, expiring soon.
                        </p>
                      </>
                    ) : (
                      <>
                        <p className="truncate text-[15px] font-medium text-foreground">{item.name}</p>
                        <p className="mt-0.5 text-[13px] text-muted-foreground capitalize">
                          {item.meal_period} ·{' '}
                          <span className="normal-case">
                            {uses.length ? `Uses ${uses.join(', ').toLowerCase()}, expiring soon` : 'Enough stock'}
                          </span>
                        </p>
                      </>
                    )}
                  </div>
                  {swap ? (
                    <Chip tone="planned">Swap</Chip>
                  ) : uses.length ? (
                    <Chip tone="verified">Uses stock</Chip>
                  ) : (
                    <Chip>Keep</Chip>
                  )}
                </li>
              ))}
            </ul>
          </Surface>
        ))}
      </div>
      {hidden > 0 ? (
        <button type="button" onClick={() => setShowAll(true)} className={`${TEXT_LINK} mt-2`}>
          Show {hidden} more unchanged item{hidden === 1 ? '' : 's'}
        </button>
      ) : null}
      {plan.length === 0 ? <p className="text-muted-foreground">No menu published for this day.</p> : null}

      <Surface className="mt-6 flex flex-wrap items-center gap-4">
        <p className="min-w-0 flex-1 text-[14px] text-foreground">
          Estimated <span className="tabular font-semibold">{lb(savings.lb)}</span> of food waste prevented and{' '}
          <span className="tabular font-semibold">{usd(savings.usd)}</span> saved.{' '}
          <IllustrativeTag source="ingredient_prices" className="ml-1" />
        </p>
        <Button className={`${LIME_BUTTON} w-full sm:w-auto`} onClick={apply} disabled={planApplied}>
          {planApplied ? 'Plan applied' : 'Apply plan'}
        </Button>
      </Surface>
    </div>
  )
}
