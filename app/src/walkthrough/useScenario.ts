import {
  createContext,
  createElement,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import type { ScenarioPath, ScenarioPathId, TransferEvent, TransferScenario, TransferState } from '@/data/scenario'
import { ACTOR_SEAT, SEAT_ACTOR, type Seat } from './roles'
import { STEPS, type WalkthroughStep } from './steps'

export const SCENARIO_URL = `${import.meta.env.BASE_URL}data/scenario-spinach.json`

/** Events a click may never apply: only an outside system import can produce `verified`. */
export const HELD_EVENT_TYPES = new Set<TransferEvent['type']>(['records_imported'])

type Load = { status: 'loading' } | { status: 'error'; error: string } | { status: 'ready'; scenario: TransferScenario }

interface Progress {
  /** The path whose next events are offered first; switches when a branch is taken. */
  pathId: ScenarioPathId
  /** Concrete events applied so far, in order. Held events are only added by importRecords. */
  events: TransferEvent[]
}

export interface ScenarioValue {
  load: Load
  seat: Seat
  /** Free-roam role switch (header). Inside the walkthrough prefer `handoffTo`. */
  setSeat: (s: Seat) => void
  /** Guided role handoff ("Notification sent to Kitchen B"). Same effect as setSeat; named for the walkthrough. */
  handoffTo: (s: Seat) => void
  progress: Progress
  /** Bumps on every restart, so per-step init guards can rerun for the same step. */
  runId: number
  /** Apply one next event (from `nextOptions`). No-op if an event with the same seq is already applied. */
  apply: (pathId: ScenarioPathId, event: TransferEvent) => void
  /** Presenter only: replace progress with the first `count` fixture events of a path. */
  seek: (pathId: ScenarioPathId, count: number) => void
  /** Participant Back: keep the first `count` events the participant actually applied, drop the rest. */
  rewind: (pathId: ScenarioPathId, count: number) => void
  /** System only: append the path's held records_imported events (the next Eatec exports). Idempotent. */
  importRecords: () => void
  /** Reset events and role together. Callers also navigate to step 1. */
  restart: () => void
}

const Ctx = createContext<ScenarioValue | null>(null)

/** A path's events minus held ones, so progression never waits on an outside import. */
export const playable = (p: ScenarioPath) => p.events.filter((e) => !HELD_EVENT_TYPES.has(e.type))

const startOf = (s: TransferScenario | null): Progress => {
  const happy = s?.paths.find((p) => p.id === 'happy')
  // Why: the 06:00 Eatec import is the starting fact of the scenario, not a demo step.
  const first = happy ? playable(happy)[0] : undefined
  return { pathId: 'happy', events: first?.type === 'inventory_imported' ? [first] : [] }
}

const START_SEAT: Seat = 'kitchen_a'

export function ScenarioProvider({ children }: { children: ReactNode }) {
  const [load, setLoad] = useState<Load>({ status: 'loading' })
  const [seat, setSeat] = useState<Seat>(START_SEAT)
  const [progress, setProgress] = useState<Progress>(() => startOf(null))
  const [runId, setRunId] = useState(0)
  const scenario = load.status === 'ready' ? load.scenario : null

  useEffect(() => {
    let live = true
    fetch(SCENARIO_URL)
      .then(async (r) => {
        if (!r.ok || !r.headers.get('content-type')?.includes('json')) throw new Error(`No scenario at ${SCENARIO_URL}`)
        return (await r.json()) as TransferScenario
      })
      .then(
        (s) => {
          if (!live) return
          setLoad({ status: 'ready', scenario: s })
          setProgress((p) => (p.events.length ? p : startOf(s)))
        },
        (e: unknown) => live && setLoad({ status: 'error', error: String(e) }),
      )
    return () => {
      live = false
    }
  }, [])

  // Why: double taps and replayed autoplay beats call apply twice before a render; seq makes it idempotent.
  const apply = useCallback(
    (pathId: ScenarioPathId, event: TransferEvent) =>
      setProgress((p) => (p.events.some((e) => e.seq === event.seq) ? p : { pathId, events: [...p.events, event] })),
    [],
  )
  const seek = useCallback(
    (pathId: ScenarioPathId, count: number) => {
      const path = scenario?.paths.find((p) => p.id === pathId)
      if (path) setProgress({ pathId, events: playable(path).slice(0, count) })
    },
    [scenario],
  )
  const rewind = useCallback(
    (pathId: ScenarioPathId, count: number) =>
      setProgress((p) => {
        const own = p.events.filter((e) => !HELD_EVENT_TYPES.has(e.type))
        // Why: imports check the whole transfer, so they only survive when nothing they checked was dropped.
        const keepImports = count >= own.length
        const kept = own.slice(0, count)
        const events = keepImports ? p.events : kept
        return p.pathId === pathId && events.length === p.events.length ? p : { pathId, events }
      }),
    [],
  )
  const restart = useCallback(() => {
    setProgress(startOf(scenario))
    setSeat(START_SEAT)
    setRunId((n) => n + 1)
  }, [scenario])
  const importRecords = useCallback(() => {
    if (!scenario) return
    setProgress((p) => {
      const path = scenario.paths.find((x) => x.id === p.pathId)
      if (!path) return p
      const have = new Set(p.events.map((e) => e.seq))
      const held = path.events.filter((e) => HELD_EVENT_TYPES.has(e.type) && !have.has(e.seq))
      return held.length ? { ...p, events: [...p.events, ...held] } : p
    })
  }, [scenario])

  const value = useMemo(
    () => ({
      load,
      seat,
      setSeat,
      handoffTo: setSeat,
      progress,
      runId,
      apply,
      seek,
      rewind,
      importRecords,
      restart,
    }),
    [load, seat, progress, runId, apply, seek, rewind, importRecords, restart],
  )
  return createElement(Ctx.Provider, { value }, children)
}

export function useScenarioContext() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useScenario must be used inside <ScenarioProvider>')
  return ctx
}

