# Walkthrough scenario API

Source: `app/src/walkthrough/useScenario.ts`. Participant (`/walkthrough/:step`) and presenter (`/present`) both drive the same `ScenarioProvider`; there is no parallel presenter state.

## `useScenarioContext()` — state and actions

| name | type | use |
|---|---|---|
| `seat` | `Seat` | current role on screen (`kitchen_a`, `kitchen_b`, `coordinator`) |
| `handoffTo(seat)` | action | guided role handoff. Call from the "Notification sent to Kitchen B" card. The presenter loop calls it too. |
| `setSeat(seat)` | action | free-roam header switcher only |
| `apply(pathId, event)` | action | apply a next option. Idempotent by `event.seq`: double taps and replays never duplicate. |
| `importRecords()` | action | system only: appends held `records_imported` events. Idempotent. |
| `restart()` | action | resets events and role together and bumps `runId`. Callers navigate to step 1 themselves. |
| `rewind(pathId, count)` | action | participant Back: keeps the first `count` events the participant applied |
| `seek(pathId, count)` | action | presenter only (arrow keys): replaces events with fixture events |
| `runId` | number | bumps on every restart; key per-step init on `${runId}:${step.id}` |
| `progress` | `{ pathId, events }` | raw state; prefer `useTransfer()` |

## `useTransfer()` — derived selectors

Existing: `scenario, path, applied, imports, log, last, state, options, forSeat(seat), systemOptions, planned, completed, verified, expectedChecks, done`.

New:
- `nextSeat: Seat | null`: who acts next on the current path. Null when only the system can act or the transfer is over.
- `handoff: { to: Seat } | null`: non-null when the current seat has nothing to do and `nextSeat` is someone else. Render the handoff card when it is set:

```tsx
const t = useTransfer()
const { handoffTo } = useScenarioContext()
if (t.handoff) return <HandoffCard to={t.handoff.to} onTap={() => handoffTo(t.handoff.to)} />
```

## Step progression helpers

- `isStepComplete(step, t)`: true once the step's required action is done. WalkthroughPage gates Next on it.
- `stepEntry(step, t)`: rewind target when opening a step, or null when the step isn't reached yet. Never seeks forward.
- `resumeStep(t)`: first step whose action is still open. Unreached deep links redirect here.

## Participant rules (WalkthroughPage)

- Opening a step never applies events. Back rewinds to that step's completed state.
- The walkthrough no longer auto-switches the role on step open. The stage shows the handoff card from `t.handoff`, and that tap is the role switch.
- Restart calls `restart()` and navigates to `/walkthrough/1`.
- `?autoplay=1` on `/walkthrough/*` redirects to `/present`.
- Layout: StageHeader, RolePill, StepHero on step 1, TransferStage, TierCounters, VerificationChecks, EventLog in one column capped at 960px, then ActionBar last. ActionBar's primary is disabled until `isStepComplete`.

## Presenter (`/present`, `usePresenterPlayback`)

- Plays steps 1 to 6 using each step's `autoplayMs`. Each beat is one of `handoffTo`, `apply`, or `importRecords`, the same calls a participant makes.
- `/present` is nested under the AppShell route, which renders it chromeless.
- Shows a 6 s end card, then `restart()` and loops.
- Space toggles pause and resume. Left and right arrows step, which seeks and pauses. Any other key or tap outside the caption bar pauses.
- `?speed=N` divides every delay, for tests.
- The root element carries `data-loop`, `data-step`, `data-phase`, `data-paused` and `data-event-seqs` for headless checks.
