import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const chip = cva(
  'inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-1 text-[11.5px] font-semibold',
  {
    variants: {
      tone: {
        good: 'bg-green-chip text-green',
        first: 'bg-amber-soft text-amber',
        expired: 'bg-red-soft text-red',
        transfer: 'bg-blue-soft text-blue',
        recover: 'bg-purple-soft text-purple',
        muted: 'bg-muted text-muted-foreground',
      },
    },
    defaultVariants: { tone: 'good' },
  },
)

export function StatusChip({
  tone,
  className,
  children,
}: VariantProps<typeof chip> & { className?: string; children: React.ReactNode }) {
  return <span className={cn(chip({ tone }), className)}>{children}</span>
}
