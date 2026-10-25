# Judge 175: A14 schedule fix (`story/a14-schedule`, lane 1: a workflow schedule and margins; judge E)

Date: 15 Oct 2026 (UTC). Branch at **e2b4c7836cf4e0334f3841be018b66d0d5649c8b**, one commit on `main`. Builder
session 01Vm1WnH8i9waM8EJG8zwWqg. Diff: 6 files, +42/-18 (the workflow, `broker_approvals.py`, `job.py`, two test
files, the register row).

## Verdict: PASS; 2 notes

| Check | Status | Evidence (mine) |
|---|---|---|
| The claimed defect is real | MET | The Actions API for `nse-margins.yml` returns `total_count: 0`, so it has never run. `research/data/margins/margins.csv` on `main` has 1 line (the header). So C2 has no NSE margin row and refuses every trade. Strong |
| The schedule | MET | Cron `15 2 * * *` (07:45 IST) and `0 3 * * *` (08:30 IST). `workflow_dispatch` is kept, as is `concurrency` with no cancel. A second run prints "nothing new" and writes nothing (existing test `test_a_second_run_changes_nothing`) |
| The false-alert root cause | MET | Before the fix, `pending_days` counted 7-13 Oct, whose rows could never be written (`any_by` is false before 14 Oct), so every run would alert. Now days before `first_day()` (the earliest `passed_on`) are not pending. With no approval at all, `first` is None and every day is still refused by name |
| Nothing written before `passed_on` (judge 77) | MET | The per-code gate `checked = [... if self.check.approves(row.structure, day)]` is unchanged. Unapproved codes are still printed, not written (`test_one_side_rows`). The new test archives 8 days of files with every code approved on DAY and asserts that only DAY's rows exist |
| The replaced test is not weakened | MET | The removed case, `after_the_day` (an approval dated after the day), now belongs to the "not pending" path. Its invariant (no row before `passed_on`) is asserted more strongly by the new first-run test: 7 earlier days with files present, none written, no alert. The `none` case is kept |
| Weekend runs find Monday's file | MET | `due_session` on a Saturday or Sunday gives Monday. Monday's `i1` file is written the previous trading evening. NSE's own files show this: `nsccl.20261012.i1.zip` (Mon 12 Oct) was created **9 Oct 22:36 IST**, and `nsccl.20261005.i1.zip` (Mon 5 Oct) **1 Oct 22:32 IST** (2 Oct was a holiday). Both SHA-256s equal the `span-bod` manifest rows. So the weekend runs archive it and write Monday's rows: point in time is safe (created before 09:00 on its day), and the Monday morning runs find nothing new. Strong |
| My plants (4, reverted) | all caught | First-day filter removed: 1 failed. Every row written regardless of code approval: 2 failed. `>=` changed to `>`: 1 failed. `first_day` using max instead of min: 2 failed |
| Gates on e2b4c783 | MET | `tests/nse_margins` 69 passed. Ruff clean; format clean (1,074 files); `check_imports` clean. Full suite (full history): 5,877 passed, 1 failed: `tests/intraday/test_two_clones.py::test_after_a_normal_pull_the_second_run_writes_no_duplicate`. That test passed alone twice on this commit and on `origin/main`; it is a timing flake in code this branch does not touch |
| Register | MET | Row "A14 schedule (O)" added in the same commit |

## Notes

1. **GitHub's late starts (judge 52 add. 1):** this repository's scheduled runs start 4-5 h late and some slots are
   skipped. The margin row must land before the 15:00 decision. The window is wide: the file is out from about 22:30
   the evening before, two slots a day, and weekend runs fill Monday early. A late start is therefore normally
   harmless, and a missed day only makes C2 refuse (fail-safe, never a money risk). Check the first week's start
   times. If a weekday row is ever missing by 14:30 IST, the owner's 15 Oct rule ("timed jobs on routines") applies:
   start it from the 14:33 routine or a morning routine.
2. The workflow comment states the late-start point correctly: the 09:00 cutoff applies to NSE's file, not to the run.

**Verdict: PASS for e2b4c7836cf4e0334f3841be018b66d0d5649c8b.** Merge with the full suite on the merged tree.
