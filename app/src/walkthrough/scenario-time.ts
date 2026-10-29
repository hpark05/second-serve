import type { RelativeTime, TimeWindow } from '@/data/scenario'

/** Scenario-relative day label: day 0 is "Today". */
export function dayLabel(day: number): string {
  if (day === 0) return 'Today'
  if (day === 1) return 'Tomorrow'
  if (day === -1) return 'Yesterday'
  return day > 0 ? `+${day}d` : `${-day}d ago`
}

export const at = (t: RelativeTime) => `${dayLabel(t.day)} ${t.time}`

export function windowLabel(w: TimeWindow): string {
  return w.start.day === w.end.day ? `${at(w.start)}–${w.end.time}` : `${at(w.start)} to ${at(w.end)}`
}

/** Minutes since day 0 00:00, for ordering. */
export const minutes = (t: RelativeTime) => {
  const [h, m] = t.time.split(':').map(Number)
  return t.day * 1440 + h * 60 + m
}
