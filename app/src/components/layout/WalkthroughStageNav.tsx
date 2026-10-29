import { NavLink } from 'react-router'
import { cn } from '@/lib/utils'
import { SIMULATED_LABEL, STAGES, VARIANTS } from '@/walkthrough/steps'
import { isSimulated, stepsForStage, type WalkthroughPosition } from './walkthrough-progress'

const stepLink = ({ isActive }: { isActive: boolean }) =>
  cn(
    'flex min-h-11 items-center gap-3 rounded-control px-3 text-label transition-colors',
    isActive ? 'bg-lime-soft font-semibold text-ink' : 'text-muted-foreground hover:bg-muted hover:text-ink',
  )

/**
 * Desktop (>= 1024px) sidebar: the deck's three stages with their steps.
 * Why no caption/progress here: the page's StageHeader owns "Step n of 6" so it never shows twice.
 */
export function StageSidebar({ pos }: { pos: WalkthroughPosition }) {
  return (
    <nav aria-label="Walkthrough stages" className="flex flex-col gap-6">
      <ol className="flex flex-col gap-5">
        {STAGES.map((stage) => {
          const current = pos.stage?.id === stage.id
          return (
            <li key={stage.id} aria-current={current ? 'step' : undefined}>
              <div className={cn('mb-1.5 border-l-2 pl-3', current ? 'border-lime' : 'border-transparent')}>
                <p className={cn('stage-label', current ? 'text-ink' : 'text-muted-foreground')}>
                  {stage.number} {stage.title}
                </p>
                <p className="text-meta text-muted-foreground">{stage.subtitle}</p>
              </div>
              <ul className="flex flex-col gap-0.5">
                {stepsForStage(stage.id).map((s) => (
                  <li key={s.id}>
                    <NavLink to={`/walkthrough/${s.id}`} className={stepLink}>
                      <span className="tabular w-4 flex-none text-center text-meta">{s.id}</span>
                      <span className="min-w-0 flex-1">
                        {s.label}
                        {isSimulated(s) ? (
                          <span className="block text-[12px] font-normal text-muted-foreground">{SIMULATED_LABEL}</span>
                        ) : null}
                      </span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            </li>
          )
        })}
      </ol>
      {VARIANTS.length ? (
        <div>
          <p className="stage-label mb-1.5 px-3 text-muted-foreground">Variants</p>
          <ul className="flex flex-col gap-0.5">
            {VARIANTS.map((s) => (
              <li key={s.id}>
                <NavLink to={`/walkthrough/${s.id}`} className={stepLink}>
                  {s.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </nav>
  )
}

/** Under 1024px: three tappable stage segments only; StageHeader on the page carries "Step n of 6". */
export function StageSegments({ pos }: { pos: WalkthroughPosition }) {
  return (
    <nav aria-label="Walkthrough stages">
      <ol className="grid grid-cols-3 gap-1.5">
        {STAGES.map((stage) => {
          const first = stepsForStage(stage.id)[0]
          const current = pos.stage?.id === stage.id
          return (
            <li key={stage.id}>
              <NavLink
                to={first ? `/walkthrough/${first.id}` : '/walkthrough'}
                aria-current={current ? 'step' : undefined}
                className={cn(
                  'flex min-h-11 flex-col justify-center rounded-control border px-3 py-1.5',
                  current ? 'border-lime bg-lime-soft text-ink' : 'border-border bg-card text-muted-foreground',
                )}
              >
                <span className="stage-label">{stage.number}</span>
                <span className="truncate text-meta font-medium">{stage.title}</span>
              </NavLink>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
