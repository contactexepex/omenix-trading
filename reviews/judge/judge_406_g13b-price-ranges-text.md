# Judge 406: G13b story text, NIFTY and BANKNIFTY ranges at N+0, N+1 and N+3 (story/g13b-price-ranges at 3cef0edd)

**Verdict: PASS on the story text, with 2 minor findings. Lane 1.** Number claimed with O12's tool. Code starts after
G13 merges, and after question 1 (where each issue runs) is answered with O1's, A16's and A22's owners.

## Checked myself
- **The one measured number** (strong evidence, recomputed). From the committed A16b candle files
  `research/data/intraday/rv-candle/2020-2025/*.csv`, status `ok`, I summed `rv_overnight` over the summed
  `rv_session`. Note that `rv_session` = `rv_intraday` + `rv_overnight`, checked on a row.
  - Result: **1,469 sessions, 39.33%**, exactly the text's figure.
  - By year: 43.0%, 33.3%, 45.3%, 30.1%, 28.0%, 41.5% (2020-2025), matching the text's "28% in 2024 to 45% in 2022".
- **The τ arithmetic:** `(1 - 0.393) x 360/375 = 0.583`. 09:30-15:30 is 360 of the 375 session minutes. N1 and N3 add
  1 and 3 sessions. All correct.
- **Against the owner's decisions** (21 Oct, rows 262 and 264):
  - 5/25/50/75/95% ranges with direction derived (`p_up`);
  - NIFTY and BANKNIFTY at N0, N1 and N3; three issues;
  - baselines `no_change` and `implied`, plus `rv20` and `hist750`;
  - proper scores (QS, coverage, Brier), sealed before the outcome, with the 60-day calibration mark printed;
  - 08:45 waits for A22 (FL1's runs follow row 264).
  All covered, with the out-of-scope items named (positions and Slack are FL1's; BANKNIFTY end-of-day back-fill is
  part c).
- **Sealing on GitHub's push time** (O8's `file_pushed_at`), never on a commit date or a self-reported time. That is
  consistent with FL1, which reads `sealed_at` and prices on the first mark strictly after it (judge 403.2).
- **Honesty:**
  - `rv20`'s `p_up` is 0.5 by construction, and said so;
  - `hist750` is `not_eligible` at 09:30, with the reason;
  - the US closes are recorded but unused in v1, said so ("an untested adjustment is a guess");
  - the implied range's back-fill lead is labelled exploratory.

## Minor findings
1. **τ's sensitivity.** The overnight share moves from 28% to 45% by year, so a frozen 0.393 puts the 09:30 N0 τ
   anywhere from about 0.53 to 0.69 in a given year. The 09:30 N0 band's coverage will show it. Have the report print
   the frozen constant beside the 09:30 N0 coverage, so a miss is read correctly. A refit is a new method version,
   never silent.
2. **`rv20`'s Brier.** It is always 0.25, the same as `no_change`. Say in the report that this tests nothing about
   direction, so a reader does not take the equality for skill or failure.

## Addendum 1
Number 406.1. Head: 4398c013 (revision 2, after the owner's "Lab universe" row, line 265).

**Verdict: PASS stands.** Changes checked:
- **Part A (phase 1):** the 15:45 issue only, NIFTY and BANKNIFTY, N1 and N3 (no N0 at 15:45, correct). Forecasters
  `implied`, `rv20`, `hist750`, `no_change` and the new `ewma_t4`.
- **`ewma_t4` = `s T/√2`, `T ~ t(4)`.** t(4) has variance 2, so dividing by √2 gives unit variance: correct. I checked
  the closed-form quantile by hand at p = 0.95: α = 4p(1-p) = 0.19; q = cos(arccos(√α)/3)/√α = 2.13612;
  t = 2√(q - 1) = 2.1318, equal to the table.
- **One outcome source with FL1** (NSE's index-close files), and `sealed_at` = GitHub push time through O8's
  `Evidence`, now agreed with FL1.
- **Part B (every contract valued at end of day):** it already states that illiquid settlements are NSE's own values,
  and calls `smile_value` "no trade signal". Carry the same rule as judge 403.3's should-fix into part B: any IV or
  score from a contract untraded that day is flagged and kept out of aggregates.
- **Part C (09:15 issue from A22, with GIFT as a separate version) and the unbuilt 09:30 issue:** both stated, and the
  measured τ is kept.

The two minors of the verdict still apply (print τ's constant; `rv20`'s Brier is constant).

## Addendum 2
Number 406.2. Head: 622878db (revision 3; story file only).

**Verdict: PASS stands. The change fixes a gap that judge 406 missed.**
- **The gap:** revision 2's 15:45 `S_ref` was "d's official close, first seen before 15:45". That never happens live.
  The NIFTY closes file is updated in the evening UTC, for example 19:41 UTC on 14 Oct and 20:43 UTC on 19 Oct (the
  `git log` of `research/data/nifty-panel/warmup_closes.csv` on `origin/main`, read by me). That is hours after 15:45
  IST, so every live 15:45 issue would have been `missing`. I passed it without checking that timing: my own miss.
- **Revision 3:** `S_ref` = the spot recorded with d's canonical 3 pm chain (A4 NIFTY 14:55-15:10, A4c BANKNIFTY
  15:01-15:13), with `s_ref_at` kept, so it is synchronous with the implied forecaster's chain.
  - τ = k + (1 - 0.393) × 30/375 = **k + 0.0486** (the rest of d's session, intraday share even in time; arithmetic
    checked).
  - `rv20`, `hist750` and `ewma_t4` use closes before d. Outcomes stay official closes. Consistent.
- **The two minors from the verdict are written in.** Part B is marked stopped by the phase-1 scope freeze.
  Criteria 1-2 match.
- **Reasoning only:** at about 15:00 the remaining 30 minutes carry the closing auction's variance; spreading it
  evenly in time is the stated simplification. The first weeks' N1 coverage will show whether it matters.
