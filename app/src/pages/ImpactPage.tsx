import { Download, Printer } from 'lucide-react'
import { useEffect, useState } from 'react'
import { TrendLine } from '@/components/charts/charts'
import { Button } from '@/components/ui/button'
import { SCENARIO_LABELS } from '@/data/bundle'
import {
  avoidedByDay,
  dedupedSavings,
  hallName,
  int,
  lb,
  relDay,
  usd,
  wasteByDay,
  weekSavings,
} from '@/data/bundle-selectors'
import { useBundle } from '@/data/useBundle'
import { Figure, IllustrativeTag, LIME_BUTTON, PageTitle, QUIET_BUTTON, Surface, SurfaceTitle } from './page-surfaces'

type Range = { low: number; mid: number; high: number }

/** The generator's deduplicated savings range from summary.json. It is campus-wide, so only for "All dining halls". */
function useSavingsRange(scenario: string, campusWide: boolean): Range | null {
  const [range, setRange] = useState<Range | null>(null)
  useEffect(() => {
    setRange(null)
    if (!campusWide) return
    let live = true
    fetch(`${import.meta.env.BASE_URL}data/${scenario}/summary.json`)
      .then((r) => (r.ok && r.headers.get('content-type')?.includes('json') ? r.json() : null))
      .then((j) => live && setRange(j?.costs?.recommendations_est_usd_saved?.deduplicated ?? null))
      .catch(() => {})
    return () => {
      live = false
    }
  }, [scenario, campusWide])
  return range
}

function downloadCsv(name: string, rows: (string | number)[][]) {
  const csv = rows
    .map((r) => r.map((c) => (/[",\n]/.test(String(c)) ? `"${String(c).replaceAll('"', '""')}"` : c)).join(','))
    .join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: name })
  a.click()
  URL.revokeObjectURL(url)
}

export function ImpactPage() {
  const { bundle, hall, approved, scenario, isFixture } = useBundle()
  const f = bundle.meta.factors
  const recs = bundle.recommendations.filter((r) => hall === 'all' || r.hall_id === hall)
  // Why: summing every rec double-counts stock several kinds target; use the generator's dedupe.
  const week = weekSavings(bundle, hall)
  const range = useSavingsRange(bundle.meta.scenario, hall === 'all')
  const lbAvoided = week.lb
  const usdSaved = week.usd
  const approvedRecs = recs.filter((r) => approved.has(r.id))
  const approvedLb = dedupedSavings(approvedRecs).lb
  const waste = wasteByDay(bundle, hall)
  const avoided = avoidedByDay(bundle, hall)
  const scope = hall === 'all' ? 'All dining halls' : hallName(bundle, hall)
  const scenarioLabel = isFixture ? 'Fixture' : SCENARIO_LABELS[scenario]
  const period = `${relDay(bundle.meta.start_date, bundle.meta.as_of)} to ${relDay(bundle.meta.end_date, bundle.meta.as_of)}`

  const exportCsv = () =>
    downloadCsv(`second-serve-impact-${bundle.meta.scenario}-${hall}.csv`, [
      ['Second Serve impact summary'],
      ['Scope', scope],
      ['Scenario', scenarioLabel],
      ['Period', `${bundle.meta.start_date} to ${bundle.meta.end_date}`],
      ['Data source', bundle.meta.source],
      [],
      ['Metric', 'Value', 'Unit'],
      ['Food waste avoidable', lbAvoided.toFixed(1), 'lb'],
      ['Purchasing savings', usdSaved.toFixed(2), 'USD'],
      ['CO2e reduced', (lbAvoided * f.co2e_lb_per_lb).toFixed(1), 'lb'],
      ['Meals supported', Math.round(lbAvoided / f.lb_per_meal), 'meals'],
      ['Approved this session', approvedLb.toFixed(1), 'lb'],
      [],
      ['Date', 'Expired lb', 'Kitchen lb', 'Plate lb', 'Total waste lb', 'Avoidable lb', 'Avoidable USD'],
      ...waste.map((w, i) => [
        w.date,
        w.expired.toFixed(1),
        w.pre_consumer.toFixed(1),
        w.post_consumer.toFixed(1),
        w.total.toFixed(1),
        avoided[i].lb.toFixed(1),
        avoided[i].usd.toFixed(2),
      ]),
      [],
      ['Factors', `lb_per_meal=${f.lb_per_meal}`, `co2e_lb_per_lb=${f.co2e_lb_per_lb}`],
    ])

  const num = (s: string) => s.replace(' lb', '')

  return (
    <div className="max-w-[960px]">
      <PageTitle
        title="Impact"
        sub={`${scope} · ${scenarioLabel} · ${period}. Every figure is illustrative, from synthetic data.`}
        action={
          <>
            <Button className={`${QUIET_BUTTON} no-print`} onClick={() => window.print()}>
              <Printer aria-hidden="true" /> Print
            </Button>
            <Button className={`${LIME_BUTTON} no-print`} onClick={exportCsv}>
              <Download aria-hidden="true" /> Export summary
            </Button>
          </>
        }
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        <Figure
          label="Food waste avoidable"
          value={num(lb(lbAvoided))}
          unit="lb"
          note="If every recommendation is planned and completed"
          tag={<IllustrativeTag source="leanpath_college_2018" />}
        />
        <Figure
          label="Purchasing savings"
          value={usd(usdSaved)}
          note={`${range ? `Range ${usd(range.low)} to ${usd(range.high)}. ` : ''}Wholesale ingredient prices.`}
          tag={<IllustrativeTag source="ingredient_prices" />}
        />
        <Figure
          label="CO₂e reduced"
          value={num(lb(lbAvoided * f.co2e_lb_per_lb))}
          unit="lb"
          note={`${f.co2e_lb_per_lb.toFixed(2)} lb CO₂e per lb of food`}
          tag={<IllustrativeTag source="co2e_lb_per_lb" />}
        />
        <Figure
          label="Meals supported"
          value={int(lbAvoided / f.lb_per_meal)}
          unit="meals"
          note={`At ${f.lb_per_meal} lb per meal`}
          tag={<IllustrativeTag source="lb_per_meal" />}
        />
      </div>

      <Surface>
        <SurfaceTitle
          title="Food waste trend"
          hint="Synthetic total lb per day, all sources"
          aside={<IllustrativeTag source="epa_2019_wasted_food" />}
        />
        <TrendLine
          title="Food waste per day"
          points={waste.map((w) => ({
            label: relDay(w.date, bundle.meta.as_of),
            sub: relDay(w.date, bundle.meta.as_of),
            value: w.total,
          }))}
        />
      </Surface>

      {approvedRecs.length ? (
        <Surface className="mt-4 flex flex-wrap items-center gap-2 text-[14px]">
          <span>
            {approvedRecs.length} recommendation{approvedRecs.length === 1 ? '' : 's'} planned this session, about{' '}
            <span className="tabular font-semibold">{lb(approvedLb)}</span>. Not yet verified.
          </span>
          <IllustrativeTag source="leanpath_college_2018" />
        </Surface>
      ) : null}
    </div>
  )
}