const pathById = (s: TransferScenario, id: ScenarioPathId) => s.paths.find((p) => p.id === id) as ScenarioPath

/** True when the path's playable events start with the applied event types (held imports ignored). */
const continues = (p: ScenarioPath, applied: TransferEvent[]) => {
  const ev = playable(p)
  return ev.length > applied.length && applied.every((e, i) => e.type === ev[i].type)
}

/** How many applied events match the start of a path, by event type. */
export const sharedPrefix = (p: ScenarioPath, applied: TransferEvent[]) => {
  const ev = playable(p)
  let n = 0
  while (n < applied.length && n < ev.length && applied[n].type === ev[n].type) n++
  return n
}

export interface NextOption {
  pathId: ScenarioPathId
  event: TransferEvent
}

/** Derived view of the transfer: applied events, current state, and what can happen next. */
export function useTransfer() {
  const ctx = useScenarioContext()
  if (ctx.load.status !== 'ready') throw new Error('useTransfer called before the scenario loaded')
  const { scenario } = ctx.load
  const { pathId, events: all } = ctx.progress
  const { seat } = ctx
  return useMemo(() => {
    const path = pathById(scenario, pathId)
    const applied = all.filter((e) => !HELD_EVENT_TYPES.has(e.type))
    const imports = all.filter((e) => HELD_EVENT_TYPES.has(e.type))
    // Why: imports are appended after the clicks they check, so the log orders by seq to read chronologically.
    const log = [...all].sort((a, b) => a.seq - b.seq)
    const last = applied[applied.length - 1]
    const state: TransferState | null = last ? last.to_state : null
    // Current path first, so its variant of a shared event type wins.
    const ordered = [path, ...scenario.paths.filter((p) => p.id !== pathId)]
    const options: NextOption[] = []
    const seen = new Set<string>()
    for (const p of ordered) {
      if (!continues(p, applied)) continue
      const event = playable(p)[applied.length]
      // Why: paths share a prefix and branch by event type; the current path's variant of a type wins.
      if (seen.has(event.type)) continue
      seen.add(event.type)
      options.push({ pathId: p.id, event })
    }
    const planned = [...log].reverse().find((e) => e.sets?.planned_action)?.sets?.planned_action ?? null
    const completed = log.flatMap((e) => (e.sets?.completed_action ? [e.sets.completed_action] : []))
    const verified = [...log].reverse().find((e) => e.sets?.verified_outcome)?.sets?.verified_outcome ?? null
    // Why: the path's last records_imported event names every check that would verify it, before any import runs.
    const expectedChecks =
      [...path.events].reverse().find((e) => e.sets?.verified_outcome)?.sets?.verified_outcome?.checks ?? []
    const forSeat = (s: Seat) => options.filter((o) => o.event.actor === SEAT_ACTOR[s])
    const systemOptions = options.filter((o) => o.event.actor === 'system')
    const done = options.length === 0
    // The person who acts next on the current path; drives the "Notification sent to …" card.
    const nextPerson = options.find((o) => o.pathId === pathId && o.event.actor !== 'system') ?? null
    const nextSeat: Seat | null = nextPerson ? (ACTOR_SEAT[nextPerson.event.actor] ?? null) : null
    const handoff = nextSeat && nextSeat !== seat && !forSeat(seat).length ? { to: nextSeat } : null
    return {
      scenario,
      path,
      applied,
      imports,
      log,
      last,
      state,
      options,
      forSeat,
      systemOptions,
      planned,
      completed,
      verified,
      expectedChecks,
      done,
      nextSeat,
      handoff,
    }
  }, [scenario, pathId, all, seat])
}

export type Transfer = ReturnType<typeof useTransfer>

const isVariant = (step: WalkthroughStep) => !STEPS.some((s) => s.id === step.id)

/** A variant step's own branch: the decline and expired variants are named after their paths. */
const variantPath = (step: WalkthroughStep) => step.id as ScenarioPathId

/** True once the step's required action is done, so Next may enable. */
export function isStepComplete(step: WalkthroughStep, t: Transfer): boolean {
  if (isVariant(step)) return t.path.id === variantPath(step) && t.done
  if (t.path.id !== step.path || t.applied.length < step.to) return false
  return !step.runsImports || t.verified?.status === 'verified'
}

/** First main step whose action is still open, given the participant's own events. */
export function resumeStep(t: Transfer): WalkthroughStep {
  const happy = pathById(t.scenario, 'happy')
  const n = sharedPrefix(happy, t.applied)
  return STEPS.find((s) => n < s.to) ?? STEPS[STEPS.length - 1]
}

/**
 * Where the participant's events must be to open `step` without inventing any: rewind target, or null when the
 * step isn't reached yet (redirect to `resumeStep`). Never seeks forward.
 */
export function stepEntry(step: WalkthroughStep, t: Transfer): { pathId: ScenarioPathId; count: number } | null {
  if (isVariant(step) && t.path.id === variantPath(step)) return { pathId: t.path.id, count: t.applied.length }
  const happy = pathById(t.scenario, 'happy')
  const shared = sharedPrefix(happy, t.applied)
  // Why: a variant replaces Kitchen B's review, so it opens just before that review.
  const count = Math.min(shared, isVariant(step) ? step.from : step.to)
  return count < step.from ? null : { pathId: 'happy', count }
}
