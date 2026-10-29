import { ChevronLeft, ChevronRight, Pause, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { SIMULATED_LABEL, STEPS, stageById } from './steps'
import type { PresenterPlayback } from './usePresenterPlayback'

/** Bottom caption bar for the hands-free loop: what the presenter would say, plus pause and step controls. */
export function PresenterCaption({ playback }: { playback: PresenterPlayback }) {
  const { step, index, phase, paused, toggle, go } = playback
  const stage = stageById(step.stage)
  return (
    <div
      // Why: controls handle their own taps; the page-level "tap anywhere pauses" must not swallow them.
      data-presenter-controls=""
      className="fixed inset-x-0 bottom-0 z-20 border-t bg-card shadow-[0_8px_24px_rgba(23,28,23,0.08)]"
    >
      <div className="mx-auto flex max-w-[1100px] items-center gap-4 px-4 py-3 sm:px-7">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">
            {phase === 'end'
              ? 'End of the sample transfer'
              : `${stage ? `${stage.number} ${stage.title} · ` : ''}Step ${step.id} of ${STEPS.length}${step.simulated ? ` · ${SIMULATED_LABEL}` : ''}`}
            {paused ? ' · Paused' : ''}
          </p>
          <p className="mt-0.5 text-[17px] leading-snug sm:text-[19px]" aria-live="polite">
            {phase === 'end' ? 'Three numbers, kept apart, and only the last one counts as saved.' : step.presenterLine}
          </p>
          <ol className="mt-2 flex gap-1.5" aria-label="Progress">
            {STEPS.map((s, i) => (
              <li
                key={s.id}
                className={cn(
                  'h-1.5 flex-1 rounded-full',
                  phase === 'end' || i < index ? 'bg-lime' : i === index ? 'bg-lime/60' : 'bg-border',
                )}
              />
            ))}
          </ol>
        </div>
        <div className="flex flex-none items-center gap-1.5">
          <Button variant="outline" size="icon" className="size-11" onClick={() => go(-1)} aria-label="Previous step">
            <ChevronLeft />
          </Button>
          <Button size="icon" className="size-12" onClick={toggle} aria-label={paused ? 'Play' : 'Pause'}>
            {paused ? <Play /> : <Pause />}
          </Button>
          <Button variant="outline" size="icon" className="size-11" onClick={() => go(1)} aria-label="Next step">
            <ChevronRight />
          </Button>
        </div>
      </div>
    </div>
  )
}
