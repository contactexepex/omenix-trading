# Judge 656: A20a, a 06:00 IST fo-masters slot for A14c part 2's lot check

Branch `story/a20-lots-early-slot` at `7ff32a3dc` (text d842defca, workflow and tests 7ff32a3dc). **PASS, lane 1**
(one judge). Judge session 01BvZZzF4XR48qNHNxLydQhf.

## Criteria

| Item | Verdict | Evidence |
|---|---|---|
| Lots filed under the run's IST date | MET | `fo_masters/cli.py`: the day is `now_ist().date()`. 00:30 UTC is 06:00 IST on the same date (`test_the_06_00_slot_runs_on_the_ist_day_it_files_under`); path `.../fo-lot-sizes/2026/10/26/fo_mktlots.csv` (test) |
| Write-once: a second run the same day keeps the first bytes | MET | `SnapshotTaker` returns `ALREADY` and the store keeps the first copy even when NSE's bytes changed (`test_the_lots_are_filed_under_the_run_day_and_a_later_run_writes_nothing_twice`) |
| Ban list at 06:00 is the run day's, stale check intact | MET | `job.py` `ban_list_step` unchanged: it takes NSE's current list, filed under the date it names, and fails on a trading day unless that day's list is archived. Test: Monday's list at 06:00 filed under Monday; a later run writes no second file |
| 18:45 next-session filing untouched | MET | no change to `fno/`; the `15 13 * * *` slot is unchanged |
| The test pins all four crons | MET | `test_four_daily_slots_early_morning_retry_and_evening` pins the ordered list. Plants: the 06:00 line removed, and 18:45 moved to 19:45; both caught |
| Concurrency | MET | `concurrency: group: fo-masters, cancel-in-progress: false`: a late 06:00 run and the 07:45 run never overlap |
| Gates | MET | trial merge with main: ruff, format, imports, check_records and check_numbers clean; full suite 16765 passed, 13 xfailed, 0 failed |

## Plants

2 planted (the new cron removed; the 18:45 slot moved), 2 caught.

## Notes

- The 06:00 slot's own lateness is not measured yet. "About 11:00" assumes the 07:45 slot's 4.5-5 h delay (some
  evidence: 3 days). The first week's start times show whether the slot lands before 14:05.
- A14c part 2's story still says "A20a archives it from 07:45 IST" (judge 634 add. 1, finding 1). That is the A14c
  builder's to correct; this slot does not settle the loss risk until its arrival times are measured.
- Lane-1 data path: no code under `fno/` changed; the workflow runs the same command at one more time.
