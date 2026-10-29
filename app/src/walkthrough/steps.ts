import type { ScenarioPathId } from '@/data/scenario'
import type { Seat } from './roles'

export type StageId = 1 | 2 | 3

/** The pitch deck's three stages (docs/deck/README.md, slide 3). Copy is verbatim from the deck. */
export interface WalkthroughStage {
  id: StageId
  /** Two-digit marker as the deck prints it. */
  number: '01' | '02' | '03'
  title: string
  subtitle: string
}

export const STAGES: WalkthroughStage[] = [
  { id: 1, number: '01', title: 'Review availability', subtitle: 'Confirm what is unallocated and still usable' },
  { id: 2, number: '02', title: 'Request a transfer', subtitle: 'Kitchen B reviews the quantity and timing' },
  { id: 3, number: '03', title: 'Agree on the handoff', subtitle: 'Identify who approves and coordinates pickup' },
]

export interface WalkthroughStep {
  /** Route segment: /walkthrough/<id>. */
  id: string
  label: string
  stage: StageId
  seat: Seat
  path: ScenarioPathId
  /** Playable events applied when the step opens. */
  from: number
  /** Playable events applied when the step's actions are done. */
  to: number
  /** One sentence the presenter says, from docs/demo-script.md. */
  presenterLine: string
  /** One sentence on what the audience should see, from docs/demo-script.md. */
  audienceSees: string
  /** Dwell time in the hands-free presenter loop. */
  autoplayMs: number
  /** Step 6 runs the next Eatec exports (system only) when it opens. */
  runsImports?: boolean
  /** Shown under SIMULATED_LABEL: the demo plays these out; no real handoff or export happens. */
  simulated?: boolean
}

/** Label for steps flagged `simulated` (docs/design-spec.md). */
export const SIMULATED_LABEL = 'Simulated follow-through'

/** Label for the system import that sets Verified in step 6 (docs/design-spec.md). */
export const SIMULATED_IMPORT_LABEL = 'Simulated next-morning Eatec export (sample)'

// Happy path playable events: import, mark extra, send offer, accept, pickup, handoff, receipt, use.
// Why stage 3 starts at step 4: the deck puts "coordinates pickup" in stage 3, and step 3 is Kitchen B's review.
export const STEPS: WalkthroughStep[] = [
  {
    id: '1',
    label: 'Mark the extra',
    stage: 1,
    seat: 'kitchen_a',
    path: 'happy',
    from: 1,
    to: 2,
    presenterLine:
      "Wednesday's Eatec export shows 10 pounds of spinach, 6 already on Thursday's lunch menu, so the cook marks the other 4 as extra, best by Friday.",
    audienceSees:
      'The lot card shows 10 lb on hand, 6 lb allocated to Baby Spinach at the Salad Bar, and 4 lb available, best by Friday, and the state changes to "Extra."',
    autoplayMs: 9000,
  },
  {
    id: '2',
    label: 'Send the offer',
    stage: 2,
    seat: 'kitchen_a',
    path: 'happy',
    from: 2,
    to: 3,
    presenterLine:
      "Café 3 has Nancy Silverton's Sauteed Spinach on Thursday's lunch menu, so the cook sends Café 3 a transfer offer for the 4 pounds, there by 9 a.m. Thursday.",
    audienceSees:
      'Second Serve suggests Café 3 from its real menu item, the offer shows 4 lb, the dish, the needed-by time and "41°F or colder," and the state changes to "Offer sent."',
    autoplayMs: 9000,
  },
  {
    id: '3',
    label: 'Accept or decline',
    stage: 2,
    seat: 'kitchen_b',
    path: 'happy',
    from: 3,
    to: 4,
    presenterLine:
      'The Café 3 chef reviews the quantity and timing and says yes, and only now does the app call it planned.',
    audienceSees: 'After Accept, a grey "Planned: 4 lb" chip appears while Reported and Verified stay at 0 lb.',
    autoplayMs: 7000,
  },
  {
    id: '4',
    label: 'Set the pickup',
    stage: 3,
    seat: 'coordinator',
    path: 'happy',
    from: 4,
    to: 5,
    presenterLine: "The coordinator only sets the pickup: 2 to 3 p.m. Wednesday, Café 3's prep cook, insulated tote.",
    audienceSees:
      'The pickup window, runner and carrier are set, the state changes to "Pickup set," and the coordinator has no Accept or Verify button.',
    autoplayMs: 7000,
  },
  {
    id: '5',
    label: 'Hand off and use',
    stage: 3,
    seat: 'kitchen_a',
    path: 'happy',
    from: 5,
    to: 8,
    presenterLine:
      'At handoff both people sign for 4 pounds at 38°F, it arrives at 39°F, and Café 3 records using it at Thursday lunch.',
    audienceSees:
      'Handoff shows 4.0 lb, 38°F and two signatures, receipt shows 39°F under the 41°F limit, and "Reported: 4 lb" fills, labelled self-reported, while Verified stays at 0 lb.',
    autoplayMs: 10000,
    simulated: true,
  },
  {
    id: '6',
    label: 'Next morning: verify',
    stage: 3,
    seat: 'coordinator',
    path: 'happy',
    from: 8,
    to: 8,
    runsImports: true,
    presenterLine:
      'Nobody can click verified; it turns green only when the next Eatec exports show the transfer posted, the dish produced, and no waste entry.',
    audienceSees:
      'Under "Simulated next-morning Eatec export (sample)", three checks turn green one by one, and the counters read Planned 4 lb, Reported 4 lb, Verified 4 lb, side by side and never summed.',
    autoplayMs: 10000,
    simulated: true,
  },
]

/** Off-script branches from the demo-script appendix and presenter notes. Both replace stage 2's Kitchen B review. */
export const VARIANTS: WalkthroughStep[] = [
  {
    id: 'decline',
    label: 'Decline variant',
    stage: 2,
    seat: 'kitchen_b',
    path: 'happy',
    from: 3,
    to: 4,
    presenterLine:
      "This time Café 3's own delivery already covers Thursday's lunch, so the chef declines and picks a reason.",
    audienceSees:
      'Decline asks for a reason, "Already stocked" is chosen, the transfer reads "Declined," and the 4 lb stays marked extra while all three counters stay at 0 lb.',
    autoplayMs: 8000,
  },
  {
    id: 'expired',
    label: 'Café 3 never answers',
    stage: 2,
    seat: 'kitchen_a',
    path: 'happy',
    from: 3,
    to: 6,
    presenterLine:
      'The offer closes at 08:00 Thursday with no answer; nothing was thrown out, and the cook puts the 4 pounds on the use-first list.',
    audienceSees:
      'The card reads "Offer closed. Nothing was thrown out," the 4 lb goes on the Crossroads use-first list, and no pounds are counted.',
    autoplayMs: 8000,
  },
]

export const stepById = (id: string | undefined) => [...STEPS, ...VARIANTS].find((s) => s.id === id)

export const stageById = (id: StageId) => STAGES.find((s) => s.id === id)
