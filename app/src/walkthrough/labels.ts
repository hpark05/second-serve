import type {
  ActorRole,
  DeclineReason,
  Disposition,
  TransferScenario,
  TransferState,
  VerificationCheck,
} from '@/data/scenario'

/** UI labels from docs/transfer-flow.md. `expired` reads "Offer closed" so staff don't hear "thrown out". */
export const STATE_LABEL: Record<TransferState, string> = {
  available: 'Extra',
  requested: 'Offer sent',
  accepted: 'Accepted',
  declined: 'Declined',
  awaiting_pickup: 'Pickup set',
  picked_up: 'Picked up',
  used: 'Used',
  expired: 'Offer closed',
}

export const STATE_TONE: Record<TransferState, 'good' | 'first' | 'transfer' | 'muted' | 'expired'> = {
  available: 'first',
  requested: 'transfer',
  accepted: 'transfer',
  declined: 'muted',
  awaiting_pickup: 'transfer',
  picked_up: 'good',
  used: 'good',
  expired: 'muted',
}

export const DECLINE_REASON_LABEL: Record<DeclineReason, string> = {
  already_stocked: 'Already stocked',
  cannot_meet_time: "Can't make the time",
  no_cold_storage: 'No cold storage',
  quality_concern: 'Quality concern',
  other: 'Other',
}

export const DISPOSITION_LABEL: Record<Disposition, string> = {
  use_first_here: 'Use first here',
  donate: 'Donate',
  compost: 'Compost',
  landfill: 'Landfill',
}

export const CHECK_LABEL: Record<VerificationCheck['check'], { title: string; source: string }> = {
  transfer_posted: {
    title: 'Transfer posted',
    source: 'Eatec transfer from Kitchen A to Kitchen B, posted on the handoff day, within 0.25 lb',
  },
  production_recorded: {
    title: 'Production recorded',
    source: "Kitchen B's Eatec production record shows the dish made, and its on-hand stock fell by the qty",
  },
  no_waste_entry: {
    title: 'No waste entry',
    source: 'No Eatec waste entry for this lot at either kitchen through the day of use',
  },
}

export function actorTitle(s: TransferScenario, role: ActorRole): string {
  return s.roles.find((r) => r.role === role)?.title ?? role
}
