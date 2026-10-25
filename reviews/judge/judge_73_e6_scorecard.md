# Judge 73: story E6, strategy scorecard and pause rules (branch, before merge)

Date: 14 Oct 2026 (UTC). Branch `story/e6-scorecard` at c264ccd. Claims: `reviews/claude/response_75_e6-scorecard.md`.
Story: `docs/stories/E-paper-desk.md` E6. Read together with judge 74 (D2 start-of-day), which this branch collides
with.

## Verdict: FAIL, four must-fixes

The scorecard numbers are right; I recomputed them from the records. The pause rule has three defects:
- an old loss re-pauses a version for ever, so the owner can never re-approve it;
- a loss from a version's shadow test pauses it the moment it is approved;
- the cap above C2's Rs 10,000 that the orchestrator asked to refuse is not refused.

And once D2's start-of-day branch is merged, the pause no longer stops the same day's trade (judge 74).

## Gates (my runs on c264ccd; `python -B`, `__pycache__` cleared)

- Full suite: 2,310 passed.
- `ruff check` and imports: clean. `ruff format --check`: 507 files already formatted.
- New files are under 350 lines.

## The story's own check: one scorecard number recomputed from the records

I made one Book 1 trade with the builder's history writer: credit 50, debit 150, 65 units, touch 0.75 from each mid.
Then I summed the cash flows from `desk_fills.csv` myself: price times units, signed by side, minus `charges_rs`.

| Number | Mine | Scorecard |
|---|---|---|
| Net | Rs -6,609.66 | Rs -6,609.66 |
| Half-spread a unit, from the fill price against each fill's `quote_bid` and `quote_ask` | Rs 0.75 | Rs 0.75 |

**MET.**

## Per criterion

| # | Criterion | Check | Result |
|---|---|---|---|
| 1 | Catastrophic loss: `paused` at once, no new trades in any book, owner alerted | The cap edge works (exactly at the cap pauses, Rs 0.01 less does not), any account counts, one alert, a rerun adds nothing. My plants Q3 (Book 1's losses only), Q7 (pause dated tomorrow) and Q1 (shadow re-alerted daily) are caught. **But three defects (must-fix 1-3), and "no new trades in any book" is false once judge 74's branch merges (must-fix 4)** | **NOT MET** |
| 2 | Gate 3 months and 20 positions, only on review dates; open at marks, not counted; inconclusive never promoted | Tests pass; my plant Q4 (months not checked) is caught | MET |
| 3 | Execution costs equal a hand computation | Builder's hand test plus my recomputation above; plant Q8 (refused counted as not filled) is caught | MET |
| 4 | On a review date: keep, pause or retire per the plan's rules | Stated, never applied (only the owner acts on statistics; `run.py` applies only the automatic pauses, which I read). Plants Q5 (another seed) and Q6 (a 90% interval instead of 95%) **both pass**: nothing pins the interval | PARTLY |

## Must-fix

**1. An old loss pauses the version again after the owner re-approves it.**
- Probe, in the builder's fixtures: fly-a is paused for a Rs 10,400 loss. The owner re-approves it (paused to paper)
  five days later. The next scorecard run pauses it again for the same old trade and sends a second alert.
- `catastrophic_losses` looks at every closed trade of a paper version, ever. Only shadow versions are limited to the
  day.
- Fix (reasoning only): count only trades closed on or after the version's latest change to `paper`, or record each
  trigger once (the trade ID) and never fire on it again. One test with a re-approval.

**2. A loss from the shadow test pauses the version the moment it is approved.**
- Probe: a cand-c shadow trade loses beyond the cap, and the owner is alerted (correct). The owner later approves
  cand-c knowing that result. The next run pauses cand-c at once, for the shadow trade.
- That shadow trade is research evidence the owner already weighed. It is not a loss of the approved version.
- The same fix as 1 closes it: count trades after the approval, in book accounts only.

**3. A cap above C2's Rs 10,000 is accepted** (orchestrator's point 1).
- `parse_strategy` takes `catastrophic_loss_rs: 50000` (my probe). The schema only checks that the number is positive.
  The Rs 10,000 appears in a comment only.
