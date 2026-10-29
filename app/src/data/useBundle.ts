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
import type { ClickableStatus } from './action-status'
import type { Bundle, ScenarioId } from './bundle'
import { normalizeBundle } from './normalize-bundle'

// THE one line to change when swapping data sources. Generated bundles live at
// public/data/<scenario>/bundle.json (copied by `pnpm data:sync`); the fixture is the fallback.
const DATA_ROOT = `${import.meta.env.BASE_URL}data`
const FIXTURE_URL = `${DATA_ROOT}/fixture/bundle.json`
const scenarioUrl = (s: ScenarioId) => `${DATA_ROOT}/${s}/bundle.json`

export type HallFilter = 'all' | string

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; bundle: Bundle; url: string; isFixture: boolean }

const cache = new Map<ScenarioId, Promise<{ bundle: Bundle; url: string; isFixture: boolean }>>()

async function fetchJson(url: string): Promise<Bundle | null> {
  const res = await fetch(url)
  // Why: Vite dev and SPA hosts answer missing files with index.html (200), so check content-type too.
  if (!res.ok || !res.headers.get('content-type')?.includes('json')) return null
  return normalizeBundle(await res.json())
}

export function loadBundle(scenario: ScenarioId) {
  let p = cache.get(scenario)
  if (!p) {
    p = (async () => {
      const url = scenarioUrl(scenario)
      const generated = await fetchJson(url).catch(() => null)
      if (generated) return { bundle: generated, url, isFixture: generated.meta.source === 'fixture' }
      const fixture = await fetchJson(FIXTURE_URL)
      if (!fixture) throw new Error(`No bundle at ${url} and no fixture at ${FIXTURE_URL}`)
      return { bundle: fixture, url: FIXTURE_URL, isFixture: true }
    })()
    cache.set(scenario, p)
    p.catch(() => cache.delete(scenario))
  }
  return p
}

interface BundleContextValue {
  state: LoadState
  scenario: ScenarioId
  setScenario: (s: ScenarioId) => void
  hall: HallFilter
  setHall: (h: HallFilter) => void
  /** Session-only action status per rec/transfer id. Clicks reach planned or completed, never verified. */
  statuses: ReadonlyMap<string, ClickableStatus>
  /** Ids with any status (planned or completed). */
  approved: ReadonlySet<string>
  /** Marks an action planned (no-op if already further along). */
  approve: (id: string) => void
  complete: (id: string) => void
  planApplied: boolean
  applyPlan: () => void
}

const BundleContext = createContext<BundleContextValue | null>(null)

const readSession = (k: string) => {
  try {
    return sessionStorage.getItem(k)
  } catch {
    return null
  }
}
const writeSession = (k: string, v: string) => {
  try {
    sessionStorage.setItem(k, v)
  } catch {
    /* private mode: keep in memory only */
  }
}

export function BundleProvider({ children }: { children: ReactNode }) {
  const [scenario, setScenarioRaw] = useState<ScenarioId>(
    () => (readSession('ss.scenario') as ScenarioId | null) ?? 'normal_week',
  )
  const [hall, setHallRaw] = useState<HallFilter>(() => readSession('ss.hall') ?? 'all')
  const [state, setState] = useState<LoadState>({ status: 'loading' })
  const [statuses, setStatuses] = useState<Map<string, ClickableStatus>>(() => new Map())
  const [planApplied, setPlanApplied] = useState(false)

  useEffect(() => {
    let live = true
    setState({ status: 'loading' })
    loadBundle(scenario).then(
      (r) => live && setState({ status: 'ready', ...r }),
      (e: unknown) => live && setState({ status: 'error', error: String(e) }),
    )
    return () => {
      live = false
    }
  }, [scenario])

  const setScenario = useCallback((s: ScenarioId) => {
    writeSession('ss.scenario', s)
    setScenarioRaw(s)
    setStatuses(new Map())
    setPlanApplied(false)
  }, [])
  const setHall = useCallback((h: HallFilter) => {
    writeSession('ss.hall', h)
    setHallRaw(h)
  }, [])
  const approve = useCallback(
    (id: string) => setStatuses((prev) => (prev.has(id) ? prev : new Map(prev).set(id, 'planned'))),
    [],
  )
  const complete = useCallback((id: string) => setStatuses((prev) => new Map(prev).set(id, 'completed')), [])
  const approved = useMemo(() => new Set(statuses.keys()), [statuses])
  const applyPlan = useCallback(() => setPlanApplied(true), [])

  const value = useMemo(
    () => ({
      state,
      scenario,
      setScenario,
      hall,
      setHall,
      statuses,
      approved,
      approve,
      complete,
      planApplied,
      applyPlan,
    }),
    [state, scenario, setScenario, hall, setHall, statuses, approved, approve, complete, planApplied, applyPlan],
  )
  return createElement(BundleContext.Provider, { value }, children)
}

export function useBundleContext() {
  const ctx = useContext(BundleContext)
  if (!ctx) throw new Error('useBundle must be used inside <BundleProvider>')
  return ctx
}

/** Pages call this. Only valid under <BundleGate>, which guarantees the bundle is loaded. */
export function useBundle() {
  const ctx = useBundleContext()
  if (ctx.state.status !== 'ready') throw new Error('useBundle called before the bundle loaded')
  return { ...ctx, bundle: ctx.state.bundle, isFixture: ctx.state.isFixture, url: ctx.state.url }
}
