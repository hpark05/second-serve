import { useCallback, useEffect, useRef, useState } from 'react'
import type { Seat } from './roles'
import { ACTOR_SEAT } from './roles'
import { STEPS, type WalkthroughStep } from './steps'
import { isStepComplete, type NextOption, type Transfer, useScenarioContext, useTransfer } from './useScenario'

export const END_CARD_MS = 6000

/** What the autoplay does on its next beat. Pure, so the loop can't drift from the participant rules. */
type Beat =
  | { kind: 'handoff'; seat: Seat }
  | { kind: 'apply'; option: NextOption }
  | { kind: 'import' }
  | { kind: 'advance' }
  | { kind: 'reseek' }
  | { kind: 'wait' }

export function nextBeat(step: WalkthroughStep, t: Transfer, seat: Seat): Beat {
  if (isStepComplete(step, t)) return { kind: 'advance' }
  // Why: someone clicked a branch (decline, let it lapse) while paused; resuming returns to the script.
  if (t.path.id !== step.path || t.applied.length < step.from) return { kind: 'reseek' }
  const option = t.options.find((o) => o.pathId === step.path && o.event.actor !== 'system')
  if (option && t.applied.length < step.to) {
    const who = ACTOR_SEAT[option.event.actor]
    if (who && who !== seat) return { kind: 'handoff', seat: who }
    return { kind: 'apply', option }
  }
  if (seat !== step.seat) return { kind: 'handoff', seat: step.seat }
  if (step.runsImports && t.state === 'used') return { kind: 'import' }
  return { kind: 'wait' }
}

/** Gap between beats inside a step, so a step's actions fill about its autoplayMs. */
const beatGap = (step: WalkthroughStep) => {
  const beats = step.to - step.from + (step.runsImports ? 1 : 0) + 2
  return Math.min(3000, Math.max(1400, Math.round(step.autoplayMs / beats)))
}

export interface PresenterPlayback {
  index: number
  step: WalkthroughStep
  phase: 'step' | 'end'
  paused: boolean
  /** Completed loops since the page opened. */
  loop: number
  pause: () => void
  resume: () => void
  toggle: () => void
  /** Jump a step (arrow keys). Seeks the fixture: presenter only. Pauses playback. */
  go: (delta: 1 | -1) => void
}

/**
 * Hands-free loop over steps 1→6. Acts only through the participant scenario API (apply, handoffTo,
 * importRecords, restart), so it can't hold state of its own that drifts. `speed` > 1 shortens every delay (tests).
 */
export function usePresenterPlayback({ speed = 1 }: { speed?: number } = {}): PresenterPlayback {
  const { seat, apply, handoffTo, importRecords, restart, seek } = useScenarioContext()
  const t = useTransfer()
  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState<'step' | 'end'>('step')
  const [paused, setPaused] = useState(false)
  const [loop, setLoop] = useState(0)
  // Run time spent in the current step, counted only from beats that fired (pauses don't count).
  const elapsed = useRef(0)
  const beats = useRef(0)
  const step = STEPS[index]

  const enter = useCallback((i: number) => {
    elapsed.current = 0
    beats.current = 0
    setIndex(i)
  }, [])

  // Why: a fresh loop starts from the same clean state a participant's Restart gives.
  useEffect(() => {
    restart()
  }, [restart])

  useEffect(() => {
    if (paused) return
    if (phase === 'end') {
      const id = setTimeout(() => {
        restart()
        enter(0)
        setPhase('step')
        setLoop((n) => n + 1)
      }, END_CARD_MS / speed)
      return () => clearTimeout(id)
    }
    const beat = nextBeat(step, t, seat)
    const gap = beatGap(step)
    const delay =
      beat.kind === 'advance'
        ? Math.max(gap, step.autoplayMs - elapsed.current)
        : beats.current === 0
          ? Math.min(2200, gap)
          : gap
    const id = setTimeout(() => {
      elapsed.current += delay
      beats.current += 1
      if (beat.kind === 'handoff') handoffTo(beat.seat)
      else if (beat.kind === 'apply') apply(beat.option.pathId, beat.option.event)
      else if (beat.kind === 'import') importRecords()
      else if (beat.kind === 'reseek') seek(step.path, step.from)
      else if (beat.kind === 'advance') {
        if (index < STEPS.length - 1) enter(index + 1)
        else setPhase('end')
      }
    }, delay / speed)
    return () => clearTimeout(id)
  }, [paused, phase, step, index, t, seat, speed, apply, handoffTo, importRecords, restart, seek, enter])

  const go = useCallback(
    (delta: 1 | -1) => {
      setPaused(true)
      if (phase === 'end') {
        if (delta === -1) setPhase('step')
        return
      }
      const i = index + delta
      if (i >= STEPS.length) {
        setPhase('end')
        return
      }
      if (i < 0) return
      const target = STEPS[i]
      seek(target.path, target.from)
      handoffTo(target.seat)
      enter(i)
    },
    [phase, index, seek, handoffTo, enter],
  )

  return {
    index,
    step,
    phase,
    paused,
    loop,
    pause: () => setPaused(true),
    resume: () => setPaused(false),
    toggle: () => setPaused((p) => !p),
    go,
  }
}
