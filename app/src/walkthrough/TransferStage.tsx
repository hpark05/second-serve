import { Hourglass, Thermometer } from 'lucide-react'
import { useState } from 'react'
import { SampleDataBadge } from '@/components/provenance/IllustrativeChip'
import { StatusChip } from '@/components/StatusChip'
import { Button } from '@/components/ui/button'
import type { ActorRole, DeclineReason, TransferEvent, TransferScenario } from '@/data/scenario'
import { cn } from '@/lib/utils'
import { Fact } from './Fact'
import { actorTitle, DECLINE_REASON_LABEL, DISPOSITION_LABEL, STATE_LABEL, STATE_TONE } from './labels'
import { ACTOR_SEAT, type Seat } from './roles'
import { HandoffCard } from './ui/HandoffCard'
import { PickupCard } from './ui/PickupCard'
import { weekdayAt, weekdayProse } from './ui/scenario-weekday'
import { type NextOption, useScenarioContext, useTransfer } from './useScenario'

const BUTTON: Partial<Record<TransferEvent['type'], string>> = {
  offer_posted: 'Mark as extra',
  request_sent: 'Request transfer',
  request_accepted: 'Accept',
  pickup_scheduled: 'Set pickup',
  handoff_signed: 'Sign handoff',
  receipt_checked: 'Check in',
  use_recorded: 'Record use',
  disposition_noted: 'Save decision',
}

/** What the next person is asked to do, for the handoff prompt. */
const ASK: Partial<Record<TransferEvent['type'], string>> = {
  request_accepted: 'accept or decline the offer',
  request_declined: 'accept or decline the offer',
  pickup_scheduled: 'set the pickup',
  handoff_signed: 'sign the handoff',
  receipt_checked: 'check the spinach in',
  use_recorded: 'record use',
  disposition_noted: 'decide what happens to the food',
}

// Why: 48px primary on walkthrough screens (docs/design-spec.md, Touch).
const BIG = 'h-12 px-5 text-[16px]'

function Card({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <article className={cn('rounded-xl border bg-card p-6', className)}>
      <h3 className="mb-4 text-[18px] leading-snug">{title}</h3>
      {children}
    </article>
  )
}

function roleName(s: TransferScenario, actor: ActorRole) {
  if (actor === 'kitchen_a_cook') return s.kitchens.a.label
  if (actor === 'kitchen_b_chef') return s.kitchens.b.label
  return 'the coordinator'
}

/** Labelled fields of one event, so every number on the card carries its meaning. */
function EventFacts({ e }: { e: TransferEvent }) {
  const { scenario } = useTransfer()
  const f = e.fields
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
      {f.qty_lb !== undefined ? (
        <Fact label={e.type === 'handoff_signed' || e.type === 'receipt_checked' ? 'Weighed qty' : 'Qty'}>
          {f.qty_lb} lb
        </Fact>
      ) : null}
      {f.intended_use ? (
        <Fact label="For menu item">
          <a
            href={f.intended_use.source_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-11 items-center text-green hover:underline"
          >
            {f.intended_use.name}
          </a>
          <span className="block text-[13px] text-muted-foreground">
            {f.intended_use.station} · {f.intended_use.meal_period} · real Cal Dining menu row
          </span>
        </Fact>
      ) : null}
      {f.needed_by ? <Fact label="Needed by">{weekdayAt(scenario, f.needed_by)}</Fact> : null}
      {f.offer_until ? <Fact label="Offer open until">{weekdayAt(scenario, f.offer_until)}</Fact> : null}
      {f.temperature_f !== undefined ? (
        <Fact label={`Temperature at ${f.temperature_point?.replace('_', '-') ?? 'reading'}`}>
          {f.temperature_f}°F
          {f.temperature_point === 'receipt' ? (
            <span className="block text-[13px] text-green">
              At or under the {scenario.temperature_constraint.receive_reject_above_f}°F receiving limit
            </span>
          ) : null}
        </Fact>
      ) : null}
      {f.signed_by ? <Fact label="Signed by">{f.signed_by.length} signatures: cook and runner</Fact> : null}
      {f.decline_reason ? <Fact label="Reason">{DECLINE_REASON_LABEL[f.decline_reason]}</Fact> : null}
      {f.disposition ? <Fact label="Disposition">{DISPOSITION_LABEL[f.disposition]}</Fact> : null}
      {f.storage_constraint ? (
        <div className="col-span-2">
          <Fact label="Storage constraint">{f.storage_constraint}</Fact>
        </div>
      ) : null}
      {f.note ? (
        <div className="col-span-2">
          <Fact label="Note">{f.note}</Fact>
        </div>
      ) : null}
    </dl>
  )
}

