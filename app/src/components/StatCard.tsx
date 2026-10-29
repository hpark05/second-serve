import type { LucideIcon } from 'lucide-react'
import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

const tones = {
  green: 'bg-green-soft text-green',
  red: 'bg-red-soft text-red',
  amber: 'bg-amber-soft text-amber',
  blue: 'bg-blue-soft text-blue',
  purple: 'bg-purple-soft text-purple',
} as const

export function StatCard({
  icon: Icon,
  label,
  value,
  note,
  noteTone = 'green',
  tone = 'green',
  index = 0,
}: {
  icon: LucideIcon
  label: string
  value: React.ReactNode
  note?: React.ReactNode
  noteTone?: 'green' | 'red' | 'muted'
  tone?: keyof typeof tones
  index?: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05, ease: 'easeOut' }}
      className="rounded-[14px] border bg-card p-4 shadow-card"
    >
      <div className="mb-2.5 flex items-center gap-2 text-xs text-muted-foreground">
        <span className={cn('grid size-[26px] place-items-center rounded-lg', tones[tone])}>
          <Icon className="size-[14px]" aria-hidden="true" />
        </span>
        {label}
      </div>
      <div className="tabular text-[28px] font-bold leading-tight tracking-tight">{value}</div>
      {note ? (
        <div
          className={cn(
            'mt-1 text-xs',
            noteTone === 'green' && 'text-green',
            noteTone === 'red' && 'text-red',
            noteTone === 'muted' && 'text-muted-foreground',
          )}
        >
          {note}
        </div>
      ) : null}
    </motion.div>
  )
}
