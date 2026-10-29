import { ArrowRight } from 'lucide-react'

/** Full-width prompt to pass the iPad to the next role. One tap switches the seat. */
export function HandoffCard({ to, waitingFor, onHandoff }: { to: string; waitingFor: string; onHandoff: () => void }) {
  return (
    <button
      type="button"
      onClick={onHandoff}
      className="group flex min-h-[72px] w-full items-center justify-between gap-4 rounded-xl border-2 border-green bg-green-soft px-6 py-4 text-left transition-colors hover:bg-green-chip focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
    >
      <span className="min-w-0">
        <span className="block font-heading text-[18px] leading-snug font-semibold text-ink">
          Hand the iPad to {to}
        </span>
        <span className="mt-0.5 block text-[14px] text-muted-foreground">Next up: {waitingFor}</span>
      </span>
      <ArrowRight
        className="size-6 flex-none text-green transition-transform group-hover:translate-x-0.5"
        aria-hidden="true"
      />
    </button>
  )
}