function declineEvent(
  template: TransferEvent,
  request: TransferEvent | undefined,
  reason: DeclineReason,
  note: string,
): TransferEvent {
  const qty = request?.fields.qty_lb ?? template.fields.qty_lb
  const fixture = template.fields.decline_reason === reason && !note
  if (fixture && request && template.seq === request.seq + 1) return template
  const text = note || DECLINE_REASON_LABEL[reason]
  return {
    ...template,
    fields: { decline_reason: reason, note: note || undefined },
    log_line: `Café 3 chef said no: ${text.toLowerCase()}. The ${qty ?? ''} lb stays marked extra.`.replace('  ', ' '),
  }
}

/** Accept, or decline with a required reason. Decline stays disabled until a reason is picked. */
function Decide({ options }: { options: NextOption[] }) {
  const { scenario, applied } = useTransfer()
  const { apply } = useScenarioContext()
  const accept = options.find((o) => o.event.type === 'request_accepted')
  const fixtureDecline = options.find((o) => o.event.type === 'request_declined')
  const template =
    fixtureDecline?.event ?? scenario.paths.flatMap((p) => p.events).find((e) => e.type === 'request_declined')
  const [declining, setDeclining] = useState(false)
  const [reason, setReason] = useState<DeclineReason | null>(null)
  const [note, setNote] = useState('')
  const request = [...applied].reverse().find((e) => e.type === 'request_sent')
  const ready = reason !== null && (reason !== 'other' || note.trim().length > 0)

  if (!declining || !template)
    return (
      <div className="mt-6 flex flex-wrap gap-3">
        <Button className={BIG} disabled={!accept} onClick={() => accept && apply(accept.pathId, accept.event)}>
          Accept {request?.fields.qty_lb !== undefined ? `${request.fields.qty_lb} lb` : ''}
        </Button>
        {template ? (
          <Button variant="outline" className={BIG} onClick={() => setDeclining(true)}>
            Decline
          </Button>
        ) : null}
      </div>
    )

  return (
    <form
      className="mt-6 space-y-4 border-t pt-5"
      onSubmit={(ev) => {
        ev.preventDefault()
        if (!ready || !reason) return
        apply(
          fixtureDecline?.pathId ?? 'decline',
          declineEvent(template, request, reason, reason === 'other' ? note.trim() : ''),
        )
      }}
    >
      <fieldset>
        <legend className="mb-3 text-[14px] font-medium text-ink">Why not? Pick a reason to decline.</legend>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(DECLINE_REASON_LABEL) as DeclineReason[]).map((r) => (
            <label
              key={r}
              className={cn(
                'inline-flex min-h-11 cursor-pointer items-center rounded-full border px-4 text-[14px] transition-colors has-focus-visible:ring-3 has-focus-visible:ring-ring/50',
                reason === r ? 'border-ink bg-ink text-white' : 'bg-card text-ink hover:bg-muted',
              )}
            >
              <input
                type="radio"
                name="reason"
                value={r}
                checked={reason === r}
                onChange={() => setReason(r)}
                className="sr-only"
              />
              {DECLINE_REASON_LABEL[r]}
            </label>
          ))}
        </div>
      </fieldset>
      {reason === 'other' ? (
        <label className="block">
          <span className="mb-1.5 block text-[14px] text-muted-foreground">Say why</span>
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="h-12 w-full rounded-lg border bg-card px-3 text-[16px]"
          />
        </label>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <Button type="submit" variant="destructive" className={BIG} disabled={!ready}>
          Decline
        </Button>
        <Button
          type="button"
          variant="ghost"
          className={BIG}
          onClick={() => {
            setDeclining(false)
            setReason(null)
          }}
        >
          Cancel
        </Button>
      </div>
    </form>
  )
}

