import { CircleCheck, CircleDashed } from 'lucide-react'
import { cn } from '@/lib/utils'
import { SIMULATED_IMPORT_LABEL } from './steps'
import { useTransfer } from './useScenario'

interface Tile {
  key: 'planned' | 'completed' | 'verified'
  label: string
  qualifier?: string
  lb: number
  setBy: string
  status?: React.ReactNode
  done: boolean
}

/**
 * Planned, Completed (self-reported) and Verified as three separate tiles. Never added together: each is a
 * different claim about the same pounds (docs/transfer-flow.md, "Planned, completed, verified").
 */
export function TierCounters() {
  const { planned, completed, verified, imports } = useTransfer()
  const reported = completed.length ? Math.max(...completed.map((c) => c.qty_lb)) : 0
  const isVerified = verified?.status === 'verified'
  const tiles: Tile[] = [
    {
      key: 'planned',
      label: 'Planned',
      lb: planned?.qty_lb ?? 0,
      setBy: 'Set when Kitchen B accepts',
      done: Boolean(planned),
    },
    {
      key: 'completed',
      label: 'Completed',
      qualifier: 'self-reported',
      lb: reported,
      setBy: 'Set by the handoff and use people record',
      done: completed.length > 0,
    },
    {
      key: 'verified',
      label: 'Verified',
      lb: isVerified ? (verified?.qty_lb ?? 0) : 0,
      setBy: 'Set only by the next Eatec export',
      done: isVerified,
      status: isVerified ? (
        <span className="inline-flex items-start gap-1.5 text-green">
          <CircleCheck className="mt-0.5 size-4 flex-none" aria-hidden="true" />
          <span>Verified · {SIMULATED_IMPORT_LABEL}</span>
        </span>
      ) : verified?.status === 'mismatch' ? (
        <span className="text-red">Records disagree · coordinator reviews</span>
      ) : (
        <span className="inline-flex items-start gap-1.5">
          <CircleDashed className="mt-0.5 size-4 flex-none" aria-hidden="true" />
          <span>{imports.length ? 'Checking Eatec records…' : 'Not yet verified · set by next Eatec export'}</span>
        </span>
      ),
    },
  ]
  return (
    <section aria-label="Planned, completed and verified pounds" className="space-y-3">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {tiles.map((t) => (
          <div
            key={t.key}
            className={cn(
              'flex min-w-0 flex-col rounded-xl border bg-card p-5',
              t.key === 'verified' && t.done && 'border-green bg-green-soft',
            )}
          >
            <div className="text-[12px] whitespace-nowrap text-muted-foreground">
              <span className="font-semibold tracking-[0.08em] uppercase">{t.label}</span>
              {t.qualifier ? <span> ({t.qualifier})</span> : null}
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span
                className={cn(
                  'font-heading tabular text-[40px] leading-none font-bold',
                  t.done ? 'text-ink' : 'text-muted-foreground/60',
                )}
              >
                {t.lb}
              </span>
              <span className="text-[14px] text-muted-foreground">lb</span>
            </div>
            <p className="mt-3 text-[13px] leading-snug text-muted-foreground">{t.status ?? t.setBy}</p>
          </div>
        ))}
      </div>
      <p className="text-[13px] text-muted-foreground">
        Three separate claims about the same food. Never added together. Only Verified counts as saved.
      </p>
    </section>
  )
}
