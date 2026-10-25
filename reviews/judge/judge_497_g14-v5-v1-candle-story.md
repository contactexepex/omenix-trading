# Judge 497: G14 story text, v5 side-by-side V1 on the candle RV history

**Scope:** story/g14-v5-v1-candle at c648a1d5 (builder session_0185gR5DmoDh2zBAvgRU4CEB), `docs/stories/G14-v5-v1-candle.md`
and its register row. It is checked against DESK_DECISIONS "v5 trial: V1 next-session forecasts from stored candle
history" (23 Oct 2026). Lane 1 (forecast records), one judge: Judge J (session_01Qg4Gxun1NvGRrtS9C68Dc1). Story text,
round 1 of 2.

**Verdict: FAIL.** 1 blocking (quality rule 2), 3 should-fix and 3 minor. The design itself is sound, and its facts
check out against the repository.

## Facts checked (my evidence)
| Story says | Result | Evidence |
|---|---|---|
| v4's V1 starts after 20 usable live A16 sessions | MET | `fno/forecast_v4_rules/capture.py:46,133` |
| Candle history `exposed`, no fresh data spent | MET | `research/DATA_SPEND.md` row "NIFTY intraday realised variance (A16b candles)" |
| 1,665 usable of 1,684 candle sessions | MET | `research/data/intraday/rv-candle/`: 1,684 files, 1,665 `ok`, 19 `void` |
| A candle row for `d-1` is first seen on `d` at about 15:33 | MET | 21 Oct's row `first_seen_at` 2026-10-22T10:03:11Z; 19 Oct's 2026-10-21T10:03:17Z |
| Gap: 19 Oct live 3.9% higher, 21 Oct 0.3% | MET | live 1.533569e-4 / candle 1.476017e-4; live 1.142562e-4 / candle 1.139157e-4 |
| A measurement trial costs one K in the luck correction | MET | `fno/factory/trial_count.py`: "a measurement counts in K but is never a test" |
| HAR intraday at least 250, up to 750 sessions | MET | `capture.py:46` (250), `baselines.py:18` (750) |

## Findings
1. **Blocking (quality rule 2): three requirements of the design have no criterion.**
   - The R1 card, ledger trial and gate-log row "before any code runs".
   - `FREEZE_v5_v1.md`, hashing the package and the imported G7 files before the first live day.
   - The measure-gap label in the report (criterion 4 covers the records only).

   A requirement in neither a criterion nor the out-of-scope list is blocking. Expected:
   - a criterion that the card's commit, with its ledger and gate-log rows, is a strict ancestor of the first
     commit touching `fno/forecast_v5_v1/`, tested on real git (as judge 480 required for D6);
   - a criterion that the step refuses a live day while a hashed file differs from `FREEZE_v5_v1.md`, or before it
     has a `Frozen on:` line;
   - the report's label inside criterion 6.
2. **Should-fix: the step's merge timing departs from the owner's decision.**
   - The decision row says "its daily step merged only after the v4 sign-off". The story says "Its code merges once
     judged", and only `daily.live_from` waits.
   - MS's hard constraint 1 (no `DAILY_RUN_STEPS` change until the owner signs v4) is the same orchestrator rule.
   - Expected: the `DAILY_RUN_STEPS` and `fno/daily/wiring.py` rows land only after the sign-off, or the orchestrator
     records that a `not_live` row is what the decision meant.
3. **Should-fix: criterion 2 does not cover v4's frozen files.**
   - It names only `fno/forecast_v4*/` and `research/forecasts/v4/`. `freeze_check.BYTE_CHECKED_GLOBS` also holds
     `fno/forecast_scoring/v4/*.py`, `fno/forecast_scoring/scores.py`, four `fno/intraday/` files, `tools/v4_*.py`,
     `research/forecasts/PROTOCOL_v4*.md` and `research/forecasts/v4_*`. This report scores with v4's QLIKE, the most
     likely place for an edit.
   - `research/forecasts/FREEZE_v4.md` does not exist yet, so "`problems()` unchanged" cannot be the only check.
   - Expected: the test takes `freeze_check.byte_checked(root)`, the one list, and asserts that none of those paths
     changes against the merge base.
4. **Should-fix: the splice rule contradicts itself on a real row.**
   - On 16 Oct, live A16 is void but the candle row is `ok` (5.82e-5), first seen 19 Oct 15:33.
   - Under "candle first", every forecast from 20 Oct on reads 16 Oct as 5.82e-5. "Void and missing stay missing,
     never filled" and criterion 1 say it is missing.
   - Expected: one rule. Candle-first is coherent, because a candle measurement is not a fill. Criterion 1 should
     carry 16 Oct's expected value for `d` = 19 Oct (missing) and `d` = 21 Oct.

**Minor:**
- (a) "On 22 Oct A16 had 3 live sessions ... 2 usable" holds only before 22 Oct's 15:31 row. After it there are 4
  rows with 3 usable, which is what the decision row says. Name the time.
- (b) A candle row for `d-1` is never seen before `d`'s cutoff, so `v5c_trailing` always reads the live A16 row and
  equals v4's trailing. The table's "the spliced series" should say so plainly.
- (c) The header names judge B as the one judge; the orchestrator assigned Judge J.

## Notes
- The measure mix (candle history, a live last lag, a live target) is honest only because every record counts its
  sources and the gap table grows daily. Keep both as criteria, not just design.
- No code yet: no gates or plants this round.

## Addendum 1

**Scope:** round 2 of 2, story/g14-v5-v1-candle at 68564773 (diff c648a1d5..68564773 of the story file).

**Verdict: PASS (story text).** No blocking and no should-fix findings; 1 minor. Code may start after v4's piece 4.

- **Blocking, accepted (fixed).**
  - Criterion 8: the card, ledger and gate-log commit is a strict ancestor of the first `fno/forecast_v5_v1/`
    commit, tested on real git.
  - Criterion 9: the capture refuses a live day when `FREEZE_v5_v1.md` is missing, lacks a `Frozen on:` line or
    shows a hash mismatch.
  - Criterion 6: the report prints the label and the gap table.
- **Should-fix 2, accepted.** The orchestrator's ruling: the package, card and freeze record merge once judged; the
  O1 step is its own commit, merged only after the owner signs v4. This matches the decision row's "its daily step
  merged only after the v4 sign-off".
- **Should-fix 3, accepted.** Criterion 2 takes `freeze_check.byte_checked(root)`, the one list, against the merge
  base.
- **Should-fix 4, accepted.** Candle first, point in time, with 16 Oct worked through: missing for `d` = 19 Oct,
  5.82224e-5 (candle) from 21 Oct.
  - My check: the candle row's `first_seen_at` is 2026-10-19T10:03:17Z, i.e. 15:33 IST, after 19 Oct's cutoff and
    before 21 Oct's; 20 Oct is the Dussehra holiday.
  - Criterion 1 carries both values.
- **Minors, accepted.**
  - The session count is timed (14:11 run: 3 rows, 2 usable; after 15:31: 4 rows, 3 usable), matching `rv/`.
  - `v5c_trailing` is stated to read the live row and to be a control; only `v5c_har_intraday` tests the candle
    input.
  - The header names Judge J, and judge D for the O1 parts.

**Minor:**
- (a) "I add the step on this branch" sits beside "a separate commit, merged only after the owner signs v4".
  Merging the branch takes all its commits. Push the step commit only after the package merge, or on its own
  branch, so a merge of the package can never carry it early.
