import { ArrowRight, Check, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { HBars, Legend, SERIES } from '@/components/charts/charts'
import { Button } from '@/components/ui/button'
import {
  campusNetwork,
  hallName,
  idx,
  ingredientName,
  lb,
  relDay,
  SURPLUS_HORIZON_DAYS,
  sum,
  usd,
} from '@/data/bundle-selectors'
import { useBundle } from '@/data/useBundle'
import { cn } from '@/lib/utils'
import { TransferStage } from '@/walkthrough/TransferStage'
import { weekdayAt, weekdayOf, weekdayProse } from '@/walkthrough/ui/scenario-weekday'
import { useScenarioContext } from '@/walkthrough/useScenario'
import {
  Chip,
  Figure,
  IllustrativeTag,
  LIME_BUTTON,
  Meta,
  PageTitle,
  QUIET_BUTTON,
  Surface,
  SurfaceTitle,
  TEXT_LINK,
} from './page-surfaces'

const SEGMENTS = [
  { key: 'onsite', label: 'Can be used on-site', color: SERIES.onsite },
  { key: 'transfer', label: 'Needs transfer', color: SERIES.transfer },
  { key: 'recover', label: 'Recovery', color: SERIES.recover },
]

/** Calm summary of the fictional spinach transfer; the full interactive stage sits behind a disclosure. */
function SampleTransfer() {
  const { load, seat } = useScenarioContext()
  const [open, setOpen] = useState(false)
  if (load.status !== 'ready') return null
  const s = load.scenario
  const planned = s.lot.allocated.reduce((a, x) => a + x.qty_lb, 0)

  return (
    <Surface className="mb-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <Chip tone="sample">Sample data</Chip>
          <h2 className="mt-3 font-heading text-[18px] leading-snug font-semibold text-foreground">
            {s.kitchens.a.name} has {s.lot.available_lb} lb {s.lot.ingredient_name.toLowerCase()} available
          </h2>
          <p className="mt-1 flex flex-wrap items-center gap-1 text-[14px] text-muted-foreground">
            {s.kitchens.a.name} · {s.kitchens.a.kind} <ArrowRight className="size-4" aria-hidden="true" />{' '}
            {s.kitchens.b.name} · {s.kitchens.b.kind}
          </p>
        </div>
        <Button asChild className={LIME_BUTTON}>
          <Link to="/walkthrough/2">Request transfer</Link>
        </Button>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-4">
        <Meta label="On hand">
          <span className="tabular">{s.lot.on_hand_lb} lb</span>
        </Meta>
        <Meta label="Planned">
          <span className="tabular">{planned} lb</span>
        </Meta>
        <Meta label="Available">
          <span className="tabular font-semibold">{s.lot.available_lb} lb</span>
        </Meta>
        <Meta label="Use by">{weekdayAt(s, s.lot.use_by)}</Meta>
      </dl>
      <p className="mt-3 text-[13px] text-muted-foreground">
        {s.kitchens.b.name} could use it for {s.demand.name}, {s.demand.meal_period} {weekdayOf(s, s.demand.day)}.
        Source: {weekdayProse(s, s.lot.source_label)}.
      </p>

      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className={cn(TEXT_LINK, 'mt-2')}>
        {open ? 'Hide' : 'Show'} transfer details
        <ChevronDown className={cn('size-4 transition-transform', open && 'rotate-180')} aria-hidden="true" />
      </button>
      {open ? (
        <div className="mt-3">
          <TransferStage seat={seat} />
        </div>
      ) : null}
    </Surface>
  )
}

export function CampusPage() {
  const { bundle, hall, approved, approve } = useBundle()
  // Why: a request is not a plan; planned is set only when the receiving kitchen accepts (docs/transfer-flow.md).
  const [requested, setRequested] = useState<ReadonlySet<string>>(() => new Set())
  const today = bundle.meta.as_of
  const rows = campusNetwork(bundle, today)
  const transfers = rows.flatMap((r) => r.outgoing)
  const recover = rows.flatMap((r) => r.recover)
  const surplusLb = sum(rows, (r) => sum(r.surplus, (s) => s.lb))
  const surplusItems = sum(rows, (r) => r.surplus.length)
  const usdPerLb = (id: string) => idx(bundle).ingredient.get(id)?.usd_per_lb ?? 0
  const transferUsd = sum(transfers, (t) => t.qty_lb * usdPerLb(t.ingredient_id))
  const recoverLb = sum(recover, (r) => r.qty)
  const sent = transfers.filter((t) => requested.has(t.transfer_id)).length
  const pickupDone = recover.length > 0 && recover.every((r) => approved.has(r.id))

  const send = (id: string, label: string) => {
    setRequested((prev) => new Set(prev).add(id))
    toast.success('Transfer requested', { description: `${label}. Waiting for the receiving kitchen to accept.` })
  }

  return (
    <>
      <PageTitle
        title="Campus network"
        sub="Surplus and needs across every dining hall, matched before anything expires."
      />

      <SampleTransfer />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Figure
          label="Halls connected"
          value={bundle.halls.length}
          note={bundle.halls.map((h) => h.name).join(' · ')}
        />
        <Figure
          label="Surplus at risk"
          value={lb(surplusLb).replace(' lb', '')}
          unit="lb"
          note={`${surplusItems} items expire within ${SURPLUS_HORIZON_DAYS} days`}
          tag={<IllustrativeTag source="fsis_foodkeeper" />}
        />
        <Figure
          label="Transfers requested"
          value={`${sent}/${transfers.length}`}
          note={`About ${usd(transferUsd)} if all accepted`}
          tag={<IllustrativeTag source="ingredient_prices" />}
        />
        <Figure
          label="Flagged for recovery"
          value={lb(recoverLb).replace(' lb', '')}
          unit="lb"
          note="To approved recovery partners"
          tag={<IllustrativeTag source="refed_mcurc_2024" />}
        />
      </div>

      <Surface className="mb-6">
        <SurfaceTitle title="Dining halls" hint="What each hall can share and what it needs today" />
        <ul className="divide-y divide-border">
          {rows.map((r) => (
            <li key={r.hall.id} className="grid gap-3 py-4 first:pt-0 last:pb-0 lg:grid-cols-[1fr_2fr_1.2fr]">
              <p className="font-medium text-foreground">
                {r.hall.name}
                {hall === r.hall.id ? <span className="font-normal text-muted-foreground"> (you)</span> : null}
              </p>
              <dl>
                <Meta label="Has surplus">
                  <div className="flex flex-wrap gap-1.5">
                    {r.surplus.slice(0, 3).map((s) => (
                      <Chip key={s.ingredient.ingredient_id} tone="expiring">
                        {s.ingredient.name} {s.lb.toFixed(0)} lb · {relDay(s.expiry, today).toLowerCase()}
                      </Chip>
                    ))}
                    {r.surplus.length > 3 ? <Chip>+{r.surplus.length - 3} more</Chip> : null}
                    {r.surplus.length === 0 ? <span className="text-muted-foreground">None</span> : null}
                  </div>
                </Meta>
              </dl>
              <dl>
                <Meta label="Needs">
                  {[...new Set(r.incoming.map((t) => ingredientName(bundle, t.ingredient_id)))].join(', ') || (
                    <span className="text-muted-foreground">None</span>
                  )}
                </Meta>
              </dl>
            </li>
          ))}
        </ul>
      </Surface>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <Surface>
          <SurfaceTitle title="Matched transfers" hint="The receiving kitchen accepts or declines each request" />
          <ul className="divide-y divide-border">
            {transfers.map((t) => {
              const done = requested.has(t.transfer_id)
              const label = `${t.qty_lb.toFixed(1)} lb ${ingredientName(bundle, t.ingredient_id).toLowerCase()} ${hallName(bundle, t.from_hall)} to ${hallName(bundle, t.to_hall)}`
              return (
                <li key={t.transfer_id} className="flex flex-wrap items-center gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px] font-medium text-foreground">
                      {ingredientName(bundle, t.ingredient_id)}{' '}
                      <span className="tabular font-normal text-muted-foreground">· {t.qty_lb.toFixed(1)} lb</span>
                    </p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-1 text-[13px] text-muted-foreground">
                      {hallName(bundle, t.from_hall)} <ArrowRight className="size-3.5" aria-hidden="true" />{' '}
                      {hallName(bundle, t.to_hall)} · use by {relDay(t.expiry_date, today).toLowerCase()}
                    </p>
                  </div>
                  {done ? (
                    <Chip tone="planned">
                      <Check className="size-3.5" aria-hidden="true" /> Requested
                    </Chip>
                  ) : (
                    <Button className={QUIET_BUTTON} onClick={() => send(t.transfer_id, label)}>
                      Request
                    </Button>
                  )}
                </li>
              )
            })}
            {transfers.length === 0 ? <li className="py-2 text-muted-foreground">No matches today.</li> : null}
          </ul>
        </Surface>

        <div className="flex flex-col gap-4">
          <Surface>
            <SurfaceTitle
              title="Expiring surplus by hall"
              hint={`Stock expiring within ${SURPLUS_HORIZON_DAYS} days, plus food flagged for recovery`}
            />
            <HBars
              title="Expiring surplus by hall"
              segments={SEGMENTS}
              rows={rows.map((r) => {
                const total = sum(r.surplus, (s) => s.lb)
                const tx = sum(r.outgoing, (t) => t.qty_lb)
                const rc = sum(r.recover, (x) => x.qty)
                return { label: r.hall.name, values: { onsite: Math.max(0, total - tx), transfer: tx, recover: rc } }
              })}
            />
            <div className="mt-3">
              <Legend items={SEGMENTS} />
            </div>
          </Surface>

          <Surface>
            <SurfaceTitle
              title="Food recovery"
              hint="Surplus no hall can use in time goes to approved partners, under campus food-safety rules."
            />
            <ul className="space-y-1.5 text-[14px] text-foreground">
              {recover.slice(0, 4).map((r) => (
                <li key={r.id}>
                  {r.target_name} · <span className="tabular">{r.qty.toFixed(1)} lb</span>{' '}
                  <span className="text-muted-foreground">
                    ({hallName(bundle, r.hall_id)}
                    {r.inputs.partner ? `, ${r.inputs.partner}` : ''})
                  </span>
                </li>
              ))}
              {recover.length === 0 ? <li className="text-muted-foreground">Nothing flagged today.</li> : null}
            </ul>
            <Button
              className={cn(QUIET_BUTTON, 'mt-4')}
              disabled={recover.length === 0 || pickupDone}
              onClick={() => {
                for (const r of recover) approve(r.id)
                toast.success('Pickup planned', { description: `${lb(recoverLb)} flagged for recovery partners.` })
              }}
            >
              {pickupDone ? 'Pickup planned' : 'Plan pickup'}
            </Button>
          </Surface>
        </div>
      </div>
    </>
  )
}
