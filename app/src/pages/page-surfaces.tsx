import { cva, type VariantProps } from 'class-variance-authority'
import { Link } from 'react-router'
import { cn } from '@/lib/utils'

// Why: tokens from docs/design-spec.md may not have landed in index.css yet; var() fallbacks keep pages correct either way.
export const LIME_BUTTON =
  'h-11 rounded-lg bg-[var(--lime,#7ED957)] px-4 text-[15px] font-semibold text-[var(--ink,#171C17)] hover:bg-[color-mix(in_oklch,var(--lime,#7ED957),black_8%)] focus-visible:ring-[var(--green,#285C35)]/40'
export const QUIET_BUTTON =
  'h-11 rounded-lg border border-border bg-card px-4 text-[15px] font-medium text-foreground hover:bg-[var(--bg,#FAFBF9)]'
export const TEXT_LINK =
  'inline-flex min-h-11 items-center gap-1 text-[14px] font-semibold text-[var(--green,#285C35)] underline-offset-4 hover:underline'

export function PageTitle({
  title,
  sub,
  action,
}: {
  title: React.ReactNode
  sub?: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 max-w-[640px]">
        <h1 className="font-heading text-[28px] leading-[32px] font-semibold tracking-tight text-foreground">
          {title}
        </h1>
        {sub ? <p className="mt-2 text-[14px] leading-relaxed text-muted-foreground">{sub}</p> : null}
      </div>
      {action ? <div className="flex flex-wrap items-center gap-2">{action}</div> : null}
    </header>
  )
}

export function Surface({
  className,
  children,
  as: Tag = 'section',
  id,
}: {
  className?: string
  children: React.ReactNode
  as?: 'section' | 'article' | 'div'
  id?: string
}) {
  return (
    <Tag id={id} className={cn('min-w-0 rounded-xl border border-border bg-card p-6', className)}>
      {children}
    </Tag>
  )
}

export function SurfaceTitle({
  title,
  hint,
  aside,
}: {
  title: React.ReactNode
  hint?: React.ReactNode
  aside?: React.ReactNode
}) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="font-heading text-[18px] leading-snug font-semibold text-foreground">{title}</h2>
        {hint ? <p className="mt-1 text-[13px] text-muted-foreground">{hint}</p> : null}
      </div>
      {aside}
    </div>
  )
}

const chip = cva(
  'inline-flex h-6 shrink-0 items-center gap-1 rounded-full px-2.5 text-[12px] leading-none font-medium whitespace-nowrap',
  {
    variants: {
      tone: {
        sample:
          'border border-dashed border-[var(--amber,#C7731A)]/60 bg-[var(--amber-soft,#FDF1E3)] text-[var(--amber,#C7731A)]',
        illustrative: 'border border-border bg-card text-muted-foreground',
        planned: 'bg-[var(--amber-soft,#FDF1E3)] text-[var(--amber,#C7731A)]',
        completed: 'bg-[var(--lime-soft,#EAF8E2)] text-foreground',
        verified: 'bg-[var(--lime-soft,#EAF8E2)] text-[var(--green,#285C35)]',
        declined: 'bg-[var(--red-soft,#FDE7E2)] text-[var(--red,#C4452C)]',
        expiring: 'bg-[var(--red-soft,#FDE7E2)] text-[var(--red,#C4452C)]',
        neutral: 'bg-[var(--bg,#FAFBF9)] text-muted-foreground ring-1 ring-border ring-inset',
      },
    },
    defaultVariants: { tone: 'neutral' },
  },
)

export function Chip({
  tone,
  className,
  children,
}: VariantProps<typeof chip> & { className?: string; children: React.ReactNode }) {
  return <span className={cn(chip({ tone }), className)}>{children}</span>
}

/** "Illustrative" marker that deep-links to the grounding row on /sources. */
export function IllustrativeTag({ source, className }: { source: string; className?: string }) {
  return (
    <Link
      to={`/sources#${source}`}
      title={`Illustrative figure. Source: ${source}`}
      // Why: the chip is 24px tall; the pseudo-element pads its hit area to the 44px touch minimum.
      className={cn(
        chip({ tone: 'illustrative' }),
        "relative align-middle after:absolute after:-inset-x-1 after:-inset-y-2.5 after:content-[''] hover:border-[var(--green,#285C35)] hover:text-[var(--green,#285C35)]",
        className,
      )}
    >
      Illustrative
    </Link>
  )
}

/** One figure: a big Poppins number, small muted unit, label above, provenance below. */
export function Figure({
  label,
  value,
  unit,
  note,
  tag,
}: {
  label: string
  value: React.ReactNode
  unit?: string
  note?: React.ReactNode
  tag?: React.ReactNode
}) {
  return (
    <Surface as="div" className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[14px] font-medium text-muted-foreground">{label}</span>
        {tag}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="tabular font-heading text-[40px] leading-none font-bold tracking-tight text-foreground">
          {value}
        </span>
        {unit ? <span className="text-[14px] text-muted-foreground">{unit}</span> : null}
      </div>
      {note ? <p className="text-[13px] leading-snug text-muted-foreground">{note}</p> : null}
    </Surface>
  )
}

/** Labelled value used in stacked (mobile) rows and proposal meta. */
export function Meta({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('min-w-0', className)}>
      <dt className="text-[12px] font-medium tracking-[0.06em] text-muted-foreground uppercase">{label}</dt>
      <dd className="mt-1 text-[14px] text-foreground">{children}</dd>
    </div>
  )
}
