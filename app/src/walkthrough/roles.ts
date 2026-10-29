import type { ActorRole } from '@/data/scenario'

/** The three seats a presenter can sit in. `system` is never a seat. */
export type Seat = 'kitchen_a' | 'kitchen_b' | 'coordinator'

export const SEATS: Seat[] = ['kitchen_a', 'kitchen_b', 'coordinator']

export const SEAT_ACTOR: Record<Seat, ActorRole> = {
  kitchen_a: 'kitchen_a_cook',
  kitchen_b: 'kitchen_b_chef',
  coordinator: 'coordinator',
}

export const ACTOR_SEAT: Partial<Record<ActorRole, Seat>> = {
  kitchen_a_cook: 'kitchen_a',
  kitchen_b_chef: 'kitchen_b',
  coordinator: 'coordinator',
}

/** Hall filter that matches a seat, so the rest of the app follows the role switcher. */
export const seatHall = (seat: Seat, a: string, b: string) =>
  seat === 'kitchen_a' ? a : seat === 'kitchen_b' ? b : 'all'
