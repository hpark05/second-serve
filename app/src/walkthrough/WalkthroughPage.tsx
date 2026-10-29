import { Loader2, RotateCcw } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/button'
import { useBundle } from '@/data/useBundle'
import { EventLog } from './EventLog'
import { RolePill } from './RoleSwitcher'
import { seatHall } from './roles'
import { SIMULATED_LABEL, STEPS, stageById, stepById } from './steps'
import { TierCounters } from './TierCounters'
import { ClockControl, TransferStage } from './TransferStage'
import { ActionBar } from './ui/ActionBar'
import { StageHeader } from './ui/StageHeader'
import { StepHero } from './ui/StepHero'
import { weekdayAt } from './ui/scenario-weekday'
import { isStepComplete, resumeStep, stepEntry, useScenarioContext, useTransfer } from './useScenario'
import { VerificationChecks } from './VerificationChecks'

export function WalkthroughPage() {
  const { load } = useScenarioContext()
  const [params] = useSearchParams()
  if (params.get('autoplay') === '1') return <Navigate to="/present" replace />
  if (load.status === 'loading')
    return (
      <p className="inline-flex items-center gap-2 text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Loading the sample scenario…
      </p>
    )
  if (load.status === 'error') return <p className="text-red">Couldn't load the sample scenario. {load.error}</p>
  return <Walkthrough />
}

function Walkthrough() {
  const { step: stepId } = useParams()
  const step = stepById(stepId)
  const navigate = useNavigate()
  const { seat, runId, rewind, importRecords, restart } = useScenarioContext()
  const { setHall } = useBundle()
  const t = useTransfer()
  const opened = useRef<string | null>(null)

  // Why: participants only move through events they applied; opening a step may rewind (Back) but never seeks forward.
  useEffect(() => {
    if (!step) return
    const key = `${runId}:${step.id}`
    if (opened.current === key) return
    opened.current = key
    const entry = stepEntry(step, t)
    if (!entry) {
      navigate(`/walkthrough/${resumeStep(t).id}`, { replace: true })
      return
    }
    if (entry.pathId !== t.path.id || entry.count !== t.applied.length) rewind(entry.pathId, entry.count)
  }, [step, runId, t, rewind, navigate])

  useEffect(() => {
    setHall(seatHall(seat, t.scenario.kitchens.a.hall_id, t.scenario.kitchens.b.hall_id))
  }, [seat, t.scenario, setHall])

  // Step 6 is the next morning: the system reads the Eatec exports. No person triggers this.
  useEffect(() => {
    if (!step?.runsImports || t.path.id !== 'happy' || t.state !== 'used' || t.imports.length) return
    const id = setTimeout(importRecords, 900)
    return () => clearTimeout(id)
  }, [step, t.path.id, t.state, t.imports.length, importRecords])

  if (!step) return <Navigate to="/walkthrough/1" replace />
  const i = STEPS.findIndex((s) => s.id === step.id)
  const prev = i > 0 ? STEPS[i - 1] : null
  const next = i >= 0 && i < STEPS.length - 1 ? STEPS[i + 1] : null
  const complete = isStepComplete(step, t)
  const stage = stageById(step.stage)
  const showChecks = t.completed.length > 0 || step.runsImports
  const onRestart = () => {
    restart()
    navigate('/walkthrough/1')
  }
  const hint = complete
    ? undefined
    : t.path.id === step.path
      ? 'Finish the step above to continue.'
      : 'This branch ends here. Restart to try again.'

  return (
    <div className="mx-auto max-w-[960px] space-y-4">
      {stage ? (
        <StageHeader
          stage={stage}
          // Why: variants replace Kitchen B's review, so they sit at that step's position.
          stepNumber={i >= 0 ? i + 1 : step.from}
          stepCount={STEPS.length}
          simulated={step.simulated}
          simulatedLabel={SIMULATED_LABEL}
        />
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-2">
        {step.runsImports ? (
          <h1 className="text-[28px] leading-tight">System, next morning</h1>
        ) : (
          <RolePill seat={seat} scenario={t.scenario} />
        )}
        <Button variant="ghost" className="h-11" onClick={onRestart}>
          <RotateCcw /> Restart sample
        </Button>
      </div>
      {/* Why: the header already carries banner_label; audienceSees is presenter-facing copy, so only the clock goes here. */}
      <p className="text-[13px] text-muted-foreground">
        Scenario clock: {t.last ? weekdayAt(t.scenario, t.last.at) : 'start'}
      </p>

      {step.id === '1' ? <StepHero /> : null}
      <TransferStage seat={seat} />
      <ClockControl />
      <TierCounters />
      {showChecks ? <VerificationChecks /> : null}
      <EventLog />

      <ActionBar
        back={prev ? { label: `Step ${prev.id}`, to: `/walkthrough/${prev.id}` } : undefined}
        primary={next ? { label: `Step ${next.id}`, to: `/walkthrough/${next.id}`, disabled: !complete } : undefined}
        hint={next ? hint : undefined}
      />
    </div>
  )
}
