# Judge 196: S6 code, scorecard measures (judge G)

- **Judged:** `story/s6-scorecard-measures` at `a9f745bf3432a1d75fb5ca383d812f7ad40a0dd7` (builder session
  0185gR5DmoDh2zBAvgRU4CEB; claims `response_180_s6-code.md`). It is built on S3 `650e861d` plus main.
- **Text:** PASSed in judge 158 addendum 1. Lane 1. The orchestrator gave the go; 196 was the next free number.
- **Verdict: FAIL.** There are 2 should-fix findings:
  - the cash-rate placeholder can be frozen silently;
  - three test gaps where my mutations survive on paths the code takes every run.

  There are also 3 notes. The arithmetic I re-ran by hand is right, and 15 of my 18 planted mutations are caught.

## What I re-ran

- **Gates:**
  - ruff check, ruff format and `check_imports` are clean;
  - the largest file is `random_control.py` at 165 lines;
  - `tests/scoreboard tests/evaluation`: 161 passed;
  - full suite: 6,397 passed, 8 failed, 1 error, **exactly main's failure set** (the shallow clone's history-based
    freeze and back-fill tests).
- **S2's tests are unedited.** `git diff 71a1de30 a9f745bf --stat -- tests/scoreboard/` lists only added files.
  `tests/evaluation/test_completeness.py` only adds the five items to the decided list and adds a test that each item
  is required.
- **View (a), recomputed by hand from the index files** (the "judge verifies" item):

  | Step | Value |
  |---|---|
  | Fund return per interval (close change + (earlier Div Yield / 100 − 0.05%) × days / 365) | −1.639272%, +1.301626%, −0.685506% (3 days), +1.607571% |
  | Fund gain on Rs 1,00,000 | Rs 584.42 |
  | Fund gain after 20.8% tax | Rs 462.86 |
  | Cash gain (5.5%, 6 days) | Rs 90.41 |
  | Cash gain after 31.2% tax | Rs 62.20 |

  These equal the test's literal values to the paisa. View (b) follows from the same growth: 20 × 584.42 for the fund
  and an idle Rs 19,00,000 at the cash rate.
- **The fixtures and the archive.** The 7, 8 and 9 Oct fixtures are byte-identical to the archived files (manifest
  SHA-256). The 12 and 13 Oct fixtures differ: they hold four extra index rows that the archived copies lack. Their
  "Nifty 50" rows are identical to the archive, so every figure stands (note 3).
- **The t-check example, by hand:**
  - z = [−50, −175, −150, 75, −50, 350] ÷ 1,333.33, so sd = 0.14475;
  - bound = 0.15 − 2.015 × 0.14475 ÷ √6 = 0.0309;
  - the table's one-sided 95% t values for 1 to 30 degrees of freedom are the standard ones.
- **`claim_allowed` is unaffected.** The disagreement test asserts the claim is unchanged and that the warning is
  appended to `reason`.

## The orchestrator's three decisions

1. **The 5.5% cash rate as a placeholder:** the placeholder itself is fine, but nothing stops it from being frozen
   (finding 1).
2. **Scoreboard A carries no AI or operating cost:** accepted. The standard unit is one lot with no account (S1). A's
   verdict therefore stands for every book, while B withholds an AI book's verdict until F8 is known.
3. **Random-control twins exit at the real exit day's quotes:** accepted as a stated limit. Time exits are the only
   coded exits, so twin and trade normally share the day. Only an E4 retry or an expiry settlement differs, and the
   control is descriptive and never a gate.

## My mutations (each alone, then reverted)

**Caught (15):**

| Area | Mutation |
|---|---|
| Do-nothing | yield of the later day |
| Do-nothing | no expense |
| Do-nothing | cash over 360 days |
| Do-nothing | fund long-term at `>` instead of `>=` |
| Do-nothing | F&O tax on the whole period instead of per financial year |
| Do-nothing | a fund loss taxed |
| Do-nothing | verdict given with the AI cost unknown |
| Measures | drawdown high not starting at 0 |
| Measures | a zero-net trade counted as a loss |
| t-check | no linearisation |
| t-check | `t(k)` instead of `t(k−1)` |
| Random control | ties counted in full |
| Random control | missing cap at 9.9% |
| Missed runs | the report day listed |
| Missed runs | `waiting` not counted as a missed exit review |