- A version with a higher cap could lose up to the cap in one trade with no pause. C2's maximum loss per trade is a
  modelled limit; real fills, gaps and legging can exceed it.
- Fix: refuse a cap above the risk settings' `max_loss_per_trade_rs`, read from the one risk setting, never a second
  number. One test.

**4. "No new trades in any book" depends on D2 reading the status now** (orchestrator's cross-check).
- E6 writes the pause dated `on` (today). Judge 74's branch makes D2 read the status as of the start of the day, so a
  pause written at 10:00 lets Book 1 trade the version at 15:00 the same day.
- E6's `approved()` also drops drifted versions. D2's new `approved_on(day)` reads only registry rows, so after both
  merge a drifted version stays tradable until a pause, and then still for the rest of that day.
- The change belongs in D2 (judge 74). E6 then needs one test through D2's evaluator, not `approved()`: pause on the
  day, then D2 on the same day chooses nothing for that version.

## Should fix

- **Pin the review interval.** One test with fixed sample values and the hand-computed nearest-rank 2.5% and 97.5%
  points from seed 20261014 (Q5 and Q6 then fail).
- **Mark the review rule provisional** (orchestrator's point 4).
  - The docstring says "reasoning only", but neither the module nor the report says "provisional until S1". The report
    should print it on every review line.
  - The gate's 20 positions also live in two places: `review.py` `MIN_POSITIONS = 20` and D2's
    `UNPROVEN_BELOW_COMPLETED_TRADES = 20` in `fno/constants.py`, both from design 6. One constant.
- **Merge collision with E2.**
  - Both branches add a top-level `desk` parser with a function named `add_desk_parser`
    (`fno/desk/pack_cli.py` and `fno/scorecard/cli.py`).
  - `git merge-tree` of the two branches merges `fno/cli.py` without a conflict, so nothing flags it. One import would
    shadow the other, and `desk` would be registered twice.
  - One `desk` parser with `pack` and `scorecard` as its actions is needed. The second branch to merge must run the
    full suite on the merged tree.

## Orchestrator's points

1. **Cap edge, any book, shadow alert only:**
   - the cap edge holds: exactly at the cap pauses, Rs 0.01 less does not;
   - a loss in any book counts;
   - a shadow version is alerted once and never paused.

   **The cap above Rs 10,000 is not refused** (must-fix 3).
2. **Drift pauses only that version: MET on this branch.** My plant Q2 (a drifted version still approved) is caught (3
   failed). A change to paper with an unvalidated feature is still refused. After merging with judge 74's branch, see
   must-fix 4.
3. **Shadow accounts:**
   - `journal/shadow/<name>-v<n>/account/` exists, with Rs 5 lakh and the same writer and lock.
   - Names other than `shadow:<name>-v<n>` are refused, including `shadow:../book1_rules-v1`.
   - **No real `ShadowBooks` is built** (`fno/playbook/shadow.py` still has only the abstract class). So nothing yet
     proves that D2's shadow evaluation writes only inside its declared folder.
   - The test shows only that starting one shadow account leaves Book 1 unstarted.
   - This is still owed by whoever builds the real `ShadowBooks` (E5, or E6's next round), with a test that writes
     through it and finds nothing changed outside `journal/shadow/<version>/`.
4. **Review rule:**
   - it never acts automatically: MET;
   - it reads its thresholds from one place: not met (the duplicate 20);
   - it is labelled provisional until S1: not met.
5. **Stale `.pyc` process note: adopted.** All my plants on this branch ran with `python -B` and every `__pycache__`
   removed before each plant. I re-ran E2's 14 plants the same way: identical results (judge 72 stands).

## My plants (8, `python -B`, caches cleared; scorecard, playbook, books and desk tests)

| Plant | Result |
|---|---|
| Q1 shadow loss alerted on every run | caught (1 failed) |
| Q2 drifted version still approved | caught (3 failed) |
| Q3 losses read from the first account only | caught (3 failed) |
| Q4 the 3-month gate not checked | caught (1 failed) |
| Q7 pause dated the next day | caught (1 failed) |
| Q8 refused counted as not filled | caught (1 failed) |
| Q5 bootstrap seed changed | **not caught** |
| Q6 a 90% interval instead of 95% | **not caught** |

## Claims vs reality

| Claim | Reality |
|---|---|
| "2310 tests pass" | Confirmed |
| "18 of 18 mutations caught" | Not re-run; my 8 found 2 gaps (the interval) |
| "paused at once ... no new trades in any book" | True on this branch alone; false after D2 start-of-day merges (must-fix 4); re-approval impossible (must-fix 1) |
| "A shadow version's catastrophic loss is alerted once, never paused" | True while it is research. After approval, that same loss pauses it (must-fix 2) |
| The plan's cap is "the owner's per-trade cap Rs 10,000" | A comment only; any positive number passes (must-fix 3) |
| Review rule reasoning only, fixed in advance | Stated in the docstring; not labelled provisional in the report |

## Project rules

- New package `fno/scorecard/` behind the existing interfaces; composition root `fno/scorecard/wiring.py`, listed in
  CLAUDE.md.
- Constants in `fno/constants.py`; Slack only to #fno-desk through the alert sender. No orders.
- Branch rule followed.

## Addendum 1 (round 2, branch 26a6244): must-fixes 1-3 and the should-fixes MET; not yet PASS (must-fix 4 and the merge with D2)

**Gates (my runs, `python -B`, caches cleared):**
- full suite: 2,328 passed;
- ruff, format (512 files) and imports: clean.

**Must-fix 1 and 2: met.** My probes from round 1, re-run on this head:
- after a catastrophic pause and the owner's re-approval, the next run leaves the version on `paper`, with no second
  alert;
- a shadow-test loss followed by an approval leaves the version on `paper`.

The rule: only a **book** account's trade, closed on or after the version's latest change to paper, pauses it.

**Must-fix 3: met.** `CatastrophicCapWithinRisk` (a loader check, wired in `fno/playbook/wiring.py`) refuses a cap
above `risk.max_loss_per_trade_rs`. `parse_strategy` alone still accepts 50,000 (it is a schema check); the loader is
the gate, and its test uses 10,000.01.

**Should-fixes: met.**
- The interval is pinned. My plants on `config.yaml`'s `scorecard_review` (seed 7: 1 failed; confidence 0.90:
  2 failed) are caught.
- Every review line says "rule provisional until S1".
- The gate uses D2's `UNPROVEN_BELOW_COMPLETED_TRADES` and a new `PAPER_GATE_MONTHS`.
- There is one `desk` parser (`fno/desk/cli.py`).

**Real `ShadowBooks`: met.** `JournalShadowBooks` keeps each candidate's account in
`journal/shadow/<name>-v<n>/account/` and refuses an unstarted one. My plant moving the shadow folder under
`journal/book1_rules/` is caught (3 failed), including the containment test that hashes the tree before and after a
real E4 entry.

**My plants (`python -B`, caches cleared; scorecard, playbook, books and desk tests):**

| Plant | Result |
|---|---|
| A shadow account's loss counts for a paper version | caught (1 failed) |
| A loss from before the approval counts | caught (2 failed) |
| Cap check off | caught (1 failed) |
| Exactly at the cap does not pause | caught (1 failed) |
| Drifted version still approved | caught (3 failed) |
| Shadow loss re-alerted daily | caught (1 failed) |
| A loss **on** the approval day excluded (`>` instead of `>=`) | **not caught** (should fix: one test, since the builder chose "errs toward pausing") |

**Still open: must-fix 4, and the branch does not merge.** D2 start-of-day is now on `main` (a0a8eef). `git
merge-tree` of `main` and 26a6244 reports a **conflict in `fno/playbook/loader.py`**. That is the exact place where
E6's `drifted` exclusion (inside `approved()`) meets D2's new `approved_on(day)` (which D2's evaluator now calls).
Resolved naively, a drifted version would trade again through D2.

**For the PASS, one short round:**
1. merge `main`;
2. make `approved_on(day)` also drop the versions in `drifted`;
3. add the test through D2's evaluator: a pause dated the day (scorecard run before 15:00) and a drifted version
   each make that day's evaluation choose nothing for that version;
4. run the full suite on the merged tree.

I will check only that merge commit and the test. The rest of this round stands.

## Addendum 2 (round 3, branch be69a08 = c829012 plus the approval-day test): PASS

**Must-fix 4 and the merge with D2: met.**
- `main` (D2 a0a8eef) is merged in, and the `loader.py` conflict is resolved. `approved_on(day)` keeps D2's rule
  (`paper` at the start of the day and after every change dated that day) and also drops versions in `drifted`.
- `tests/scorecard/test_same_day_pause.py` runs D2's real evaluator on 21 Oct:
  - a catastrophic-loss pause written by a scorecard run that day removes the version from that day's evaluation;
  - a drifted version is not approved even before its pause row exists;
  - the prior day's set is unchanged.
- **The loss-on-approval-day test is there** (be69a08). My plant `>` instead of `>=` is now caught.

**My plants (`python -B`, caches cleared; scorecard, playbook, books and desk tests, 362): all 9 caught.**

| Plant | Result |
|---|---|
| A shadow account's loss counts for a paper version | 1 failed |
| A loss from before the approval counts | 2 failed |
| A loss on the approval day excluded | 1 failed |
| Cap check off | 1 failed |
| Exactly at the cap does not pause | 1 failed |
| `approved()` ignores drift | 3 failed |
| **`approved_on(day)` ignores drift** | 1 failed |
| **D2's evaluator back on `approved()`** | 1 failed |
| Shadow loss re-alerted daily | 1 failed |

**Gates:**
- full suite: 2,340 passed;
- ruff, format (513 files) and imports: clean;
- `git merge-tree` with current `main`: clean.

**Note (information, reasoning only):** drift is judged from today's validation reports, so `approved_on` for a past
day on a playbook that is drifted now leaves the version out of that past day too. That differs from the recorded
decision only if someone rebuilds an old day after a drift. Before E6 such a drift refused the whole load, so this is
no less safe, as the builder says. D3's records stay the truth for past days.

**Merge order:** E2 (b2749a6) and P8 (c59f862) are not on `main` yet. E6 already has the single `desk` parser
(`fno/desk/cli.py`). Whichever of E2 and E6 merges second must fold E2's `pack` command into it and run the full suite
on the merged tree. I check that merge.

**Verdict: PASS for be69a08.**

## Addendum 3 (merge check, 374ad67 with the `desk` parser fold)

**MET.** 374ad67 = 6f8c859 (main with E2) + be69a08. Beyond a plain merge, it differs only in the fold:
- `fno/cli.py` imports the one parser from `fno/desk/cli.py` and registers it once;
- `fno/desk/cli.py` has `COMMANDS = (add_pack_command, add_scorecard_command)`;
- E2's `pack_cli.py` now adds only its command (`add_pack_command`, handler `cmd_pack`);
- a new test covers one `desk` parser holding `pack` and `scorecard`;
- CLAUDE.md's composition-root list resolves the conflict by listing both `fno/desk/pack_wiring.py` (E2) and
  `fno/scorecard/wiring.py` (E6). That is correct.

**Checks on `main` e72677e (my runs):**
- `fno desk pack --day 2026-10-13` dispatches to the pack handler: refused, exit 2, nothing written;
- `fno desk scorecard --report-only` dispatches to the scorecard: "automatic pauses: none", exit 0;
- full suite: 2,448 passed;
- CI `checks` is green on 8c5bd5f (run 38511118329) and c0c40b0 (run 38511399834).

`main`'s code now equals the passed tips of P8, E2, D6 and E6 plus this fold. No unjudged code.
