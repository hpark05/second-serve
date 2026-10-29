import { ArrowRight, BellRing } from 'lucide-react'

/** Full-width card: the system notified the next role. One tap opens their view (switches the seat). */
export function HandoffCard({ to, waitingFor, onHandoff }: { to: string; waitingFor: string; onHandoff: () => void }) {
  return (
    <button
      type="button"
      onClick={onHandoff}
      aria-label={`Notification sent to ${to}. View as ${to}`}
      className="group flex min-h-[72px] w-full items-center justify-between gap-4 rounded-xl border-2 border-green bg-green-soft px-6 py-4 text-left transition-colors hover:bg-green-chip focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
    >
      <span className="flex min-w-0 items-start gap-3">
        <BellRing className="mt-1 size-5 flex-none text-green" aria-hidden="true" />
        <span className="min-w-0">
          <span className="block font-heading text-[18px] leading-snug font-semibold text-ink">
            Notification sent to {to}
          </span>
          <span className="mt-0.5 block text-[14px] text-muted-foreground">Waiting on {waitingFor}</span>
        </span>
      </span>
      <span className="flex flex-none items-center gap-1.5 text-[14px] font-medium text-green">
        View as {to}
        <ArrowRight className="size-5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
      </span>
    </button>
  )
}
