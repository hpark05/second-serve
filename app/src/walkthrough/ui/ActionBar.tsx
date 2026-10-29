import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { cn } from '@/lib/utils'

export interface BarAction {
  label: string
  /** Route to go to; omit to use onClick. */
  to?: string
  onClick?: () => void
  disabled?: boolean
}

const base =
  'inline-flex h-12 min-w-[44px] items-center justify-center gap-1.5 rounded-lg px-5 text-[16px] font-medium transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none'

function BarButton({ action, kind }: { action: BarAction; kind: 'primary' | 'back' }) {
  const cls = cn(
    base,
    kind === 'primary'
      ? action.disabled
        ? 'cursor-not-allowed border bg-muted text-muted-foreground'
        : 'bg-primary text-primary-foreground hover:bg-primary/85'
      : 'border bg-card text-ink hover:bg-muted',
  )
  const body =
    kind === 'back' ? (
      <>
        <ChevronLeft className="size-5" aria-hidden="true" /> {action.label}
      </>
    ) : (
      <>
        {action.label} <ChevronRight className="size-5" aria-hidden="true" />
      </>
    )
  if (action.to && !action.disabled)
    return (
      <Link to={action.to} className={cls}>
        {body}
      </Link>
    )
  return (
    <button type="button" className={cls} disabled={action.disabled} onClick={action.onClick}>
      {body}
    </button>
  )
}

/**
 * Sticky bottom bar: Back plus the one primary action. Sits in normal flow at the end of the page
 * and sticks to the viewport bottom, so it is never pushed off-screen and never covers the last card.
 */
export function ActionBar({ primary, back, hint }: { primary?: BarAction; back?: BarAction; hint?: ReactNode }) {
  return (
    <nav
      aria-label="Walkthrough steps"
      className="sticky bottom-0 z-20 -mx-4 mt-6 border-t bg-card/95 px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-sm sm:-mx-6 sm:px-6"
    >
      <div className="mx-auto flex max-w-[960px] items-center gap-3">
        {back ? <BarButton action={back} kind="back" /> : null}
        <div className="min-w-0 flex-1 text-right text-[13px] text-muted-foreground">{hint}</div>
        {primary ? <BarButton action={primary} kind="primary" /> : null}
      </div>
    </nav>
  )
}
