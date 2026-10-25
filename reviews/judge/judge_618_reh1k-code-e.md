# Judge 618: REH1k code, the lab's editions in a rehearsal of a day before their live date (story/reh1k-lab-editions @ 34aad0d85), judge E

**FAIL (round 1 of 2; 1 should-fix, 1 minor). Lane 1** (posts to #fno-forecast and #fno-desk). Judge E, judge 1 of
2, own session; judge B's verdict not read. Text passed in 611.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| K1 live dates | MET | `build_edition` takes `lab_live` (`forecast_lab/wiring.py:57-62,119-123`), which is `rehearsed_live` and so returns no notes with no mode. My K1 (the root on the real dates) and K1b (`<` made `<=` in `_not_live_editions`) caught |
| K2 note in every post | MET | `note_this_process` sets `FNO_REHEARSAL_NOT_LIVE` only for a note (None leaves the process as is). K2 (not set) 3 failed; K5 (a note set with no mode) caught |
| K3 not a routine failure | PARTLY | K3 (live key ignored), K3b (exercised outcome dropped), K8 (single-command shortcut) and K9 (no raise without a sink) caught. The **ok** half is untested (finding 1) |
| K4 once | MET | One `alerts.send`; my per-command plant is equivalent (one live-key command per routine) |
| K5 real runs unchanged | MET | No mode: same live dates, no note, no wrapper. `lab preview` is pinned to the real dates (`:132`; my plant there is equivalent outside a rehearsal, minor 1). The real morning replay below posts with the label only |
| Evening never takes a real morning record as its own | MET | `records(EVENING)` and `records(edition)` are both the evening's for `lab close` (`:71-72,110-116`). The morning's `Confirmation` reads earlier evenings, as on the day |
| Flake fix (REH1h test) | MET, hides nothing | It patches `build_manifest_folder`, the builder the writers call, not the constant. The test still asserts the row lands in the rehearsal checkout's folder (`test_recorded_archive_wiring.py:106`), so a write elsewhere would still fail it. `git status` of my main checkout is clean after the runs |
| Gates | MET | Trial merge baf896ca0 with origin/main b93212b8f: ruff clean, format clean (2,629 files), imports clean (2,758 files), record scan clean (9,253 files). Full suite with the token kept: **16,528 passed, 14 xfailed, 0 failed** (no skip: `growwapi` is installed now) |

## My 23 Oct morning replay (`rehearse morning --day 2026-10-23`, run 20261024T194516Z-7ff022, trial merge)

"lab open 2026-10-23: report to #fno-forecast: posted"; "0 of 0 alert(s)"; certify ok. It ended "3 commands done", with
no exercised line: the edition is live on 23 Oct. Read back from #fno-forecast: one post, under the bold "DRY RUN,
2026-10-23 replay, not a real trading day" label, with no not-live note. Drive `dryrun/20261024T194516Z-7ff022/`. Only
#fno-forecast and #fno-desk are written by the routine.

## Findings

1. **Should fix: an exercised command that succeeds is not tested.**
   - My plant K7 records an exit 0 as failed: `not_live_result` with `{"status": "failed"}` for code 0
     (`exercised_line.py:43-46`). It passed all 398 tests in `tests/rehearsal` and `tests/forecast_lab`.
   - The design says the line reads "lab open ok" for a run that worked. The 22 Oct evening sample (posted, exit 0)
     shows the path works today, but no test would catch it breaking (rule 4).
   - Fix: one case where the not-live command exits 0 and the line names "lab close ok" (and nothing is in "failed").

## Minor

1. `build_preview` passes the real dates (`:132`), but no test runs it under the mode, so a plant that drops the
   argument survives. It is equivalent outside a rehearsal, and preview is never part of one. Pin it with one test
   under the mode, or leave it as stated.

## Plants

11 planted: 8 caught; 3 survived. Two of the three are equivalent in practice (one post per command; preview under
the mode). The third is finding 1.

## Addendum 1

**REH1k code, round 2 of 2 (story/reh1k-lab-editions @ cd7cf403d): PASS. Lane 1.** Judge E, judge 1 of 2; judge
B's verdict not read.

- **No code changed this round.** `git diff 34aad0d85 cd7cf403d -- fno/forecast_lab fno/rehearsal` is empty. The two
  `fno/forecast_v5_v1/` files in `git diff -- fno/` come from main, by the G14 amendment 2 merge (110cfae03, the
  branch's second parent, on main). The round changes `tests/rehearsal/test_lab_editions.py` and the Claims only.

| Round-1 item | Outcome | My evidence |
|---|---|---|
| SF1: an exercised command that succeeds was untested | **Accepted, fixed** | `test_a_not_live_command_that_exits_0_is_exercised_ok_and_nothing_failed` asserts exercised `{"status": "ok"}`, "2 commands done" and the line "... lab open ok". My K7 (exit 0 recorded as failed): **1 failed**, caught |
| m1: preview under the mode | Fixed | My K6 (preview built without the real dates): **2 failed**, caught |

K4 (one post per command) still passes, and stays equivalent: each routine has exactly one live-key command.

**Gates** on trial merge a2530415b with origin/main e982de095: ruff clean, format clean (2,629 files), imports clean
(2,758 files), record scan clean (9,257 files). Full suite with the token kept: **16,533 passed, 14 xfailed, 0
failed**, matching the builder's count.

## Findings

None blocking, none should-fix, none minor.
