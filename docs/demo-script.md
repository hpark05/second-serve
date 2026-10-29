# Second Serve demo script: one spinach transfer

One transfer, start to finish, so dining staff can judge whether it fits their day. It follows the pitch deck's fictional scenario and its three stages (`docs/deck/README.md`). Data comes from `app/public/data/scenario-spinach.json`, the step copy from `app/src/walkthrough/steps.ts`, and the rules from `docs/transfer-flow.md`. If this script and `steps.ts` disagree, `steps.ts` wins, because the app reads it.

**The scenario.** Today is Wednesday. Kitchen A is Crossroads, a dining hall. It has 10 lb of spinach on hand. 6 lb are allocated to Thursday's lunch menu, and 4 lb are unallocated and best by Friday. Kitchen B is Café 3, a campus cafe. It has Nancy Silverton's Sauteed Spinach on Thursday's lunch menu and could use the 4 lb.

**Target: under 3 minutes.** Allow 15 seconds to open, about 25 seconds per step, and 15 seconds to close. That totals 2 minutes 40 seconds. The hands-free loop uses each step's `autoplayMs` instead, 52 seconds in all.

**Open (15 s).** Say: "This is a fictional scenario with sample data only, built on real Cal Dining menu items. Kitchen A has 10 pounds of spinach, 6 are planned for Thursday's menu, and Kitchen B could use the other 4." The audience should see the banner "Fictional scenario · Sample data only" and the provenance line "Eatec export, today 06:00."

## 01 Review availability: confirm what is unallocated and still usable

| # | Role on screen | Presenter says (one sentence) | Audience should see |
|---|---|---|---|
| 1 | **Crossroads cook** | "Wednesday's Eatec export shows 10 pounds of spinach, 6 already on Thursday's lunch menu, so the cook marks the other 4 as extra, best by Friday." | The lot card shows 10 lb on hand, 6 lb allocated to Baby Spinach at the Salad Bar, and 4 lb available. Best by Friday. Walk-in 38°F. The state changes to "Extra." |

## 02 Request a transfer: Kitchen B reviews the quantity and timing

| # | Role on screen | Presenter says (one sentence) | Audience should see |
|---|---|---|---|
| 2 | **Crossroads cook** | "Café 3 has Nancy Silverton's Sauteed Spinach on Thursday's lunch menu, so the cook sends Café 3 a transfer offer for the 4 pounds, there by 9 a.m. Thursday." | Second Serve suggests Café 3 from the real menu item. The offer shows 4 lb, the menu item, the needed-by time, and the cold-holding line "41°F or colder." After **Request transfer**, the state changes to "Offer sent." |
| 3 | Switch to **Café 3 chef** | "The Café 3 chef reviews the quantity and timing and says yes, and only now does the app call it planned." | The offer appears with an Accept and a Decline button. After **Accept**, a grey "Planned: 4 lb" chip appears. The Reported and Verified counters stay at 0 lb. |

## 03 Agree on the handoff: identify who approves and coordinates pickup

Steps 5 and 6 carry the label "Simulated follow-through." The demo plays them out; no real handoff or Eatec export happens.

| # | Role on screen | Presenter says (one sentence) | Audience should see |
|---|---|---|---|
| 4 | Switch to **Coordinator** | "The coordinator only sets the pickup: 2 to 3 p.m. Wednesday, Café 3's prep cook, insulated tote." | The pickup window, runner and carrier are set. The state changes to "Pickup set." The coordinator has no Accept or Verify button. |
| 5 | Switch to **Crossroads cook**, then **Café 3 chef** | "At handoff both people sign for 4 pounds at 38°F, it arrives at 39°F, and Café 3 records using it at Thursday lunch." | Handoff shows 4.0 lb, 38°F and two signatures. Receipt shows 39°F, under the 41°F limit. Use is recorded. The "Reported: 4 lb" counter fills, labelled as self-reported. Verified stays at 0 lb. |
| 6 | **System**, Thursday and Friday mornings, simulated | "Nobody can click verified; it turns green only when the next Eatec exports show the transfer posted, the dish produced, and no waste entry." | Under "Simulated next-morning Eatec export (sample)," three checks turn green one by one: transfer posted, production recorded, no waste entry. The counters read Planned 4 lb, Reported 4 lb, Verified 4 lb, side by side and never summed. |

**Close (15 s).** Say: "Three numbers, kept apart, and only the last one counts as saved. Try the workflow on the iPad and tell us what is missing." Leave the vocabulary table from `docs/transfer-flow.md` on screen as the question for staff.

## Presenter notes

- Roles change through the "Notification sent to …" cards inside the walkthrough (tap "View as …"). Every switch should show the role name large enough to read from the back of the room.
- Say "sample" once at the start and leave the badge visible. Do not call any number in this scenario real.
- If asked about the 41°F and 45°F limits, they come from CalCode §113996. Berkeley EH&S lists spinach as a cut leafy green.
- If asked "what if Café 3 never answers?", show the expired path. The offer closes at 08:00 Thursday, and the card reads "Offer closed. Nothing was thrown out." The Crossroads cook puts the 4 lb on the use-first list.
- If asked "shouldn't Café 3 ask first?", say yes, that is how Eatec requisitions work, and the direction is an open question for the pilot.

## Appendix: decline variant (about 1 minute)

Run steps 1 and 2, then these instead of steps 3 to 6. Both rows replace stage 02's review by Kitchen B.

| # | Role on screen | Presenter says | Audience should see |
|---|---|---|---|
| 3′ | **Café 3 chef** | "This time Café 3's own delivery already covers Thursday's lunch, so the chef declines and picks a reason." | Decline asks for a reason, and "Already stocked" is chosen. The transfer reads "Declined." The 4 lb stays marked extra, so Crossroads can offer it to another kitchen. |
| 4′ | Any role | "Nothing was planned, so nothing is counted." | Planned, Reported and Verified all stay at 0 lb. The activity log shows the offer and the decline with its reason. |

The point for staff is that declining takes one tap and a reason. It never counts against either kitchen.