**Survived (3):** the oldest remainder kept, the 10-step window at `<` instead of `<=`, and no bucket replay. These
are finding 2.

## Findings

### Should fix

1. **The 5.5% cash rate can be frozen silently.**
   - `Terms.cash_rate = 0.055` is a placeholder; the protocol says "the RBI repo rate on the freeze day, written here
     and in `Terms.cash_rate` ... at the freeze".
   - But `do_nothing_benchmark` is marked "decided by the owner on 2026-10-15", and nothing refuses a freeze while the
     placeholder stands. The freeze hashes the code, so 5.5% would be frozen unless someone remembers.
   - That is a real path: the S1 freeze is scheduled after S3, F9 and E8.
   - **Fix:** make the placeholder detectable and refused at the freeze. For example, put the cash rate in
     `PROTOCOL.md` as a number with a "to be set at the freeze" marker that `evaluation check --decided` and the freeze
     refuse, with the code reading it from there or a test pinning the two equal. Add a test for the refusal.
2. **Three test gaps, each on a path the code takes in normal running:**
   - **t-check, the oldest remainder left out:** keeping the oldest blocks instead survives. The 45-session test uses
     a constant series and checks only the counts. Almost every section has n mod 20 ≠ 0. **Fix:** a known answer on
     a non-constant series where the left-out sessions change the bound.
   - **Random control, the bucket redraw:** removing the `_bucket_room` call from `_twin` survives. The test checks
     `_bucket_room` alone, not that a draw is redrawn, which is criterion 10's wording. **Fix:** an end-to-end case
     where a flip would overfill the bucket and the twin is redrawn.
   - **Random control, the 10-step window boundary:** `<` instead of `<=` survives. Rule 5 asks for the boundary.
     **Fix:** a strike exactly 10 steps away is in the window, and one at 11 steps is not unless it is the real trade's.

### Notes

