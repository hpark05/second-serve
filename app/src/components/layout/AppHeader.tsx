import { Database } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Wordmark } from '@/components/brand/LeafMark'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { SCENARIO_LABELS, SCENARIOS, type ScenarioId } from '@/data/bundle'
import { useBundle } from '@/data/useBundle'

export const FICTIONAL_BANNER = 'Fictional scenario · Sample data only'

/** Sticky top bar: wordmark, banner on walkthrough routes, scenario + hall switchers, and a role slot. */
export function AppHeader({
  walkthrough,
  roleSlot,
  bannerLabel,
}: {
  walkthrough: boolean
  roleSlot?: ReactNode
  /** From the scenario fixture's banner_label; falls back to the spec copy while it loads. */
  bannerLabel?: string
}) {
  const { bundle, hall, setHall, scenario, setScenario, isFixture, url } = useBundle()

  return (
    <header className="no-print sticky top-0 z-30 border-b bg-card">
      <div className="flex min-h-16 flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2 sm:px-6">
        <Link to="/dashboard" className="flex min-h-11 items-center rounded-control" aria-label="Second Serve home">
          <Wordmark />
        </Link>

        {walkthrough ? (
          <p className="text-meta text-muted-foreground">{bannerLabel || FICTIONAL_BANNER}</p>
        ) : isFixture ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex min-h-8 items-center gap-1.5 rounded-full bg-amber-soft px-3 text-meta font-medium text-amber">
                <Database className="size-3.5" aria-hidden="true" />
                Fixture data
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-64">
              No generated bundle for {SCENARIO_LABELS[scenario]} yet, so every scenario shows the illustrative fixture
              ({url}).
            </TooltipContent>
          </Tooltip>
        ) : (
          <span className="hidden text-meta text-muted-foreground md:inline">
            Synthetic bundle · dates relative to the simulated today
          </span>
        )}

        <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
          {roleSlot}
          {walkthrough ? null : (
            <>
              <Select value={scenario} onValueChange={(v) => setScenario(v as ScenarioId)}>
                <SelectTrigger className="min-w-40" aria-label="Scenario">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Scenario</SelectLabel>
                    {SCENARIOS.map((s) => (
                      <SelectItem key={s} value={s}>
                        {SCENARIO_LABELS[s]}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              <Select value={hall} onValueChange={setHall}>
                <SelectTrigger className="min-w-40" aria-label="Dining hall">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Dining hall</SelectLabel>
                    {bundle.halls.map((h) => (
                      <SelectItem key={h.id} value={h.id}>
                        {h.name}
                      </SelectItem>
                    ))}
                    <SelectItem value="all">All dining halls</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
