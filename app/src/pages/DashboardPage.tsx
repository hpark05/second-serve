import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router'
import { Legend, SERIES, StackedBars } from '@/components/charts/charts'
import { Button } from '@/components/ui/button'
import {
  addDays,
  dates,
  dedupedSavings,
  dinersOn,
  hallName,
  int,
  inventoryOn,
  lb,
  menuOn,
  recsOn,
  relDay,
  USE_FIRST_DAYS,
  usd,
  wasteByDay,
} from '@/data/bundle-selectors'
import { useBundle } from '@/data/useBundle'
import { Figure, IllustrativeTag, LIME_BUTTON, PageTitle, Surface, SurfaceTitle, TEXT_LINK } from './page-surfaces'

const WASTE_SEGMENTS = [
  { key: 'expired', label: 'Expired in storage', color: SERIES.expired },
  { key: 'pre_consumer', label: 'Kitchen (trim + overprep)', color: SERIES.kitchen },
  { key: 'post_consumer', label: 'Plate waste', color: SERIES.plate },
]

export function DashboardPage() {
  const { bundle, hall } = useBundle()
  const today = bundle.meta.as_of
  const tomorrow = addDays(today, 1)
  const team = hall === 'all' ? 'Campus Dining' : hallName(bundle, hall)

  const dTomorrow = dinersOn(bundle, tomorrow, hall)
  const dToday = dinersOn(bundle, today, hall)
  const delta = dToday.forecast ? (dTomorrow.forecast - dToday.forecast) / dToday.forecast : 0
  const lots = inventoryOn(bundle, today, hall)
  const atRisk = lots.filter((l) => l.days_to_expiry <= USE_FIRST_DAYS)
  const atRiskItems = new Set(atRisk.map((l) => `${l.hall_id}|${l.ingredient_id}`)).size
  const recs = recsOn(bundle, today, hall)
  const saved = dedupedSavings(recs)
  const days = dates(bundle)
  const waste = wasteByDay(bundle, hall)

  const seen = new Set<string>()
  const menu = menuOn(bundle, tomorrow, hall)
    .filter((m) => !seen.has(m.name) && seen.add(m.name))
    .slice(0, 5)

  return (
    <>
      <PageTitle
        title={team}
        sub="Today at a glance. Every figure is illustrative, from synthetic data."
        action={
          <Button asChild className={LIME_BUTTON}>
            <Link to="/recommendations">
              Review {recs.length} recommendation{recs.length === 1 ? '' : 's'}
            </Link>
          </Button>
        }
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Figure
          label="Diners tomorrow"
          value={int(dTomorrow.forecast)}
          note={`${delta >= 0 ? 'Up' : 'Down'} ${Math.abs(delta * 100).toFixed(0)}% vs. today`}
          tag={<IllustrativeTag source="caldining_hall_pages" />}
        />
        <Figure
          label="Lots expiring soon"
          value={int(atRiskItems)}
          unit={`of ${int(lots.length)}`}
          note={`Within ${USE_FIRST_DAYS} days`}
          tag={<IllustrativeTag source="fsis_foodkeeper" />}
        />
        <Figure
          label="Avoidable waste today"
          value={lb(saved.lb).replace(' lb', '')}
          unit="lb"
          note={`Across ${recs.length} recommendations`}
          tag={<IllustrativeTag source="leanpath_college_2018" />}
        />
        <Figure
          label="Purchasing savings"
          value={usd(saved.usd)}
          note="If every recommendation is planned"
          tag={<IllustrativeTag source="ingredient_prices" />}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Surface>
          <SurfaceTitle
            title="Food waste this week"
            hint="lb by source. Days after today are projected."
            aside={<IllustrativeTag source="epa_2019_wasted_food" />}
          />
          <StackedBars
            title="Food waste by day"
            segments={WASTE_SEGMENTS}
            splitIndex={days.indexOf(today)}
            rows={waste.map((w) => ({
              label: relDay(w.date, today),
              sub: relDay(w.date, today),
              values: { expired: w.expired, pre_consumer: w.pre_consumer, post_consumer: w.post_consumer },
            }))}
          />
          <div className="mt-3">
            <Legend items={WASTE_SEGMENTS} />
          </div>
        </Surface>

        <Surface>
          <SurfaceTitle title="Tomorrow's menu" />
          <ul className="divide-y divide-border">
            {menu.map((m) => (
              <li key={m.menu_item_id} className="py-3 first:pt-0">
                <p className="truncate text-[15px] font-medium text-foreground">{m.name}</p>
                <p className="mt-0.5 text-[13px] text-muted-foreground capitalize">
                  {m.meal_period}
                  {m.station_role ? ` · ${m.station_role.replaceAll('_', ' ')}` : ''}
                  {hall === 'all' ? ` · ${hallName(bundle, m.hall_id)}` : ''}
                </p>
              </li>
            ))}
            {menu.length === 0 ? <li className="py-3 text-muted-foreground">No menu published for tomorrow.</li> : null}
          </ul>
          <Link to="/meal-planning" className={`${TEXT_LINK} mt-2`}>
            Full menu plan <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </Surface>
      </div>
    </>
  )
}
