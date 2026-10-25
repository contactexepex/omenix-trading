# Judge 619: REH1l code, rehearsal pre-open serving and clock cell, `story/reh1l-preopen-serving` at 2d8ccb8d4 (round 1 of 2, judge K, judge 2 of 2)

**PASS, lane 1.** No findings.

**Scope:** REH1l's own diff, `git diff 34aad0d85...2d8ccb8d4` (REH1k's 34aad0d85 is judged in its own round). I did
not read judge F's verdict.

**Gates.** A trial merge of 2d8ccb8d4d617cc977933a7dd0763dd72cfb54b2 into origin/main 6e332c6f2 is clean. On it, with
the Slack token set:
- `pytest -n auto`: 16,540 passed, 1 skipped, 14 xfailed, exit 0.
- ruff check and format clean; `check_imports` (2,759 files), `check_records` and `check_numbers` clean.
- **No test posted to Slack:** all three channels are empty for 19:59:54-20:10:40 UTC.

## Criteria (the orchestrator's three checks first)

| Check | Verdict | Own evidence |
|---|---|---|
| Real-run serving, records and day cells unchanged | MET | Real serving: `RecordedPreopenPart` exists only in a rehearsal (`rehearsed_preopen_parts`). Real day cell: `day_cell()` is `warning() or ("ok" if CLOCK_OK else status)`. A real `ClockCheck` always has two servers, so `CLOCK_PARTIAL` or `CLOCK_UNCHECKED` always has a check with skew None and a non-empty warning (`clock.py:31-53`); the cell is the same as the old `warning or "ok"` in every real state. Other readers of the reading use its `status` (`quotes/capture_log.py:53-65`, `intraday/recorder.py:227`, `v4_pack/builder.py:48` requires `clock_ok`), which is unchanged |
| No bytes served before their seen time | MET | `RecordedPreopenPart.answer` sleeps until `seen` when `seen > now`; plant "sleep removed" caught. `ServedOnce.pick` is unchanged (never the same copy twice, never back in time) |
| No rehearsal writes "ok" for an unchecked clock | MET | `RehearsalClockCheck` returns `ClockReading(CLOCK_UNCHECKED, ())`: no checks, so no warning, and its cell is `clock_unchecked`. Test L3 at the recorder: the day row's clock is `clock_unchecked`. Plants caught: "day cell ok for unchecked", "rehearsal clock reads ok", "record back to `warning or "ok"`" |
| L1: copies at or after the window's close dropped before the pick | MET | `recorded_preopen.py:55-57`: `seen < closes`. 09:10:59 is served, 09:11:00 is not. Plants caught: close inclusive (`<=`), filter removed |
| L2: the 23 Oct record replayed part by part | MET | the test reads the committed receipts: gift 08:40:00, fo_list 09:08:30, nifty 09:10:59, banknifty none; 22 Oct none (non-vacuous: 23 Oct's folder exists) |
| L3: the replay clock said once, last, in the exercised line | MET | `rehearse.py` passes `(REPLAY_CLOCK,)`; `exercised_line` appends the fixed items last and alone still make a line. Plant "line dropped" caught |
| Size, design | MET | small edits; the `PreopenRecorder` now takes `clock: Callable[[], ClockReading]` (one reading for warning and cell, no second check) |

## Files read (the whole diff, and the changed functions with their callers)

- `fno/intraday/clock.py` (the new `day_cell`), `fno/preopen/record.py` and `fno/preopen/wiring.py` (the reading
  passed once).
- `fno/rehearsal/recorded_preopen.py`, `serving.py`, `preopen_wiring.py`, `exercised_line.py` and `rehearse.py`.
- The tests `tests/rehearsal/test_preopen_window.py`, `test_recorded_preopen.py`, `test_exercised_line.py` and
  `test_checkout.py`, and `tests/preopen/desk.py`.

## Plants

- **Mine: 7, all caught:** day cell "ok" for unchecked; close inclusive; close filter removed; rehearsal clock reads
  ok; replay-clock item dropped; recorder back to `warning or "ok"`; copies served before their seen time.

## Notes

- In a rehearsal, A16's per-mark line no longer carries "not checked" (`intraday/recorder.py:117` reads `warning()`).
  Its rows keep `clock_status=clock_unchecked`, and the exercised line says it once. This is by design and costs
  nothing in real runs.
- `NOT_CHECKED` stays in `preopen_wiring.py` for `card_label.py`; it is used, not dead.
