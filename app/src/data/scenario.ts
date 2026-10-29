// Second Serve transfer scenario contract. Types only; the data lives in public/data/scenario-*.json.
// Prose spec and the transition rules: docs/transfer-flow.md.

/** Lifecycle of one transfer: Kitchen A sends, Kitchen B accepts or declines. Terminal: declined, used, expired. */
export type TransferState =
  | 'available'
  | 'requested'
  | 'accepted'
  | 'declined'
  | 'awaiting_pickup'
  | 'picked_up'
  | 'used'
  | 'expired'

export type TerminalTransferState = Extract<TransferState, 'declined' | 'used' | 'expired'>

/** Who acted. `system` is the clock and the Eatec import, never a person. */
export type ActorRole = 'kitchen_a_cook' | 'kitchen_b_chef' | 'coordinator' | 'system'

/** The three tiers the UI must keep apart. Only `system` can produce `verified`. */
export type ActionStatus = 'planned' | 'completed' | 'verified'

export type TransferEventType =
  | 'inventory_imported' // system: Eatec export read; no state change
  | 'offer_posted' // kitchen_a_cook marks extra food: null -> available
  | 'request_sent' // kitchen_a_cook sends the transfer offer to Kitchen B: available -> requested
  | 'request_accepted' // kitchen_b_chef: requested -> accepted
  | 'request_declined' // kitchen_b_chef: requested -> declined
  | 'pickup_scheduled' // coordinator: accepted -> awaiting_pickup
  | 'handoff_signed' // kitchen_a_cook + runner: awaiting_pickup -> picked_up
  | 'receipt_checked' // kitchen_b_chef: picked_up -> picked_up
  | 'use_recorded' // kitchen_b_chef: picked_up -> used
  | 'offer_lapsed' // system: any open state -> expired
  | 'records_imported' // system: later Eatec export; may set verified_outcome
  | 'disposition_noted' // kitchen_a_cook: after expired; informational only

/** Kitchen B's reason for saying no. */
export type DeclineReason = 'already_stocked' | 'cannot_meet_time' | 'no_cold_storage' | 'quality_concern' | 'other'

export type ExpiryReason = 'offer_window_closed' | 'needed_by_passed' | 'use_by_reached'

export type Disposition = 'use_first_here' | 'donate' | 'compost' | 'landfill'

/** Scenario-relative time. day 0 = "today" in the demo; time is 24h local "HH:MM". */
export interface RelativeTime {
  day: number
  time: string
}

export interface TimeWindow {
  start: RelativeTime
  end: RelativeTime
}

export interface SourceCitation {
  id: string
  label: string
  url: string
  /** Short verbatim or near-verbatim excerpt that supports the claim. */
  excerpt?: string
}

export interface Kitchen {
  /** Matches Hall.id in the bundle (crossroads, cafe-3). */
  hall_id: string
  name: string
  /** "Kitchen A" (has the food) or "Kitchen B" (needs it). */
  label: 'Kitchen A' | 'Kitchen B'
  /** Eatec's word for this side of a transfer. */
  eatec_role: 'From Location' | 'To Location'
  /** Deck wording; render as `${name} · ${kind}`, e.g. "Café 3 · Campus cafe". */
  kind: 'Dining hall' | 'Campus cafe'
}

export interface RoleCard {
  role: ActorRole
  title: string
  /** Fictional display name for the demo; never a real staff member. */
  display_name: string
  kitchen_hall_id: string | null
  does: string
}

export interface MenuItemRef {
  hall_id: string
  name: string
  station: string
  meal_period: 'breakfast' | 'brunch' | 'lunch' | 'dinner'
  /** Day the item is served, relative to day 0. */
  day: number
  serving_size?: string
  eatec_recipe_id?: string
  /** A real scraped menu row this item was taken from. */
  source_url: string
  source_menu_date: string
}

export interface Allocation {
  qty_lb: number
  menu_item: MenuItemRef
  basis: string
}

export interface InventoryLotSample {
  lot_id: string
  hall_id: string
  ingredient_id: string
  ingredient_name: string
  on_hand_lb: number
  allocated: Allocation[]
  available_lb: number
  storage: 'refrigerated'
  received: RelativeTime
  /** Last usable moment, inclusive. Day 2 23:59 reads as the deck's "best by Friday". */
  use_by: RelativeTime
  shelf_life_basis: string
  /** Shown verbatim in the UI as the provenance line. */
  source_label: string
  source_system: 'Eatec'
  exported_at: RelativeTime
}

