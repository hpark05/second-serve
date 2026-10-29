import type { RecommendationKind } from './bundle'

/**
 * Every action moves planned -> completed -> verified. Only the last step needs evidence from outside the app
 * (an inventory count, a receiving log), so UI clicks can set planned and completed but never verified.
 */
export type ActionStatus = 'planned' | 'completed' | 'verified'
export type ClickableStatus = Exclude<ActionStatus, 'verified'>

export const STATUS_LABEL: Record<ActionStatus, string> = {
  planned: 'Planned',
  completed: 'Completed',
  verified: 'Verified',
}

/** What evidence would move a completed action to verified. */
export const VERIFIED_BY: Record<RecommendationKind, string> = {
  use_first: 'next Eatec count shows the lot drawn down',
  adjust_prep: 'next production record shows the lower prep count',
  buy_less: 'next purchase order shows the reduced quantity',
  transfer: 'next Eatec count at both kitchens and the receiving log',
  recover: 'recovery partner pickup receipt with weight',
}
