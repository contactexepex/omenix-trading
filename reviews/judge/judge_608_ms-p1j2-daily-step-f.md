# Judge 608: MS-P1j2, the market school's daily step (story/ms-p1j-daily-steps-r2 @ 526bccb61, code f21525614)

**PASS (3 minor), judge 1 of 2 (a money piece: paper fills). Lane 1.** Judge F, own session
(session_01A8XfbTUVgeeEpqatHaWbtP); no contact with the second judge. Labels: strong, some, reasoning only.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| 1 | place | MET | `constants_operations.py:69`, right after `premium_ranges`, after `quotes_done`, before `v4_deadline`; close reads last; my swap plant caught (6 tests) |
| 2 | command | MET | `wiring.py:47-49` `school run --session D` through `CommandStep` (no pathspecs; the command commits its own files, as `desk book1` does); plant without the session caught |
| 3 | switch off | MET | e2e: `school:OFF`, no `research/school/` on `origin` |
| 4 | stop or raise | MET | `Alerted(..., note=SCHOOL_NOT_RETRIED)` (`wiring.py:163-168`); the alert ends with `RERUN_FINAL`'s words; a rerun never starts it: `Alerted` never marks `retry`, and my plant "`_retried` ignores `retry`" is caught |
| 5 | hang | MET | O1's `COMMAND_LIMIT_SECONDS`; e2e past and inside the limit |
| 6 | public log | MET | four templates (`reason_codes.py:100-105`); plants removing TOO_LATE and STOPPED caught; other lines give `command:ok` / `command:exit_1`, and their text stays private (test) |
| 7 | closed day | MET | e2e Saturday: log holds only `skipped` |
| 8 | rehearsal | MET | `test_rehearsed_stores.py`: dashcam and accounts write only under `dryrun/`; a real replace is refused; real Drive outside a rehearsal; the clone's `ROOT`, `REPOSITORY` and receipt publisher all point at the clone, whose `origin` is a local bare repository. My plant bypassing `rehearsed_drive` is caught. `StartsBy` takes `now_ist`, which reads REH1's installed replay clock (`models.py:18-29`), so a rehearsal of a past day is not refused |
| 9 | late start | MET | `StartsBy` (`steps.py:146-158`); 15:25:00 runs, 15:25:00.000001 is refused, a UTC clock is compared in IST; plants `>=`, guard removed, 15:30, and the clock's zone instead of IST all caught |
| 10 | harness | MET | `school_runs` writes its own `school_off.yaml` outside the checkout; plant `config=None` caught |
| gates | full suite, ruff, imports, records | MET | trial merge with main 63457300a (clean): **16,118 passed, 1 skipped, 14 xfailed** (token kept); ruff, format (2,566 files), `check_imports`, `check_records` (9,168 files) clean |
| QR1-6 | text, gap list, self-review, plants, cases, sample | MET | the gap list names each item left out and why; the self-review's 8 items answered; the plant table matches my own plants |

**The orchestrator's points.**
- G13's moved row (`test_score_steps.py`) still states G13d's rule in its comment. With the school pinned right after
  `premium_ranges`, the order G13d → school → scores holds, and my swap plant fails both tests.
- The O2 harness fix is real: the child gets its own settings file.
- Real timing [some evidence, 3 sessions of `journal/runs/`]: `premium_ranges` started 15:22:27 (22 Oct) and
  15:18:55 (23 Oct). The school would start about 15:19-15:23, leaving 2-6 minutes before 15:25.

## Minor

1. **The builder's open item 1 (no first-seal cutoff in the runner for a manual `school run` after 15:30).** It is not
   in this change, and law 6 refuses every fill, so no money moves. But a late first manual run seals the whole
   session with no fills, and the day is lost. It should be fixed in j's runner (refuse a first seal after the last
   start, outside `--replay`) **before `school.enabled` is turned on**: a condition for the switch commit, not for
   this merge [reasoning only].
2. On a slow day (`quotes_done` after about 15:24) the school is refused as `school:TOO_LATE`. That is visible and
   alerted, and the story revisits 15:25 from the first enabled sessions. Report the first ten refusals, if any.
3. The rerun rule rests on O1's generic skip of recorded steps. A test in `tests/daily` that names `school` beside
   `RETRIED_ON_RERUN` would make it explicit. Today the e2e rerun tests carry it.

## Plants

17 planted on 526bccb61, one at a time, each restored and `__pycache__` cleared: **16 caught, 0 survived**. One was
equivalent: adding `school` to the desk's `RETRIED_ON_RERUN` does nothing, as that list governs only E3's internal
steps (`daily_run.py:281`). Caught: swap with `premium_ranges`; note dropped; `>=`; guard removed; 15:30; clock zone;
no `--session`; TOO_LATE code removed; STOPPED code removed; harness reads `config.yaml`; `rehearsed_drive` bypassed;
`status_alerts=False`; `FAILED_ALERT` without its note; `_retried` ignores `retry`; row renamed.

## Notes

- `school.enabled` stays false (not in this change). Merge needs the second judge's PASS too (JUDGE.md, two judges).
