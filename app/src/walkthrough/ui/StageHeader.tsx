import type { WalkthroughStage } from '../steps'

/** "02 Request a transfer · Step 3 of 6", the lime progress bar, and the simulated label for steps 5 and 6. */
export function StageHeader({
  stage,
  stepNumber,
  stepCount,
  simulated,
  simulatedLabel = 'Simulated follow-through',
}: {
  stage: WalkthroughStage
  stepNumber: number
  stepCount: number
  simulated?: boolean
  simulatedLabel?: string
}) {
  const pct = Math.round((stepNumber / stepCount) * 100)
  return (
    <header className="space-y-2">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <p className="text-[12px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
          {stage.number} {stage.title} · Step {stepNumber} of {stepCount}
        </p>
        {simulated ? (
          <span className="rounded-full border border-dashed px-2.5 py-0.5 text-[12px] text-muted-foreground">
            {simulatedLabel}
          </span>
        ) : null}
      </div>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={stepCount}
        aria-valuenow={stepNumber}
        aria-label="Walkthrough progress"
        className="h-1 overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full rounded-full bg-[var(--lime,#7ED957)] transition-[width]" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[14px] text-muted-foreground">{stage.subtitle}</p>
    </header>
  )
}
