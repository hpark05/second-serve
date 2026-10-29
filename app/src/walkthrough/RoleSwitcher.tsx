import { ChefHat, Route, Store } from 'lucide-react'
import type { TransferScenario } from '@/data/scenario'
import { cn } from '@/lib/utils'
import { SEATS, type Seat } from './roles'

const SEAT_UI: Record<Seat, { label: string; short: string; icon: typeof ChefHat }> = {
  kitchen_a: { label: 'Kitchen A (Crossroads)', short: 'Crossroads', icon: Store },
  kitchen_b: { label: 'Kitchen B (Café 3)', short: 'Café 3', icon: ChefHat },
  coordinator: { label: 'Coordinator', short: 'Coordinator', icon: Route },
}

export const seatLabel = (s: Seat) => SEAT_UI[s].label

/** "Kitchen B · Café 3 · Campus cafe", from the fixture when it is loaded. */
export function seatIdentity(seat: Seat, scenario?: TransferScenario | null): string {
  if (seat === 'coordinator') return 'Coordinator · Cal Dining operations'
  const k = scenario?.kitchens[seat === 'kitchen_a' ? 'a' : 'b']
  return k ? `${k.label} · ${k.name} · ${k.kind}` : SEAT_UI[seat].label
}

/** Read-only "You are:" pill for the walkthrough, where the handoff card changes roles. */
export function RolePill({ seat, scenario }: { seat: Seat; scenario?: TransferScenario | null }) {
  const Icon = SEAT_UI[seat].icon
  return (
    <output
      aria-live="polite"
      className="inline-flex min-h-11 max-w-full items-center gap-2 rounded-full border bg-card px-4 text-[14px] text-ink"
    >
      <Icon className="size-4 flex-none text-green" aria-hidden="true" />
      <span className="truncate">
        <span className="text-muted-foreground">You are: </span>
        {seatIdentity(seat, scenario)}
      </span>
    </output>
  )
}

/**
 * Role control. Interactive in free-roam; pass `readOnly` inside the walkthrough to show the pill instead.
 */
export function RoleSwitcher({
  seat,
  onSeat,
  readOnly,
  scenario,
}: {
  seat: Seat
  onSeat?: (s: Seat) => void
  readOnly?: boolean
  scenario?: TransferScenario | null
}) {
  if (readOnly || !onSeat) return <RolePill seat={seat} scenario={scenario} />
  return (
    <fieldset className="flex max-w-full flex-wrap gap-1 rounded-xl border bg-card p-1">
      <legend className="sr-only">Viewing as</legend>
      {SEATS.map((s) => {
        const { label, short, icon: Icon } = SEAT_UI[s]
        const on = s === seat
        return (
          <button
            key={s}
            type="button"
            aria-pressed={on}
            onClick={() => onSeat(s)}
            className={cn(
              'inline-flex min-h-11 items-center gap-1.5 rounded-lg px-3 text-[14px] whitespace-nowrap transition-colors',
              on ? 'bg-green font-semibold text-white' : 'text-muted-foreground hover:bg-muted',
            )}
          >
            <Icon className="size-4" aria-hidden="true" />
            <span className="sm:hidden">{short}</span>
            <span className="hidden sm:inline">{label}</span>
          </button>
        )
      })}
    </fieldset>
  )
}
