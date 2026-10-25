# Judge 191: S3 code, scoreboard A matched decisions (judge G)

- **Judged:** `story/s3-scoreboard-a` at `3e626db71cc3d10522aefaad7ed4f554fe35d3dd` (code) and `eebf90ef` (claims,
  `response_177_s3-code.md`, being renumbered). Builder session 0185gR5DmoDh2zBAvgRU4CEB. Lane 1. The text PASSed in
  judge 168 addendum 1; the orchestrator gave the go and confirmed the SHA. 191 was the next free number on main.
- **Verdict: FAIL.** There is one should-fix: a test gap on the p-value's tie rule, where my mutation survived on a
  path that sparse series really take. There are also 3 notes. Everything else is MET on my own evidence. Twelve of my
  13 planted mutations are caught.

## What I ran

- **Gates:** ruff check, ruff format and `check_imports` are clean. The new modules total 611 lines, and the largest
  file is 160 lines.
  - `tests/scoreboard tests/risk`: 361 passed.
  - Full suite on the commit: 6,165 passed, 11 failed, 1 error. Eight of the failures and the error are main's
    shallow-clone set from my earlier runs.
  - The other 3 are the ones the builder declared: the G7 count test and two account tests moved by E2c. The
    orchestrator confirms they are fixed on main (`7c154a90`; judge 187 addendum 1).
- **Real output, built without the Drive push** (I did not run the CLI, because it pushes to Drive):
  - `build_matched_board(cfg).build(2026-10-15)` gives "scoreboard A 2026-10-15 (protocol v1, not frozen: figures
    provisional); common start not reached", with every book "not started" and 0 actions.
  - That is the expected state before the first paper run.

## The orchestrator's points

- **(a) Holm takes a plain list.** `uncertainty.holm(p_values, alpha)` takes a `Sequence[float]` and returns one bool
  per claim, in the input order. The known answer is tested ([0.010, 0.030, 0.040] gives [True, False, False], and the
  same in any order). MET.
- **(b) S2's tests are unedited.** `git diff 71a1de30 3e626db7 --stat -- tests/` shows only the 4 new `matched` files.
  `lower_bound` is the old code split into `resampled_ratios` plus the same nearest-rank reader. MET.
- **`HeldMaxLoss.of_legs` keeps behaviour.**
  - The "more sold than bought" check moves from `_legs` into `of_legs`.
  - `max_loss` now calls `of_legs(_legs(...))`, so it runs the same check in the same order. An empty leg list still
    passes the check and returns 0.
  - The existing `open_risk` tests are unedited and pass. My mutation removing the check is caught (2 tests). MET.
- **The criterion 8 example correction (a rule-document edit).** Design 3 says a series runs "to the last decision
  day whose actions have all closed". The old example (keeping the day and cutting the open take) contradicted that.
  The new example (day 1 only, until day 2's take closes) follows it, and the code does exactly this: `scored_days`
  stops at the first day with an open take. **Accepted.**

## The builder's decisions made in code

| # | Decision | Judge |
|---|---|---|
| 1 | One-lot maximum loss = B2's held model (Rs 7,615 for a 100 × 75 long call, exit pad and brokerage included) | Accepted. It is the same model C5 uses for held positions, conservative and stated |
| 2 | Criterion 8's example | Accepted (above) |
| 3 | `inputs` (the same trade already open) is an account limit, so the action is a take | Accepted: it is book state (`manager.py:56-58`). Note 1 |
| 4 | "No common pack" is its own reason, outside the cap | Accepted: it is a desk fault, not the book's |
| 5 | Pairs run both ways, and both enter Holm | Accepted. Each direction is a distinct one-sided claim, so including both makes Holm more conservative, not less |
| 6 | No collected run yet gives "not started" | Accepted, and consistent with the miss cap counting from the first run |
| 7 | Lot size comes from `config.yaml` | Note 2 |

## My mutations (each alone, then reverted; `tests/scoreboard tests/risk`, clean tree 361 passed)

Caught: 12.

- Holm `>=` changed to `>`.
- Holm without the stop at the first failure.
- An open take not ending the series.
- `inputs` read as a skip.
- `stress_loss` read as a skip.
- Pair risk set to 2.
- Miss cap `>` changed to `>=`.
- No pack-hash check.
- Settlement on the wrong side.
- Pairs left out of Holm.
- A not-filled leg scored.
- `of_legs` without the fixed-loss check.

**Survived: `p_value` counting `r < 0` instead of `r <= 0` (finding 1).**

## Findings

### Should fix

1. **The p-value's tie rule is untested, and ties happen.**
   - `p_value` counts resampled ratios **at or below** 0. That is what makes "p < 5% exactly when `lower_bound` > 0"
     hold. The equivalence test uses continuous Gaussian series, so it never meets a tie.
   - Ties at exactly 0 are common on a real scoreboard A series. Most days are (0, 0) skips, and any resample of
     20-day blocks with no take gives a ratio of exactly 0.0 (`uncertainty.py`: "a resample never at risk").
   - **My check:** a 40-day series with 3 takes gives 565 resamples of exactly 0 out of 10,000. With the `<` mutation,
     a sparse all-winning series would report p = 0 and pass Holm, while `lower_bound` is 0 (no claim). The mutation
     survives today.
   - **Fix:** add a known-answer test on a sparse series, for example 40 days with two winning takes. It should
     check that `p_value` ≥ 0.05 exactly when `lower_bound` is not above 0, with the tie share stated. No code change
     is needed.

### Notes

1. **`inputs` as a take:** if a book's same trade ID is proposed again while open, A counts a second take of that
   opportunity. Opportunities appear on their first day in the window, so this needs a re-run; no fix.
2. **Lot size:** the unit uses today's `lot_sizes.NIFTY` for every past day. When NSE revises the lot, the per-book
   ratio is unchanged (net and maximum loss scale together), but past rupee pair differences rescale. If it matters,
   the record's day-specific lot could be used later.
3. **F9 imports:** `StandardUnit` and `holm` signatures are listed in the claims for F9. Any change goes through the
   orchestrator, as the claims say.

## Project rules

- **Simplicity and reuse:** S2's resampler, E4's `price_leg`, C1's `Order`, E7's settlement and B2's held model are
  reused, with no second bootstrap or pricing.
- **Composition root:** `fno/scoreboard/wiring.py`.
- **Privacy:** the board path is git-ignored and pushed to Drive through E2c's `PrivateFiles`.
- **Process:** a self-review section is present (1 must-fix and 7 should-fix, all applied), and a real output sample
  is in the claims.

## Addendum 1: re-judge at `650e861df50e466a7669fdcb5b200693d9013d51` (judge G)

**Verdict: PASS.** The fix reached me from the builder. I re-judged it as part of the judge and builder loop and report
the verdict to the orchestrator.

- **Should-fix 1 is accepted.** `test_a_resample_exactly_at_zero_counts_against_the_claim` covers both cases:
  - a flat series, where every resample is exactly 0: `lower_bound` = 0.0 and `p_value` = 1.0;
  - a tied series of 19 zeros and one positive day: p < 0.05 exactly when the bound is above 0.
- **I re-ran both:**
  - `tests/scoreboard` on the fix gives 76 passed;
  - my `< 0` mutation of the p-value is now caught (1 failed, 75 passed).
- **The commit changes nothing else:** no `fno/` change, only the test, the claims renamed to
  `response_179_s3-code.md` (177 was BR1a's) and the README row.