/** Kitchen A's transfer offer: Second Serve suggests Kitchen B from a real menu item that uses the food. */
function OfferForm({ option }: { option: NextOption }) {
  const { scenario } = useTransfer()
  const { apply } = useScenarioContext()
  const tc = scenario.temperature_constraint
  return (
    <div className="space-y-5">
      <p className="text-[16px]">
        Suggested: <b>{scenario.kitchens.b.name}</b>, because a dish on its menu uses{' '}
        {scenario.lot.ingredient_name.toLowerCase()}.
      </p>
      <EventFacts e={option.event} />
      <p className="flex items-start gap-2 text-[14px] text-muted-foreground">
        <Thermometer className="mt-0.5 size-4 flex-none" aria-hidden="true" />
        <span>
          <b className="font-medium text-ink">{tc.hold_max_f}°F or colder.</b> {tc.plain_language}
        </span>
      </p>
      <Button className={BIG} onClick={() => apply(option.pathId, option.event)}>
        Request transfer
      </Button>
    </div>
  )
}

function NextAction({ seat }: { seat: Seat }) {
  const t = useTransfer()
  const { apply } = useScenarioContext()
  const mine = t.forSeat(seat)
  if (!mine.length) return null
  const o = mine[0]
  const type = o.event.type
  if (type === 'request_sent')
    return (
      <Card title={`Send ${t.scenario.kitchens.b.name} a transfer offer`}>
        <OfferForm option={o} />
      </Card>
    )
  if (type === 'request_accepted' || type === 'request_declined') {
    const request = [...t.applied].reverse().find((e) => e.type === 'request_sent')
    return (
      <Card title={`${t.scenario.kitchens.a.name} offers you ${t.scenario.lot.ingredient_name.toLowerCase()}`}>
        <p className="mb-5 text-[16px] text-muted-foreground">Review the quantity and timing.</p>
        {request ? <EventFacts e={request} /> : null}
        <Decide options={mine} />
      </Card>
    )
  }
  if (type === 'pickup_scheduled' && o.event.fields.pickup)
    return (
      <Card title="Set the pickup">
        <PickupCard pickup={o.event.fields.pickup} />
        <p className="mt-4 text-[13px] text-muted-foreground">
          The coordinator schedules only. No accept, decline or verify here.
        </p>
        <Button className={cn(BIG, 'mt-5')} onClick={() => apply(o.pathId, o.event)}>
          Set pickup
        </Button>
      </Card>
    )
  const title = type === 'disposition_noted' ? 'Decide what happens to the food' : (BUTTON[type] ?? type)
  return (
    <Card title={title}>
      <EventFacts e={o.event} />
      <Button className={cn(BIG, 'mt-6')} onClick={() => apply(o.pathId, o.event)}>
        {BUTTON[type] ?? type}
        {type === 'offer_posted' && o.event.fields.qty_lb !== undefined ? ` ${o.event.fields.qty_lb} lb` : ''}
      </Button>
    </Card>
  )
}

