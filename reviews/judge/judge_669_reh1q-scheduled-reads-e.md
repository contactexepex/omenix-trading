# Judge 669: REH1q, a scheduled read pushed later than the day's (story/reh1q-scheduled-reads @ 569ba7b7a), judge E

**PASS (round 1; 1 minor). Lane 1** (it changes what a rehearsal serves from the real record; judge 1 of 2). Judge E,
own session; judge F's verdict not read. Story and code judged together.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| Q1 the 21 Oct candles case | MET | The real manifest row `nifty-15m.csv` (15m 2026-09-21..2026-10-19): requested 15:33:06.77, fetched 15:33:11.36 IST, as claimed. `scheduled_pick` at 15:35:43 finds nothing near, then serves the latest same-day answer saved before now. Q1 plant (no fallback): 5 failed |
| Q2 the recheck gets its own answer | MET | Real 23 Oct receipts: first raw saved 15:40:07, recheck raw 16:00:10 IST, so at 16:00:00 the latest answer before now is 15:40's. Near-first serves the recheck its own. Q4 plant (the near window's latest): 1 failed. Q7 (`EARLIER` 0 s): 2 failed |
| Q3 never another day's | MET | The fallback keeps only `saved.astimezone(IST).date() == now's IST date`. Q2 plant (any day): 1 failed |
| Q4 ahead bounded, nothing after now from behind | MET | Q3 plant (`saved <= now` dropped): 5 failed. Q6 plant (the fallback's earliest, not latest): 2 failed |
| Paced reads unchanged | MET | `ServedOnce` is not in the diff; only `recorded_candles` and `recorded_closes` call `scheduled_pick` |
| The candle window | MET | Q8 plant (any window of the kind): 1 failed |
| Gates | MET | Trial merge a1d015d0e (569ba7b7a + origin/main 140ea83d8): ruff clean, format clean (2,730 files), check_imports clean (2,886 files), record scan clean (9,483 files). Full suite with the token kept: **17,445 passed, 13 xfailed, 0 failed** |

## Plants

8 planted, each alone on `tests/rehearsal`, `tests/close_read` and `tests/intraday` (622 tests), restored after. 7
caught. Q5 (the fallback's day taken as `now.date()`, not the IST date) is equivalent in the real wiring: both
sources get `now_ist` (`candle_wiring.py:29`, `close_wiring.py:23`), so the two dates are the same.

## Findings

**Minor 1. The stated limit is wider than stated.** Strong evidence: code read, plus the real save times.
- The near window (60 s back to 10 min ahead) comes before the fallback, and both sources sleep until the picked
  answer's save time.
- The builder states M1: a 15:40 read pushed past 16:00:04 is served the recheck's answer.
- The same happens from 15:50:10 on. A first read pushed to 15:52 has the 16:00:10 recheck answer inside its near
  window, so it waits about 8 minutes and records the recheck's list, though 15:40's answer already existed.
- The recheck then reads "unchanged", and the daily run is delayed by that wait.
- It is rehearsal-only and writes nothing real, and a read pushed 10 minutes is less likely than the 21 Oct case
  (2.5 minutes).
- Fix: state the limit as "a first read pushed to 10 minutes or less before the recheck's answer". If it ever
  matters, keep the near window only up to the day's next scheduled read.

## Answer

The rule matches the orchestrator's summary. The fallback never takes an answer saved after now, nor one from another
IST day, so there is no look-ahead.

## Addendum 1

Minor 1 follow-up, commit 87ec0493a on `story/reh1qs-minors`. **PASS.**

- **Accepted: the limit is stated, not capped.** The builder's reason holds: capping the near window at the next read
  would need the recorded source to know A4h's timetable or which read is asking, for a rehearsal-only case. My own
  fix offered stating it precisely as the first option.
- **The stated boundaries are right.** I checked them against the rule (`EARLIER` 60 s, `NEAREST` 10 min) and
  the real 23 Oct saves (15:40:07, 16:00:10):
  - 15:41:07, the first answer exactly 60 s back: near, so "first";
  - 15:41:08 to 15:50:09: the fallback serves "first";
  - 15:50:10, the recheck exactly 10 min ahead: "recheck".
  - The new `test_the_stated_limit_at_the_real_23_oct_times` pins all five points.
- **Plants:** M3 (`EARLIER` 61 s) 1 failed; M4 (`NEAREST` 599 s) 3 failed.
- Gates: trial merge 0454aa763 (story/reh1qs-minors adc5063a5 + origin/main 5c613c6b4), token kept: ruff, format (2,744 files), check_imports (2,900 files) and the record scan (9,513 files) clean; **17,528 passed, 13 xfailed, 0 failed**. Only `87ec0493a^..87ec0493a` judged; judge F not read.
