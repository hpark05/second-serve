import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { VERIFIED_BY } from '@/data/action-status'
import type { Recommendation, RecommendationKind } from '@/data/bundle'
import { dedupedSavings, hallName, lb, recsOn, relText, usd } from '@/data/bundle-selectors'
import { proposalFor } from '@/data/rec-proposal'
import { useBundle } from '@/data/useBundle'
import { cn } from '@/lib/utils'
import { Chip, IllustrativeTag, Meta, PageTitle, QUIET_BUTTON, Surface, TEXT_LINK } from './page-surfaces'

const KIND_META: Record<
  RecommendationKind,
  { label: string; title: (r: Recommendation) => string; next: { to: string; label: string } }
> = {
  use_first: {
    label: 'Use first',
    title: (r) => `Use ${r.target_name.toLowerCase()} before it expires`,
    next: { to: '/meal-planning', label: 'Menu ideas' },
  },
  adjust_prep: {
    label: 'Adjust prep',
    title: (r) => `Prep less ${r.target_name}`,
    next: { to: '/meal-planning', label: 'Prep plan' },
  },
  buy_less: {
    label: 'Buy less',
    title: (r) => `Order less ${r.target_name.toLowerCase()}`,
    next: { to: '/inventory', label: 'Inventory' },
  },
  transfer: {
    label: 'Transfer',
    title: (r) => `Share ${r.target_name.toLowerCase()} across campus`,
    next: { to: '/campus', label: 'Campus network' },
  },
  recover: {
    label: 'Recover',
    title: (r) => `Flag ${r.target_name.toLowerCase()} for food recovery`,
    next: { to: '/campus', label: 'Recovery pickup' },
  },
}
const ORDER: RecommendationKind[] = ['use_first', 'adjust_prep', 'buy_less', 'transfer', 'recover']

export function RecommendationsPage() {
  const { bundle, hall, statuses, approve, complete } = useBundle()
  const [kind, setKind] = useState<RecommendationKind | 'all'>('all')
  const today = bundle.meta.as_of
  const all = useMemo(
    () =>
      recsOn(bundle, today, hall).sort(
        (a, b) => ORDER.indexOf(a.kind) - ORDER.indexOf(b.kind) || b.est_usd_saved - a.est_usd_saved,
      ),
    [bundle, today, hall],
  )
  const shown = kind === 'all' ? all : all.filter((r) => r.kind === kind)
  const pending = all.filter((r) => !statuses.has(r.id))

  const onPlan = (r: Recommendation) => {
    approve(r.id)
    // Why: a transfer rec and its Campus Network row are the same action; plan both ids.
    if (r.kind === 'transfer' && r.inputs.transfer_id) approve(String(r.inputs.transfer_id))
    toast.success(`Planned: ${KIND_META[r.kind].title(r)}`, {
      description: `${hallName(bundle, r.hall_id)} kitchen notified. Mark it completed once it is done.`,
    })
  }
  const onComplete = (r: Recommendation) => {
    complete(r.id)
    if (r.kind === 'transfer' && r.inputs.transfer_id) complete(String(r.inputs.transfer_id))
  }

  return (
    <div className="max-w-[960px]">
      <PageTitle
        title="Recommendations"
        sub="Proposals for today from inventory, menu and forecast demand. Each needs a chef's review before it is planned."
        action={
          <div className="lg:text-right">
            <p className="tabular font-heading text-[28px] leading-none font-bold text-foreground">
              {usd(dedupedSavings(pending).usd)}
            </p>
            <p className="mt-1 flex items-center lg:justify-end gap-2 text-[13px] text-muted-foreground">
              not yet planned <IllustrativeTag source="ingredient_prices" />
            </p>
          </div>
        }
      />

      <fieldset className="mb-6 flex flex-wrap gap-2">
        <legend className="sr-only">Recommendation type</legend>
        {(['all', ...ORDER] as const).map((k) => {
          const n = k === 'all' ? all.length : all.filter((r) => r.kind === k).length
          if (k !== 'all' && n === 0) return null
          return (
            <button
              key={k}
              type="button"
              aria-pressed={kind === k}
              onClick={() => setKind(k)}
              className={cn(
                'h-11 rounded-full border px-4 text-[14px] transition-colors',
                kind === k
                  ? 'border-foreground bg-foreground text-card'
                  : 'border-border bg-card text-muted-foreground hover:text-foreground',
              )}
            >
              {k === 'all' ? 'All' : KIND_META[k].label} <span className="tabular opacity-70">{n}</span>
            </button>
          )
        })}
      </fieldset>

      <div className="space-y-4">
        {shown.map((r) => {
          const m = KIND_META[r.kind]
          const status = statuses.get(r.id) ?? null
          const p = proposalFor(bundle, r)
          return (
            <Surface key={r.id} as="article">
              <p className="text-[12px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
                {m.label} · {hallName(bundle, r.hall_id)}
              </p>
              <div className="mt-1 flex flex-wrap items-start justify-between gap-2">
                <h2 className="min-w-0 font-heading text-[18px] leading-snug font-semibold text-foreground">
                  {m.title(r)}
                </h2>
                {status === 'planned' ? <Chip tone="planned">Planned</Chip> : null}
                {status === 'completed' ? <Chip tone="completed">Completed (self-reported)</Chip> : null}
              </div>

              <dl className="mt-5 grid gap-x-6 gap-y-4 border-y border-border py-4 sm:grid-cols-2 lg:grid-cols-4">
                <Meta label="Quantity">
                  <span className="tabular">{p.quantity}</span>
                </Meta>
                <Meta label="Intended use">{p.intendedUse}</Meta>
                <Meta label="Needed by">{p.neededBy}</Meta>
                <Meta label="Needs review">
                  <ul className="space-y-1">
                    {p.review.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                </Meta>
              </dl>

              <p className="mt-4 text-[14px] leading-relaxed text-muted-foreground">
                <span className="font-medium text-foreground">Why: </span>
                {relText(r.rationale, today)}
              </p>

              <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
                <span className="tabular text-[14px] text-foreground">
                  Est. {lb(r.est_lb_saved)} saved
                  {r.est_usd_saved > 0 ? ` · ${usd(r.est_usd_saved)}` : ''}
                </span>
                <IllustrativeTag source={r.est_usd_saved > 0 ? 'ingredient_prices' : 'leanpath_college_2018'} />
                <span className="flex-1" />
                <Link to={m.next.to} className={TEXT_LINK}>
                  {m.next.label}
                </Link>
                {status === null ? (
                  <Button className={QUIET_BUTTON} onClick={() => onPlan(r)}>
                    Plan it
                  </Button>
                ) : status === 'planned' ? (
                  <Button className={QUIET_BUTTON} onClick={() => onComplete(r)}>
                    Mark completed
                  </Button>
                ) : null}
              </div>
              {status ? (
                <p className="mt-3 text-[13px] text-muted-foreground">
                  Not yet verified. Verified when the {VERIFIED_BY[r.kind]}.
                </p>
              ) : null}
            </Surface>
          )
        })}
      </div>
      {shown.length === 0 ? <p className="text-muted-foreground">No recommendations for this hall today.</p> : null}
    </div>
  )
}
