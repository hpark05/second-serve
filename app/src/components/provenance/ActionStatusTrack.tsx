import { Check, CircleDashed } from 'lucide-react'
import type { ActionStatus } from '@/data/action-status'
import { cn } from '@/lib/utils'

const STEPS: ActionStatus[] = ['planned', 'completed', 'verified']

/**
 * Planned -> Completed -> Verified. Verified is never reached from a click, so it always renders as
 * "Not yet verified" with the evidence that would verify it.
 */
export function ActionStatusTrack({
  status,
  verifiedBy,
  className,
}: {
  status: ActionStatus | null
  verifiedBy: string
  className?: string
}) {
  const reached = status ? STEPS.indexOf(status) : -1
  return (
    <div className={cn('text-xs', className)}>
      <ol className="flex flex-wrap items-center gap-1.5" aria-label="Action status">
        {(['planned', 'completed'] as const).map((s, i) => {
          const on = reached >= i
          return (
            <li
              key={s}
              className={cn(
                'inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-semibold',
                on ? 'bg-green-chip text-green' : 'bg-muted text-muted-foreground',
              )}
            >
              {on ? <Check className="size-3" aria-hidden="true" /> : null}
              {s === 'planned' ? 'Planned' : 'Completed'}
              <span className="sr-only">{on ? ' (done)' : ' (not yet)'}</span>
            </li>
          )
        })}
        <li className="inline-flex items-center gap-1 rounded-full border border-dashed px-2 py-0.5 font-semibold text-muted-foreground">
          <CircleDashed className="size-3" aria-hidden="true" />
          Not yet verified
        </li>
      </ol>
      <p className="mt-1 text-muted-foreground">Verified when: {verifiedBy}.</p>
    </div>
  )
}
