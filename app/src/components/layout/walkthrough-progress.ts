import { STAGES, STEPS, VARIANTS, type WalkthroughStage, type WalkthroughStep } from '@/walkthrough/steps'

type StepLike = WalkthroughStep

export const stepStage = (s: StepLike): number => s.stage
export const isSimulated = (s: StepLike): boolean => s.simulated === true

export interface WalkthroughPosition {
  step: StepLike | undefined
  stage: WalkthroughStage | undefined
  /** 1-based index into the main STEPS path; null on a variant. */
  stepNumber: number | null
  total: number
  isVariant: boolean
  /** 0–100, lime progress bar. */
  percent: number
}

export function walkthroughPosition(pathname: string): WalkthroughPosition {
  const id = pathname.match(/^\/walkthrough\/([^/]+)/)?.[1]
  const mainIdx = STEPS.findIndex((s) => s.id === id)
  const variant = VARIANTS.find((s) => s.id === id)
  const step: StepLike | undefined = mainIdx >= 0 ? STEPS[mainIdx] : variant
  const stage = step ? STAGES.find((st) => st.id === stepStage(step)) : undefined
  const total = STEPS.length
  // Why: a variant replaces a stage-2 step, so show progress as of that stage's last main step.
  const fallbackIdx = step ? STEPS.findLastIndex((s) => stepStage(s) <= stepStage(step)) : -1
  const progressIdx = mainIdx >= 0 ? mainIdx : fallbackIdx
  return {
    step,
    stage,
    stepNumber: mainIdx >= 0 ? mainIdx + 1 : null,
    total,
    isVariant: Boolean(variant),
    percent: progressIdx >= 0 ? Math.round(((progressIdx + 1) / total) * 100) : 0,
  }
}

export const stepsForStage = (stageId: number) => STEPS.filter((s) => stepStage(s) === stageId)
