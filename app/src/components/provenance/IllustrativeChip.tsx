import { BookOpen } from 'lucide-react'
import { Link } from 'react-router'
import { cn } from '@/lib/utils'

/** Marks a number as illustrative and links to the source that grounds it on /sources. */
export function IllustrativeChip({ source, className }: { source: string; className?: string }) {
  return (
    <Link
      to={`/sources#${source}`}
      className={cn(
        'inline-flex items-center gap-1 rounded-full bg-amber-soft px-2 py-0.5 text-[10.5px] font-semibold whitespace-nowrap text-amber hover:underline',
        className,
      )}
      title={`Illustrative figure. Source: ${source}`}
    >
      <BookOpen className="size-3" aria-hidden="true" />
      Illustrative · source
    </Link>
  )
}

/** Marks a row or card as part of the fictional demo scenario. */
export function SampleDataBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border border-dashed border-amber bg-amber-soft px-2 py-0.5 text-[10.5px] font-semibold whitespace-nowrap text-amber',
        className,
      )}
    >
      Sample data
    </span>
  )
}
