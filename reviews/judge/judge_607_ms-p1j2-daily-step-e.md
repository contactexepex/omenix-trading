# Judge 607: MS-P1j2, the market school's daily step (story/ms-p1j-daily-steps-r2 @ 526bccb61, code f21525614), judge E

**PASS (round 1 of 2). Lane 1, money piece (paper fills): judge 2 of 2.** Judge E, own session; the other judge's
verdict not read. `school.enabled` stays false. Labels: strong, some, reasoning only.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| 1 Place | MET | On the trial merge: `... card, price_distribution, premium_ranges, school, price_distribution_scores, ..., v4_deadline, candles, close_read, close_recheck`. M1 (row renamed) 15 failed; M1b (row moved one place, after G13's scores) 5 failed |
| 2 Command | MET | `school_run` gives `school run --session D` as a `CommandStep` with no pathspecs. M10 (no session) 7 failed |
| 3 Switch off | MET | `school:OFF`; the harness test asserts nothing under `research/school/` reaches `origin` |
| 4 Not retried | MET | A failed step is rerun only when its result carries `RETRY` true (`desk/run_log.py:81-82`), and the school step never sets it. The alert ends with `RERUN_FINAL`'s words. M2 (note dropped) 3 failed; M6 (every failed step retried) 17 failed |
| 5 Hang | MET | O1's `CommandStep` limit, unchanged; the builder's two tests |
| 6 Public log | MET | Four templates. M8 (`school:TOO_LATE` removed) and M12 (`school:STOPPED` removed) each caught |
| 7 Closed day | MET | `test_a_closed_day_never_starts_the_school`: the log holds only `skipped` |
| 8 Rehearsal | MET | `test_rehearsed_stores.py`: both Drives are `DryrunDrive` under `dryrun/<run_id>`; a real replace is refused; the real Drive is used outside a rehearsal. In a clone, `ROOT`, `REPOSITORY` and the dashcam's publisher are the clone, and the accounts and the fleet take `ROOT` (`school/accounts/wiring.py:14`, `school/wiring.py:53`) |
| 9 15:25 cutoff | MET | `StartsBy` compares the full datetime, so a past day's run is refused. M3 (`>=`, the boundary), M4 (guard removed), M5 (time of day only, so past days pass) and M9 (15:30) each caught. Refused is alerted once with the named line |
| 10 Harness | MET | The child runs `cmd_run` on its own settings file outside the checkout, with `school.enabled` false. M7 (switch true in that file) 2 failed |
| Gates | MET | Trial merge 76a60c629 with origin/main ddb0c0510: ruff clean, format clean (2,566 files), imports clean (2,695 files), record scan clean (9,172 files). Full suite with the token kept: **16,118 passed, 1 skipped (`growwapi`), 14 xfailed, 0 failed** |

## Placement checked on the run logs

`journal/runs/` (strong): `quotes_done` started at 15:18:39 (21 Oct), 15:22:05 (22 Oct) and 15:18:28 (23 Oct);
`premium_ranges` ended at 15:22:27 (22 Oct) and 15:19:07 (23 Oct). So the school would have started about 15:22:30 and
15:19:10: 2.5 and 6 minutes inside the 15:25 cutoff. G13d keeps its 15:30 margin, since it still runs first. The moved
G13 score-row test now pins `price_distribution_scores` right after `school`, which keeps its rule (G13d's seal first).

## Plants

13 planted, 13 caught (M1-M10, M1b, M12; each alone on `tests/daily`, `tests/e2e/test_school_step.py`,
`tests/school/test_rehearsed_stores.py`, `tests/price_ranges/test_score_steps.py` and
`tests/health/test_desk_and_data_checks.py`, 195 tests; restored after each).

## Findings

None blocking, none should-fix, none minor.

## Rulings and conditions (not findings on this branch)

1. **The builder's open item 1** (a manual `school run` after the close seals the session's decisions, and law 6 then
   refuses every fill): out of scope here, rightly, since this step can never start after 15:25. It fails closed, with
   no trade and no hindsight decision. But **the switch-on commit should wait for a first-seal cutoff in j's runner**
   (or a runbook line forbidding a manual run after 15:25). Otherwise one manual run wastes a session's record
   [reasoning only].
2. **The 15:25 cutoff** leaves about 2.5 minutes on a 22 Oct-like day. A slower day refuses the school (alerted, with
   no session); revisit it from the first enabled sessions' logs, as the story says.
