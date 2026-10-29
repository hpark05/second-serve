import { SampleDataBadge } from '@/components/provenance/IllustrativeChip'
import { useTransfer } from '../useScenario'
import { weekdayAt, weekdayOf } from './scenario-weekday'

function Figure({ value, unit, label, accent }: { value: number; unit: string; label: string; accent?: boolean }) {
  return (
    <div className="min-w-0">
      <div className="flex items-baseline gap-1.5">
        <span
          className={`font-heading tabular text-[44px] leading-none font-bold sm:text-[52px] ${accent ? 'text-green' : 'text-ink'}`}
        >
          {value}
        </span>
        <span className="text-[14px] text-muted-foreground">{unit}</span>
      </div>
      <p className="mt-2 text-[14px] text-muted-foreground">{label}</p>
    </div>
  )
}

/** The scenario's three numbers, big, straight from the fixture lot. */
export function StepHero() {
  const { scenario } = useTransfer()
  const { lot } = scenario
  const planned = lot.allocated.reduce((n, a) => n + a.qty_lb, 0)
  const plannedDay = lot.allocated[0] ? weekdayOf(scenario, lot.allocated[0].menu_item.day) : null
  return (
    <section
      aria-label={`${lot.ingredient_name} at ${scenario.kitchens.a.name}`}
      className="rounded-xl border bg-card p-6"
    >
      <p className="mb-4 text-[12px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
        {lot.ingredient_name} · {scenario.kitchens.a.label} · {scenario.kitchens.a.name}
      </p>
      <div className="grid grid-cols-3 gap-4">
        <Figure value={lot.on_hand_lb} unit="lb" label="on hand" />
        <Figure value={planned} unit="lb" label={plannedDay ? `planned ${plannedDay}` : 'planned'} />
        <Figure
          value={lot.available_lb}
          unit="lb"
          label={`available, best by ${weekdayOf(scenario, lot.use_by.day)}`}
          accent
        />
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-2 border-t pt-4 text-[13px] text-muted-foreground">
        <span>
          {lot.source_system} export · {weekdayAt(scenario, lot.exported_at)}
        </span>
        <SampleDataBadge />
      </div>
    </section>
  )
}
