# Second Serve — design spec for the Thursday demo build

Source: pitch deck (docs/deck/README.md) + Codex Astra review 2026-10-28 + advisor feedback. Every swarm agent follows this. Product name: Second Serve.

## Direction
A calmer, product-grade cousin of the deck. Keep its lime, geometric headings, white cards, whitespace. Drop decoration (doodles, blobs) inside the product so staff can follow the decision. Notion-level restraint: one primary action per screen, nothing competes with it.

## Tokens (app/src/index.css, Tailwind v4 @theme)
| token | value | use |
|---|---|---|
| --bg | #FAFBF9 | page background |
| --card | #FFFFFF | cards, panels |
| --ink | #171C17 | headings, body |
| --muted | #596459 | labels, secondary |
| --border | #E2E9DF | 1px borders everywhere |
| --lime | #7ED957 | primary button fill (black text), stage accents, progress |
| --lime-soft | #EAF8E2 | selected row, chip bg |
| --green | #285C35 | links, focus ring, verified state |
| --amber | #C7731A / #FDF1E3 | planned / needs-review |
| --red | #C4452C / #FDE7E2 | declined / expiring |

No gradients. No card shadows. One subtle shadow (0 8px 24px rgba(23,28,23,.08)) reserved for overlays and the presenter caption bar.

## Type
- Headings: Poppins 600/700 (self-host via @fontsource/poppins). Page title 28/32, card title 18, stage label 12 uppercase tracking .08em.
- Body: Inter 400/500, 16px body, 14px labels, 13px meta. Line height 1.5.
- Big scenario numbers (10 lb, 4 lb): Poppins 700, 40–56px, lime or ink. Unit in 14px muted.

## Shape & density
- Card radius 12px, controls 8px, chips 999px. Card padding 24px. Section gap 24px. Grid gap 16px.
- Touch: every interactive element ≥ 44px tall, ≥ 44px wide. Primary buttons 48px on walkthrough screens.
- Max content width 960px centered on walkthrough; sidebar collapses to a top stage bar under 1024px (iPad portrait).

## Walkthrough structure (deck's 3 stages)
| stage | title | subtitle | steps |
|---|---|---|---|
| 01 | Review availability | Confirm what is unallocated and still usable | 1 |
| 02 | Request a transfer | Kitchen B reviews the quantity and timing | 2–3 |
| 03 | Agree on the handoff | Identify who approves and coordinates pickup | 4–6 (5–6 labeled "Simulated follow-through") |

Stage + step always visible (e.g. "02 Request a transfer · Step 3 of 6"). Progress bar in lime.

## Scenario copy (canonical)
Kitchen A · Crossroads · Dining hall: 10 lb spinach on hand. 6 lb planned for Thursday's lunch. 4 lb available, best by Friday. Source: Eatec export, Wednesday 06:00 (today = Wednesday; use `today_weekday` from the fixture to render weekday names instead of "Tomorrow"/"+2d" on walkthrough screens).
Kitchen B · Café 3 · Campus cafe: could use 4 lb for tomorrow's real menu item.
Banner on every walkthrough screen: "Fictional scenario · Sample data only" (small, muted, never hidden).

## Honesty rules (advisor)
- Planned / Completed (self-reported) / Verified are separate tiles, never summed.
- Verified only via the simulated Eatec import event; label it "Simulated next-morning Eatec export (sample)".
- Every derived number outside the walkthrough carries an "Illustrative" chip linking to /sources.
- Expired state shows "Offer closed".

## Presenter mode (hands-free laptop)
- Route `/present` (also `?autoplay=1`): plays steps 1→6 with per-step dwell from steps.ts `autoplayMs`, performs the clicks and role switches itself, shows a bottom caption bar with `presenterLine`, pauses on any tap/key (space = pause/resume, ← → = step), 6s end card, loops cleanly with no duplicated events. Hide the app chrome (sidebar, header) in this mode.

## Participant mode (iPad self-serve)
- Next is gated: a step's required action must be taken before Next enables. Back is allowed. Restart resets route, role and events together.
- Role changes are guided: when a step needs Kitchen B, show a full-width "Notification sent to Kitchen B · View as Kitchen B →" card that switches the role on tap. No manual role switcher needed inside the walkthrough (keep it in the header for the free-roam app).
- Activity log collapsed by default under a "History (n)" toggle; sticky bottom action bar.

## Anti-slop
No emoji, no gradient text, no glassmorphism, no stock illustration inside the product. Lime is for actions and progress only, not backgrounds. Whitespace does the work.

## Token aliases (app/src/index.css)
Old names still compile so pages keep working mid-migration. Prefer the spec name in new code.

| old name / class | now resolves to | note |
|---|---|---|
| `--panel`, `bg-panel` | `--card` #FFFFFF | |
| `--line` | `--border` #E2E9DF | |
| `--muted-ink`, `text-muted-foreground` | spec `--muted` #596459 | shadcn keeps `--muted` / `bg-muted` as the neutral surface #F1F4F0 |
| `--green`, `text-green`, `bg-green` | #285C35 (was #1E6B4A) | links, focus ring, verified |
| `--green-2`, `bg-green-2` | `--green` | |
| `--green-soft`, `--green-chip`, `bg-green-chip` | `--lime-soft` #EAF8E2 | |
| `--amber-line`, `border-amber-line` | `--amber-soft` | |
| `--blue*`, `--purple*` (+ `-soft`, `-line`) | `--muted-ink` / `--surface-muted` / `--border` | not in spec palette; neutralized, remove usages over time |
| `--shadow-card`, `shadow-card` | `none` | spec: no card shadows. Overlays use `shadow-overlay` |
| `--primary`, `bg-primary` | `--lime` with black `text-primary-foreground` | was forest green with white text |
| `font-heading` | Poppins 600/700 | was Georgia |
| `font-sans` | Inter 400/500/600 | was Inter Variable |

New utilities: `bg-lime`, `bg-lime-soft`, `text-ink`, `text-muted-ink`, `bg-red-soft`, `rounded-control` (8px), `rounded-card` (12px), `text-page-title` / `text-card-title` / `text-stage` / `text-body` / `text-label` / `text-meta` / `text-stat`, and `page-title`, `card-title`, `stage-label`, `stat-number` composite classes.
Primitives: Button sizes are all >= 44px; `size="walkthrough"` (and `lg`) is 48px. Badge variants `sample`, `illustrative`, `planned`, `completed`, `verified`, `declined`.
