import { Loader2 } from 'lucide-react'
import { useEffect } from 'react'
import { useSearchParams } from 'react-router'
import { EventLog } from './EventLog'
import { PresenterCaption } from './PresenterCaption'
import { RolePill } from './RoleSwitcher'
import { SIMULATED_LABEL, stageById } from './steps'
import { TierCounters } from './TierCounters'
import { TransferStage } from './TransferStage'
import { StepHero } from './ui/StepHero'
import { weekdayAt } from './ui/scenario-weekday'
import { END_CARD_MS, type PresenterPlayback, usePresenterPlayback } from './usePresenterPlayback'
import { useScenarioContext, useTransfer } from './useScenario'
import { VerificationChecks } from './VerificationChecks'

/** `/present`: the hands-free laptop loop. No app chrome; same scenario state the iPad walkthrough uses. */
export function PresenterPage() {
  const { load } = useScenarioContext()
  if (load.status === 'loading')
    return (
      <p className="inline-flex items-center gap-2 p-7 text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Loading the sample scenario…
      </p>
    )
  if (load.status === 'error') return <p className="p-7 text-red">Couldn't load the sample scenario. {load.error}</p>
  return <Presenter />
}

function Presenter() {
  const [params] = useSearchParams()
  // Why: tests run the full loop several times; ?speed=20 compresses every delay without a separate code path.
  const speed = Math.max(1, Number(params.get('speed')) || 1)
  const playback = usePresenterPlayback({ speed })
  const { seat } = useScenarioContext()
  const t = useTransfer()
  const { step, phase, pause, toggle, go } = playback
  const stage = stageById(step.stage)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key === ' ') {
        e.preventDefault()
        toggle()
      } else if (e.key === 'ArrowRight') go(1)
      else if (e.key === 'ArrowLeft') go(-1)
      else pause()
    }
    const onPointer = (e: PointerEvent) => {
      if (!(e.target as Element | null)?.closest('[data-presenter-controls]')) pause()
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('pointerdown', onPointer)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('pointerdown', onPointer)
    }
  }, [toggle, go, pause])

  return (
    <div
      className="min-h-dvh bg-bg pb-40"
      data-presenter=""
      data-loop={playback.loop}
      data-step={step.id}
      data-phase={phase}
      data-paused={playback.paused}
      data-event-seqs={t.log.map((e) => e.seq).join(',')}
    >
      <div className="mx-auto max-w-[960px] space-y-4 px-4 pt-6 sm:px-7">
        {/* Why: the caption bar owns "Stage · Step n of 6" on /present, so the page keeps only the subtitle. */}
        {stage ? (
          <p className="flex flex-wrap items-center gap-2 text-[14px] text-muted-foreground">
            {stage.subtitle}
            {step.simulated ? (
              <span className="rounded-full border border-dashed px-2.5 py-0.5 text-[12px]">{SIMULATED_LABEL}</span>
            ) : null}
          </p>
        ) : null}
        {step.runsImports ? (
          <h1 className="text-[32px] leading-tight">System, next morning</h1>
        ) : (
          <RolePill seat={seat} scenario={t.scenario} />
        )}
        <p className="text-[13px] text-muted-foreground">
          {t.scenario.banner_label} · Scenario clock: {t.last ? weekdayAt(t.scenario, t.last.at) : 'start'}
        </p>
        {step.id === '1' ? <StepHero /> : null}
        <TransferStage seat={seat} />
        <TierCounters />
        {t.completed.length > 0 || step.runsImports ? <VerificationChecks /> : null}
        <EventLog />
      </div>
      {phase === 'end' ? <EndCard playback={playback} /> : null}
      <PresenterCaption playback={playback} />
    </div>
  )
}

function EndCard({ playback }: { playback: PresenterPlayback }) {
  return (
    <div className="fixed inset-0 z-10 grid place-items-center bg-bg/95 px-6">
      <div className="max-w-[640px] rounded-xl border bg-card p-8 text-center shadow-[0_8px_24px_rgba(23,28,23,0.08)]">
        <p className="text-xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">Second Serve</p>
        <h2 className="mt-2 text-[28px] leading-tight">Planned, reported, verified. Kept apart.</h2>
        <p className="mt-3 text-muted-foreground">
          Only the verified number counts as saved. Try the workflow on the iPad and tell us what is missing.
        </p>
        <p className="mt-4 text-[13px] text-muted-foreground">
          {playback.paused ? 'Paused. Press space to play.' : `Starting again in ${END_CARD_MS / 1000} seconds.`}
        </p>
      </div>
    </div>
  )
}
