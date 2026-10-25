# Judge 244: P2b, the Forecast lab page (`forecast_lab`)

Trading `story/p2b-forecast-lab` at e2a5791d (P2 builder 013xqaNTCbSBytKgqpfaYFqZ; claims: response 242). The
orchestrator sent 0d236b0d; the head moved to e2a5791d, which contains it (main merged, the claims renumbered, the
answer-day stop named), so I judged e2a5791d. Story W3 Part 1, build step 2. Lane 1. Judge D, 16 Oct 2026.

**FAIL: one should-fix.** The page is right; its year-end stop takes every other page down with it.

| Item | Result | Evidence |
|---|---|---|
| Built from the real sources, nothing re-scored | MET | G4's latest report on or before the session, used as is, and the committed live_v2 and ai_v1 records. On the real 16 Oct data: Book 1 has 2 pack days (1 counted, 1 late); Books 2 and 3 have 2 pack days each (0 counted, 1 missing, 1 late); the baselines' coverage is null (G4 measures none). This matches the claims. |
| The yardstick is Book 1 (PROTOCOL.md section 8) | MET | Every v3 question has `primary_baseline` book1_rules, and its comparisons are book2_hybrid and book3_ai against book1_rules, both `not_tested` today. Both registered comparisons are listed, the not-yet-possible one too, as section 8 requires (judge 239's note). The report carries `confirmatory_allowed`, and the verdict is `before_review` while it is false. |
| Live only; v4 as a draft | MET | Scores come from `live_1500_proxy` only, and v4 is listed with no V question (test; a test fails once `FREEZE_v4.md` exists). |
| Today's values and AI statuses | MET (tests) | A recorded empty probability is left out. Late, pending, model_mismatch, breach and the unlisted-day rule are covered by tests on real and planted days. |
| Coverage adds up or stops named | MET | `FiguresNotComputed`, test. |
| Never sent | MET | The test covers three real days (reasons, versions, sessions). |
| Gates | MET | On e2a5791d: 6989 passed (`-n auto`, Slack token unset), ruff check and format clean, check_imports clean. A trial merge with main is clean, and then 6992 passed. |

## Finding (should-fix)

**From the 3 Dec 2026 publish, the whole market publication stops, not only the Forecast lab.** `SessionsAhead` raises
`FiguresNotComputed` when a question's answer day lies past NSE's calendar (31 Dec 2026). `market_run.py:117` turns
any `FiguresNotComputed` into `Stopped("F&O figures")`, so no page of the day is published: the weather, Home, the
chain, the stock pages and every other block.
- On the real calendar (my run): `SessionsAhead(cal)(2 Dec, 20)` is 31 Dec, while `(3 Dec, 20)` raises; and `(16 Dec,
  10)` is 31 Dec, while `(17 Dec, 10)` raises. Q1 to Q3 are 20-session questions, so every session from 3 Dec on stops
  the publish.
- The stop lasts until NSE's 2027 holiday circular is added. NSE usually publishes it in December (reasoning, the
  builder's and mine), so it is likely to cost one to several weeks of every dashboard page.
- The claims name this and propose two fixes for later: the per-page hold (its own story, next) and a nullable
  `answer_on`. Merging P2b before either lands sets a known date when all publishing stops. A new page must not be
  able to stop the pages that already work.

**Fix (either, before merge):** (a) the Forecast lab alone is held when its answer day is unknown and every other
page publishes (the per-page hold for this one cause, with its alert); or (b) the screens lead lets `answer_on` be
null ("not known yet") in the contract, and P2b sends null past the calendar. Either way, add a test on the real
calendar: a publish on 3 Dec 2026 builds every other page.

## Notes

- O8b's horizon line (judge 240) fires on 17 Nov, 16 days before this would stop. Name that consequence in O8b's line
  only if (a) or (b) is not done.
- The question-level `n_scored` is Book 1's; the claims say so.

## Addendum 1: head 8ea526cb (rebased on P11; the root fix)

**PASS.** The should-fix is fixed at its root, with no hold needed. `SessionsAhead` walks one session at a time and
returns `None` when the answer day lies past NSE's calendar. `today.answer_on` is then null, which is contract
2.13.0's "not known yet". Nothing raises, so nothing stops or holds.
- **On the real calendar (my run):** (2 Dec, 20) gives 31 Dec; (3 Dec, 20) gives None; (16 Dec, 10) gives 31 Dec;
  (17 Dec, 10) gives None. The builder's test moves the 15 Oct records to 3 Dec 2026, and the page validates against
  the pinned 2.13.0, with Q1, Q2, Q3 and Q5 null and Q4 on 17 Dec.
- **Gates on 8ea526cb:** 7205 passed (`-n auto`, Slack token unset), ruff and check_imports clean, and `market
  contract-check` gives 2.13.0 "same as the dashboard's". P11 (1082b285) is on main, and a trial merge with main is
  clean (WORK_REGISTER auto-merged).

**Note:** any `CalendarError` in the walk now reads as "not known yet". A calendar broken inside its covered range
would show as unknown answer days on this page, but the same calendar stops the 3 pm recorder, the desk and O8 loudly
(O8c), so it cannot go unseen.