1. **Scoreboard A's view (a) understates capital.** A take's net sits on its decision day, but its capital is counted
   only on the series' days. A closed take whose exit falls after the series' last day therefore has capital-days cut
   off, so the book looks better per rupee-day. It is descriptive (RM1's gate reads scoreboard B). State it, or extend
   the capital path to each take's exit day.
2. **Twins at the real exit day** (decision 3): accepted, stated limit.
3. **Fixtures for 12 and 13 Oct** are not the archived bytes (four extra index rows; the "Nifty 50" rows are
   identical). Say where they came from in the test docstring, or replace them with the archived copies.

## Project rules

- **Reuse:** S2's resampler and the uncertainty criterion, E4's pricing, C1's `Order`, B2's held model and
  `read_index_figures` are reused.
- **Composition root:** the scoreboard wiring.
- **Size:** every file is under 350 lines.
- **Process:** the self-review is present (1 must-fix and 8 should-fix, 7 applied, 2 stated), and real index files are
  used.

## Addendum 1: re-judge of revision 1 at `f6d0d379312739e0df291dbaed5e4252a12fb7dd` (judge G)

**Verdict: PASS.** I judged the S6 commit `f6d0d379`. The rest of the range is main merged in.

| # | Fix | Re-judge |
|---|---|---|
| 1 (should fix) | The cash-rate placeholder: `PROTOCOL.md` says "cash rate = 5.5% a year (set at the freeze)"; `undecided_items` refuses any value still carrying the marker; a test pins `Terms.cash_rate` to the protocol's number; the freeze and `--decided` both refuse | **Accepted.** On the real `PROTOCOL.md`, `python -m fno evaluation check --decided` lists `do_nothing_benchmark` as not decided, and the parsed value contains the marker even though it is split across a line break. My mutations are caught: ignoring the marker (4 tests fail), and changing `Terms.cash_rate` to 0.06 without the protocol (3 fail). The freeze test refuses with "not decided by the owner: do_nothing_benchmark" and writes no freeze file |
| 2 (should fix) | Three test gaps | **Accepted.** I re-planted all three surviving mutations. Each now fails a test: the t-check keeping the oldest remainder, the 10-step window at `<`, and no bucket replay in `_twin` |
| note 1 | Scoreboard A's capital cut | Labelled on the board (`capital_cut`, with the count of takes): accepted |
| note 3 | Fixtures | The 12 and 13 Oct fixtures are now the archived bytes. A new test pins all five fixtures to the manifest's SHA-256. Accepted |

**Gates on `f6d0d379`:**

- ruff check, ruff format and `check_imports` are clean.
- `tests/scoreboard tests/evaluation` with `-n auto`: 187 passed.
- Full suite with `-n auto` (`env -u FNO_SLACK_BOT_TOKEN`, full git history): **6,641 passed, 0 failed**.

Per rule 9 (money and the real-money gate's input), ChatGPT reviews next, then the merge with S3.

## Addendum 2: re-judge of revision 2 after ChatGPT review 120, at `3eb96cda` (code commit `6a26770d`) (judge G)

**Verdict: PASS.** The orchestrator's answer to review 120 is response 200. I judged the code commit `6a26770d`; the
rest of the range is main merged in.

**Gates on `3eb96cda`:** ruff check, ruff format and `check_imports` are clean. Full suite with `-n auto`
(`env -u FNO_SLACK_BOT_TOKEN`, full git history): **6,693 passed, 0 failed**.

| Fix | Code | My planted break (each alone) | Result |
|---|---|---|---|
| 1. A fixed Holm family | `_apply_holm`: each book's head-to-head claim plus every directional pair (3 + 6 = 9 for three books); an untestable member enters with p = 1; `holm_family` is shown | Untestable members dropped, so the family shrinks | caught (4 tests) |
| | | Pairs with no common day dropped from the family | caught |
| 2. Own unscored days as misses | `_misses`: a D6-unscored day while another book submitted is the book's own miss and is eligible; a day unscored for every book stays apart | Own unscored day not counted as a miss | caught |
| | | Own unscored day left apart | caught |
| | | Every unscored day counted, including all-book days | caught |
| 3. `_reviewed` requires True | `.get("reviewed") is True`; a missing book counts as a missed review. E3 writes `reviewed` on every outcome (`daily_steps.py:205, 215, 218`) | `reviewed: false` accepted | caught |
| | | A missing book read as reviewed | caught |
| Disclosure 4: `inputs` | An account limit only with the "is already open in" reason | `inputs` read as a limit for any reason | caught |
| Disclosure 8: "not comparable" | View (a)'s verdict is withheld when `capital_cut` is not 0 | Withholding removed | caught |
| Cash rate | `PROTOCOL.md` states the owner's 16 Oct rule (91-day T-bill on the freeze date, DESK_DECISIONS row 221), and the "(set at the freeze)" marker stays | — | `evaluation check --decided` still names `do_nothing_benchmark` |

**Caught:** 9 of my 10 planted breaks; the clean tree gives 195 passed in `tests/scoreboard tests/evaluation`.

### Notes (no fix required)

1. **Untested design point.** Making an *incomplete* section testable in Holm (removing `not claim.get("incomplete")`)
   survives. Its own verdict is still blocked, because `_section` sets `claim_allowed` to false. But a testable
   incomplete member with a small p would move the other members' step-down thresholds.
   - It needs a take open past its expiry with no settlement price, which E7 refuses only on a malformed settlement
     file, so it is not normal running.
   - Worth a one-line test when the file is next touched.
2. **`reviewed` is now stricter than E3's own blocking rule.** E3 treats "no snapshot, nothing due" as nothing left
   unreviewed (`daily_run.py:104`). With a trade held, S6 now lists it as a missed exit review.
   - That is review 120's choice: `reviewed: false` with no error counts. It is conservative and descriptive (scoreboard
     B's operations list).
   - It will appear on any day the execution snapshot fails while trades are open. Read it as "exits not checked
     against prices that day", not as a lost exit.
3. Disclosures 5, 6, 7 and 9 (staggered exits and no-fill share, `after_cut` "not a claim" and "incomplete",
   `net_per_risk` beside each rupee pair, random-control `flipped_share` and rejections) are reporting only, and
   their tests pass. They change no figure that decides anything.

S3 and S6 can merge, followed by the rule 8 dry run.

## Addendum 3: head `7cb57e3cb8d17cb9effd6f95926d1235a86f91a6` (judge G)

**The PASS stands.** `git diff 3eb96cda 7cb57e3c` touches only `research/evaluation/PROTOCOL.md`. It adds two lines to
`missed_runs`' reason, which cite the owner's 16 Oct row "S3 missed runs: one book's unscored day counts as its miss"
(DESK_DECISIONS line 225, owner: "Yes, count it (Recommended)"). That row is the rule judged in addendum 2.

- The status stays "decided by the owner on 2026-10-15".
- No code changed.
- On this head, `python -m fno evaluation check` reports "complete", and `tests/evaluation tests/scoreboard` gives
  195 passed.

## Addendum 4: `story/s6-followups` at `edb78629` (on main `91c54f88`) (judge G)

**Verdict: PASS.** The branch has two commits:

- `8a9f849c`: the reasons for a missed exit review, a test that an incomplete section is never testable in Holm (my
  addendum 2 note 1), and no `-0.0` share;
- `edb78629`: no worst day until a day loses money, and `cash_rate_basis` = "placeholder until the S1 freeze sets the
  91-day T-bill yield" on every do-nothing block.

**Gates:**

- ruff check, ruff format and `check_imports` are clean.
- Full suite with `-n auto`: **6,788 passed, 0 failed**.

**Mutations (each alone, then reverted).** All four were caught; `tests/scoreboard` gives 127 passed clean:

- an incomplete section made testable in Holm, which survived in addendum 2;
- a worst day reported at a net of 0;
- `waiting` read as "failed";
- the cash-rate basis label emptied.

**Exit-review reasons:**

- "no exit review ran";
- "not checked against prices: <reason>" when `waiting` (no valid snapshot);
- "exit review failed: <error>";
- "exit review not recorded as done".

This answers my addendum 2 note 2: a no-snapshot day now says it was not checked against prices, not that an exit was
lost.

**Real data:** I built both boards for 16 Oct 2026 from the repository, without the CLI's Drive push, so no Drive
download was made.

- Scoreboard A: every book "not started", `holm_family` 0, because the common start is not reached.
- Scoreboard B: every account "account not started" locally, because the accounts are kept in Drive under E2c.
- No book has a missed run.

This is the expected state before the first paper run.

**R3 note (judge 208):** see judge 208, addendum 1 note.

## Addendum 5: `story/s6-followups` at `e015438b` (judge G)

**Verdict: PASS.** It is one commit on top of the merged `edb78629`. `CommittedRuns.records` now drops records with
`mode: shadow`, so a D2 shadow record can never stand for the book's own action: not in S3's `MatchedDays._actions`,
not in S2's readers, and not in F9a's `CollectedRunRecords`.

- **F9a stays correct.** I checked that it was unaffected and is in fact made right. F9a's real decision is the book's
  own records; its shadow decision is read from the separate `journal/<book>/role_value/shadow/` folder
  (`fno/role_value/records.py`). So the filter removes nothing F9a needs.
- **The test is real.** Reverting the filter fails 1 test; `tests/scoreboard` gives 128 passed clean.
- **Gates:** ruff is clean. Full suite with `-n auto`: **6,814 passed, 0 failed**.
- **What is left:** the store-level overwrite (`DecisionStore` keyed by opportunity ID) is with R3's builder, as the
  orchestrator says. I will check it in judge 210 addendum 1.