/** Presenter-only clock control: lets the offer window pass with no request (the expired path). */
export function ClockControl() {
  const t = useTransfer()
  const { apply } = useScenarioContext()
  if (!t.systemOptions.length || t.state !== 'requested') return null
  const run = () => {
    // Why: the expired path's system events (next import, offer lapse) happen together when time passes.
    const first = t.systemOptions[0]
    const path = t.scenario.paths.find((p) => p.id === first.pathId)
    const rest = path?.events.slice(path.events.indexOf(first.event) + 1) ?? []
    apply(first.pathId, first.event)
    for (const e of rest) {
      if (e.actor !== 'system') break
      apply(first.pathId, e)
    }
  }
  return (
    <button
      type="button"
      onClick={run}
      className="inline-flex min-h-11 items-center gap-2 rounded-full border border-dashed px-4 text-[14px] text-muted-foreground hover:bg-muted"
    >
      <Hourglass className="size-4" aria-hidden="true" /> What if {t.scenario.kitchens.b.name} never answers? Let the
      offer window close
    </button>
  )
}

function Notice({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border bg-card p-6">
      <p className="font-heading text-[18px] font-semibold text-ink">{title}</p>
      <p className="mt-1.5 text-[16px] text-muted-foreground">{children}</p>
    </div>
  )
}

/** Everything the current seat sees about the sample transfer: status, its next action, or who to hand to. */
export function TransferStage({ seat }: { seat: Seat }) {
  const t = useTransfer()
  const { handoffTo } = useScenarioContext()
  const mine = t.forSeat(seat)
  // Why: t.handoff is the engine's single rule for when to pass the iPad; the presenter loop follows it too.
  const waitingSeat = t.handoff?.to
  const waitingOn = waitingSeat ? t.options.find((o) => ACTOR_SEAT[o.event.actor] === waitingSeat) : undefined
  // Why: when this seat has a next step, its action card already shows the latest entry's facts.
  const latest = !mine.length && t.last && t.last.type !== 'inventory_imported' ? t.last : null
  const { a, b } = t.scenario.kitchens
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {/* Why: both chips share h-6 and 11.5px type so they sit on one baseline. */}
        <StatusChip tone={t.state ? STATE_TONE[t.state] : 'muted'} className="h-6 py-0">
          {t.state ? STATE_LABEL[t.state] : 'Not offered yet'}
        </StatusChip>
        <span className="text-[14px] text-muted-foreground">
          {a.name} to {b.name}
        </span>
        <SampleDataBadge className="h-6 px-2.5 py-0 text-[11.5px]" />
      </div>

      {t.state === 'expired' ? (
        <Notice title="Offer closed">
          Nothing was thrown out. The {t.scenario.lot.ingredient_name.toLowerCase()} stays at {a.name}, and the cook
          decides what happens next. No pounds are counted.
        </Notice>
      ) : null}
      {t.state === 'declined' ? (
        <Notice title="Declined">
          The {t.scenario.lot.available_lb} lb stays marked extra, so {a.name} can offer it to another kitchen. Nothing
          was planned, so nothing is counted.
        </Notice>
      ) : null}

      <NextAction seat={seat} />

      {waitingOn && waitingSeat ? (
        <HandoffCard
          to={roleName(t.scenario, waitingOn.event.actor)}
          waitingFor={`${actorTitle(t.scenario, waitingOn.event.actor)}, to ${ASK[waitingOn.event.type] ?? 'take the next step'}`}
          onHandoff={() => handoffTo(waitingSeat)}
        />
      ) : null}

      {latest ? (
        <Card title={weekdayProse(t.scenario, latest.log_line.split('. ')[0].replace(/\.$/, ''))}>
          <p className="-mt-2 mb-4 text-[13px] text-muted-foreground">
            {weekdayAt(t.scenario, latest.at)} · {actorTitle(t.scenario, latest.actor)}
          </p>
          {latest.fields.pickup ? <PickupCard pickup={latest.fields.pickup} /> : <EventFacts e={latest} />}
        </Card>
      ) : null}
    </div>
  )
}
