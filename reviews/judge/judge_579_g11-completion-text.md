# Judge 579: G11 completion, stage 1 text, story/g11-ai-books-v4 at acacf5c7f (judge J, round 1 of 2)

**FAIL**, lane 1 (rule 1, text first): 7 should-fix, 2 minor. Diff: only `docs/stories/G-forecasts.md` (+182) on 312eb791.

## Criteria (the builder's five findings and the text)
| Item | Verdict | My evidence |
|---|---|---|
| F1 prompt defines only V6a, V6b | MET | branch `fno/ai/versions.py:23` `V4_AI_QUESTIONS = (V6_BIG_MOVE_1S, V6_BIG_MOVE_5S)`; rules folders `v1_close_blend`, `v2_close_blend`, `v6_ewma_t4`, `v7_vix_vs_mean20` exist in `research/forecasts/v4/` |
| F2 ~24 min reveal wait, 10 min timeout | MET | `book.py:94-97` sleeps the whole wait in one call; `book2/3_*_v2.md:64` "Bash timeout of 600000 ms"; the code still waits to 15:15:10 (`timing.py:13`), so C5 is also needed |
| F3 BG1 stop not read before a fire | MET | `grep stop_ai_roles fno`: written `budget/signal.py:53`, read only `learning/writer.py:49`; nothing in `fno/ai/fire.py`, `v4_fire.py` |
| F4 cost estimates | PARTLY | 6 runs 4.21-4.51, mean 4.36 (main's `accounting/ai_usage.csv`); 22x2x(20-30) = 880-1,320, 22x2x(5-8) = 220-352 right; meter "200.0%; level unknown" reproduced (now 29.82 min). See m2 |
| F5 7 of 14 on time | MET | `scores/2026-10-24.json` `unscored_ai_days`: 3 `no_submission`, 4 `late` over 7 sessions x 2 books (20 Oct holiday) |
| Criteria testable and complete | PARTLY | S1-S7, m1 |
| Gap list covers the protocol | PARTLY | S2, S3, S4, S5 |
| C15 "not a money piece" | MET (some evidence) | no module in `fno/desk`, `books`, `book3`, `risk`, `factory`, `playbook` reads `research/forecasts/v4` or imports `fno.ai.v4_*`; the test as written is weak (S6) |
| D1-D5 | PARTLY | D1, D4 match G10 completion's answers; D2, D3 do not (S1); D5 misses the freeze-order trap (S2) |
| Doc-reading tests | MET | 698 passed, 16 xfailed (branch head) |

## Findings
**S1 (should fix) D2/D3 contradict G10's published answers.** `story/g10-completion` c876ede53, its "pack's interface for G7b and G11" table: the day label is the Drive release record read through `ReleasedPacks.release(day)`; `research/data/v4_days/` is retired; the `paths:` filter is `receipts/data/v4/days/**`; `v4-fire.yml` is held on `story/g10-part2b-pack` (also on `-release`). Fix: D2, D3, C11, C16 read the label via `ReleasedPacks` and name that path.

**S2 (should fix) The freeze order can refuse G11's rows and break every v4 score.** `slot_file.py:62-69` refuses `effective_start <= frozen_on` and `effective_start > first_eligible`, and `registered()` raises for the whole file. So rows written before `FREEZE_v4.md` with a start on or before its day, or a go-live session after the slots' first eligible session (V6/V7 base rate is eligible on day one), stop G8's reads. Fix: D5 and C13 state the required order (go-live no later than the first eligible session after the freeze), what G11 does in each order, and a test for both.

**S3 (should fix) C3's baseline and w.** (a) V1's primary switches one way to HAR intraday (`eligibility.primary_baseline`, protocol 3.2); the branch uses static `PRIMARY_BASELINE[question]` (`v4_book_inputs.py`); C3 must name the switch. (b) V2's w cannot be "measured before code": no premium-adjusted back-fill exists (`research/forecasts/v4/` has none). If w sits in hashed prompt v2 and is set after merge, it becomes v3, never a member (5.6). Fix: per-question w, with V2's path stated before merge.

**S4 (should fix) Measures of the point questions.** V2 is scored on `close_proxy` for all of v4 and V1 on intraday `RV_s` with the overnight return (protocol 1.1). Item 3 gives both intraday `RV_s`. Fix: C2 and the prompt name each question's measure; C4 gives V2 close-proxy history and tests it.

**S5 (should fix) Earlier criterion 6 dropped.** No C tests "N days awaiting audit" (pending audit: no row). A `CommitmentTimeUnknown` (`commitment.py:16`) has no row either. Fix: one criterion with that output and the retry.

**S6 (should fix) C15 is not testable as written.** `fno/ai_trading/` does not exist (F1t's plan) and "any decider" is no set. Fix: list the packages, check imports and the path string `research/forecasts/v4/book`. Note: O1 stages all of `research/forecasts/v4/` (`daily/wiring.py:18,119-121`).

**S7 (should fix) C8 vs "AI forecasters last".** BG-budget.md:46-48 and design 7.6 stop forecasters last, but the signal is one flag (`signal.py:53`), so C8 stops them with everyone. A missing signal file has no case. Fix: say how "last" holds or name it a BG1 or owner ruling; add the empty case.

**m1 (minor)** C5, C7, C9, C10, C13-C17 lack the good/bad/boundary/empty set the header promises (quality rule 5).
**m2 (minor)** Stale facts: `fno/constants.py` is 349 on main and 350 on the branch, not 346. The 4.2-4.5 minutes run from about 15:11 to 15:15:13-40 (`ai_v1/timing/`), so they include the reveal wait. 2,712 commits, not 2,717. "0.5-5 min" not reproduced (rewritten committer dates).

## Plants
0 (text round, nothing to run). Planned plants in C1-C14 noted for the code round.

## Notes
- C8 enforces a cost cap that can only stop AI runs, never enlarge a trade. One judge is fine; the orchestrator decides.
- C6's re-run loop costs model turns as well as wall-clock minutes; C17 should report both.

## Addendum 1: the delta to a3de25b66 (still round 1, the orchestrator's re-point)
One Markdown commit on acacf5c7f (D1-D3, C16; +16 -9). Checked against `story/g10-completion` at e5626aabf (contains
2f508ae15), its "pack's interface" rows G11 D1-D3: module names, Drive release records via `ReleasedPacks.release(day)`,
`research/data/v4_days/` retired, `paths:` filter `receipts/data/v4/days/**` and the catch-up rule match word for word.
**S1 closed.** The new rule that a day with no release record is neither collected nor written is consistent with the
look's reconciliation, which refuses until the catch-up record lands. S2-S7, m1 and m2 are untouched by the delta.
**The verdict stays FAIL** at a3de25b66.

## Addendum 2: round 2 (the last), story/g11-ai-books-v4 at 0f8380cbf
**PASS** (text), lane 1. One Markdown commit on a3de25b66. Every finding was re-checked with my own evidence:
- S2 closed: C13 sets the order (freeze and rules rows, then G11's rows, then the go-live). Start is the first session after the freeze, so `slot_file.py:62-69` passes. A command refuses before the freeze, without rules rows, or from 09:15 of the start day. A late go-live gives honest `not_fired` rows. Both sides are tested.
- S3 closed: the primary comes from `eligibility.primary_baseline`, so V1's switch is one way. The span covers the rules value and the baseline, widened by w (0.10 absolute, 0.25 relative), fixed before merge. V2 needs no measured w. Item 4's numbers reproduced exactly from main's back-fill: within +-0.10 on 94.4%, 55.5% and 96.7% of 1,912/1,908/1,908 days; p95 gap 0.113/0.438/0.091.
- S4 closed: C2 names the measure per question (V1 intraday with the overnight return, V2 `close_proxy`) and adds a unit-error bound. C4 gives V2 its close-proxy history.
- S5 closed: C19. `v4_settle.py:45-46` already prints "N day(s) awaiting audit". An unknown receipt time writes no row and is retried.
- S6 closed: C15 names six packages and checks imports and path strings. None of the six imports `fno.ai` or holds those strings today (grep).
- S7 closed as a text question. C8 states both choices plainly as "reasoning only", for the owner:
  - (a) "Last" means stop only on `stop` and the books' own minutes at or above the cap.
  - (b) A missing signal fires (fail open) and posts one line.
  - Each is a single change: (a) one extra condition, whose removal is the plant; (b) one branch.
  - The owner's answer is not mine to rule on.
- m1 closed: every C1-C17 and C19 has G/B/Bd/E. C14 and C16 have no planned plant; that is fine, since the judge plants its own.
- m2 closed. Fire-to-receipt 35-309 s reproduced from the fire logs and audit receipts (11 book-days 15-23 Oct; the text's 9 are 16-23 Oct). Cost arithmetic checked: 22 x 2 x 25-35 = 1,100-1,540; 22 x 2 x 1-8 = 44-352.

Notes: the commit count moves with main (2,768 when I checked). For the code round, C8's "books' own minutes" must use BG1's ledger and the same cap as the meter, never a copy.
