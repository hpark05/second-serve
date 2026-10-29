import { ChevronDown } from 'lucide-react'
import { useId, useState } from 'react'
import { cn } from '@/lib/utils'
import { actorTitle } from './labels'
import { weekdayAt, weekdayProse } from './ui/scenario-weekday'
import { useTransfer } from './useScenario'

/** Append-only activity log, collapsed under "History (n)" so it never competes with the step's action. */
export function EventLog({ defaultOpen = false }: { defaultOpen?: boolean }) {
  const { scenario, log } = useTransfer()
  const [open, setOpen] = useState(defaultOpen)
  const id = useId()
  return (
    <section aria-label="History" className="rounded-xl border bg-card">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className="flex min-h-12 w-full items-center justify-between gap-3 rounded-xl px-6 py-3 text-left hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        <span className="text-[16px] font-medium text-ink">
          History <span className="tabular text-muted-foreground">({log.length})</span>
        </span>
        <ChevronDown
          className={cn('size-5 text-muted-foreground transition-transform', open && 'rotate-180')}
          aria-hidden="true"
        />
      </button>
      {open ? (
        <div id={id} className="border-t px-6 pt-2 pb-4">
          <p className="py-2 text-[13px] text-muted-foreground">
            Append-only. Corrections are new entries. Times are scenario time.
          </p>
          <ol className="divide-y">
            {log.map((e) => (
              <li
                key={e.seq}
                className="grid grid-cols-[2.5rem_7.5rem_1fr] gap-x-3 py-3 text-[14px] max-sm:grid-cols-[2.5rem_1fr]"
              >
                <span className="tabular text-muted-foreground">#{e.seq}</span>
                <span className="tabular text-muted-foreground max-sm:hidden">{weekdayAt(scenario, e.at)}</span>
                <div className="min-w-0">
                  <p className="text-[13px] text-muted-foreground">
                    <span className="sm:hidden">{weekdayAt(scenario, e.at)} · </span>
                    {actorTitle(scenario, e.actor)}
                  </p>
                  <p className="text-ink">{weekdayProse(scenario, e.log_line)}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
  )
}
