import { cn } from '@/lib/utils'

export function LeafMark({ className }: { className?: string }) {
  return (
    <span className={cn('grid size-7 flex-none place-items-center rounded-control bg-lime', className)}>
      <svg
        viewBox="0 0 24 24"
        className="size-4"
        fill="none"
        stroke="var(--ink)"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M5 19c0-8.5 5.5-13 14-14-.8 8.8-5.5 14-14 14z" />
        <path d="M5 19c2.8-4.6 6.3-7.4 10.5-9" />
      </svg>
    </span>
  )
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'flex items-center gap-2.5 font-heading text-[18px] font-bold tracking-[-0.01em] text-ink',
        className,
      )}
    >
      <LeafMark />
      Second Serve
    </span>
  )
}