export interface TemperatureConstraint {
  food_class: string
  hold_max_f: number
  transport_max_f: number
  /** CalCode 113996(a): transport under this many minutes is outside the 41°F hold rule. */
  short_transport_exempt_minutes: number
  /** Second Serve's receiving rule (stricter than code): reject above this at receipt. */
  receive_reject_above_f: number
  carrier: string
  plain_language: string
  source_ids: string[]
}

export interface PickupDetails {
  window: TimeWindow
  runner_role: string
  carrier: string
}

/** Optional fields an event may carry. Which are required per event type is in docs/transfer-flow.md. */
export interface TransferEventFields {
  qty_lb?: number
  lot_id?: string
  intended_use?: MenuItemRef
  needed_by?: RelativeTime
  offer_until?: RelativeTime
  storage_constraint?: string
  pickup?: PickupDetails
  temperature_f?: number
  temperature_point?: 'walk_in' | 'handoff' | 'receipt'
  signed_by?: ActorRole[]
  runner?: string
  decline_reason?: DeclineReason
  expiry_reason?: ExpiryReason
  disposition?: Disposition
  note?: string
  /** Record pulled from an outside system during records_imported. */
  external_record?: ExternalRecord
}

export interface ExternalRecord {
  system: 'Eatec'
  kind: 'inventory_snapshot' | 'transfer_posting' | 'production_record'
  reference: string
  summary: string
}

export interface PlannedAction {
  status: 'planned'
  qty_lb: number
  from_hall_id: string
  to_hall_id: string
  intended_use: MenuItemRef
  needed_by: RelativeTime
  set_by_event: number
}

export interface CompletedAction {
  status: 'completed'
  kind: 'transferred' | 'used'
  qty_lb: number
  at: RelativeTime
  /** Always true: a person reported it in Second Serve. */
  self_reported: true
  set_by_event: number
}

export type VerificationCheckStatus = 'match' | 'mismatch' | 'pending'

export interface VerificationCheck {
  check: 'transfer_posted' | 'production_recorded' | 'no_waste_entry'
  status: VerificationCheckStatus
  evidence: string | null
  set_by_event: number | null
}

export interface VerifiedOutcome {
  status: 'verified' | 'mismatch' | 'pending'
  /** Always system: no click sets this. */
  set_by: 'system'
  qty_lb: number | null
  checks: VerificationCheck[]
  set_by_event: number
}

/** What an event wrote to the three tiers. A check's evidence comes only from a records_imported event. */
export interface EventEffects {
  planned_action?: PlannedAction
  completed_action?: CompletedAction
  verified_outcome?: VerifiedOutcome
}

export interface TransferEvent {
  seq: number
  at: RelativeTime
  actor: ActorRole
  type: TransferEventType
  /** null for the first event of a transfer. Equal to to_state when the event changes no state. */
  from_state: TransferState | null
  to_state: TransferState | null
  fields: TransferEventFields
  sets?: EventEffects
  /** One line, in kitchen language, as the activity log should show it. */
  log_line: string
}

export type ScenarioPathId = 'happy' | 'decline' | 'expired'

export interface ScenarioPath {
  id: ScenarioPathId
  title: string
  summary: string
  events: TransferEvent[]
  final_state: TerminalTransferState
  planned_action: PlannedAction | null
  completed_actions: CompletedAction[]
  verified_outcome: VerifiedOutcome | null
}

export interface TransferScenario {
  /** Always true: the scenario is fictional and must render with a "Sample" label. */
  sample: true
  fictional_notice: string
  /** Short banner for every walkthrough screen, verbatim from docs/design-spec.md. */
  banner_label: string
  scenario_id: string
  title: string
  time_basis: string
  /** Weekday of day 0, so the UI can say "Thursday" for day 1 as the deck does. Timestamps stay relative. */
  today_weekday: 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday' | 'Friday' | 'Saturday' | 'Sunday'
  kitchens: { a: Kitchen; b: Kitchen }
  roles: RoleCard[]
  lot: InventoryLotSample
  demand: MenuItemRef
  temperature_constraint: TemperatureConstraint
  /** Which numbers are made up for the demo, so the UI can mark them. */
  illustrative: string[]
  sources: SourceCitation[]
  paths: ScenarioPath[]
}
