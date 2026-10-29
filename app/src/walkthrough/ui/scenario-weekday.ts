import type { RelativeTime, TimeWindow, TransferScenario } from '@/data/scenario'

const WEEK = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

/** Weekday name for a scenario day offset, from the fixture's `today_weekday`. */
export function weekdayOf(s: TransferScenario, day: number): string {
  const today = WEEK.indexOf(s.today_weekday)
  if (today < 0) return day === 0 ? 'Today' : `Day ${day}`
  return WEEK[(((today + day) % 7) + 7) % 7]
}

export const weekdayAt = (s: TransferScenario, t: RelativeTime) => `${weekdayOf(s, t.day)} ${t.time}`

/** "Wednesday 14:00–15:00", or "Wednesday 22:00 to Thursday 06:00" across days. */
export function weekdayWindow(s: TransferScenario, w: TimeWindow): string {
  return w.start.day === w.end.day
    ? `${weekdayAt(s, w.start)}–${w.end.time}`
    : `${weekdayAt(s, w.start)} to ${weekdayAt(s, w.end)}`
}

/** Rewrites fixture prose like "day 1 lunch" or "today 14:00" to weekday names for walkthrough screens. */
export function weekdayProse(s: TransferScenario, text: string): string {
  return text
    .replace(/\bday (-?\d+)\b/g, (_, d: string) => weekdayOf(s, Number(d)))
    .replace(/\btoday (?=\d{1,2}:\d{2})/gi, `${weekdayOf(s, 0)} `)
}
