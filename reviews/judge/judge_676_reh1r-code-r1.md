# Judge 676: REH1r code, a routine command not yet in its routine on the replayed day is exercised (story/reh1r-code @ 5695be3d5)

**PASS, code round 1 of 2, judge F (judge E the other; I did not read its verdict). Lane 1, two judges.** Own session
(session_01A8XfbTUVgeeEpqatHaWbtP). Labels: strong, some, reasoning only.

## Criteria

| Criterion | Verdict | My evidence (strong unless marked) |
|---|---|---|
| R1 before `since`, exercised | MET | the 21 Oct evening test: "7 commands done", seven exercised, `closes read`'s `since` 2026-10-22; plant P1 (`since` ignored) fails 7 tests; P6 (exercised counted as failed) fails 5 |
| R2 on and after `since`, the real rule | MET | the 22 Oct evening fails on its own five; the boundary day is the routine's; P2 (`<` made `<=`) fails 4 |
| R3 the sources | MET | each constant equals the table; I re-read every source commit (IST): a2b2ad8c6 22 Oct 03:09, e6010ac0a 05:02, 96af942cd 04:29, cae76af89 05:58, 49aa26951 04:39, 51cab79b0 23 Oct 22:42; first outputs 47a4ff7a8 23 Oct 08:40, d88023df0 08:51, 3decf6a60 08:45, 936611423 22 Oct 19:54, 2428dac17 24 Oct 08:41. P3 (index-close 22 Oct) fails 2, P4 (evening 21 Oct) fails 3 |
| R4 empty | MET | the daily run has no `since`; P7 (the `NO_EXERCISED` guard dropped) fails 2 |
| R5 real runs unchanged | MET | `routines.py` is imported only by `rehearsal/cli.py` and `rehearse.py`; full suite below |
| The line names the reason | MET | "(in its routine from <since>)" tested at the line; P5 (qualifier dropped) fails 1, P8 (`since` never recorded) fails 2, P9 (`since` recorded for a lab edition) fails 4 |
| 674.1 minor (Finding cites 5c3195ba0) | MET | story line now names 5c3195ba0, 21 Oct 22:44 UTC (22 Oct 04:14 IST), checked with `git show -s` |

## Gates (trial merge: main eb1b5a817 is an ancestor of 5695be3d5, so the merge is the head itself; token kept)

ruff check, format (2,746 files), imports (2,909 files), record scan (9,531 files): clean. Full suite: 17,570 passed,
1 skipped, 13 xfailed, 0 failed. The skip is `tests/intraday/test_feed_tls.py:190`, "could not import 'growwapi'":
this container has no Groww SDK; it is not related to this change.

**Plants:** 9 planted, 9 caught, one at a time in a worktree of 5695be3d5 (`tests/rehearsal`, 265 tests), each restored
with `git checkout --` and `__pycache__` cleared; the worktree ended clean.

## The orchestrator's question: "lab close failed: ... (RuntimeError)" in run 20261025T055423Z-26bf03

- **It is marked exercised (strong evidence).** The item is inside "not live in real runs (exercised): ...", and the
  routine ended "7 commands done". It has no "(in its routine from ...)" note by design: `lab close` uses its edition key
  (REH1k), and `forecast_lab.live_from.evening` is 2026-10-23, so on 21 Oct it is in `not_live`. The question's premise
  is not right: `lab close` joined the evening routine only with 5c3195ba0, on 22 Oct at 04:14 IST, after 21 Oct's 19:53.
- **Cause, reproduced (strong evidence).** I took a worktree of the rehearsal's own checkout commit d736e318e ("data as
  of 2026-10-21T19:53"), set the rehearsal mode for 21 Oct with the replay clock at 19:58 IST, and called
  `forecast_lab.wiring.build_composer("evening")`. Nothing was posted. It raised a bare `RuntimeError`: "G13b's records
  could not be read verified from Drive: data/price_ranges/v1/live: no receipts under it ...; .../scores: ...;
  .../backfill: ...". `guarded` prints only the error's type, so the line says "(RuntimeError)".
- **This is a true replay outcome.** G13b's first receipts reached `main` later: d6958a422 (back-fill) and fc01f6892
  (scores) on 22 Oct at 00:04 IST, and the first live receipts with f03430276 on 22 Oct at 15:23 IST
  (`daily.live_from.price_ranges` is 2026-10-22). On 21 Oct a real `lab close` would have stopped the same way.
- **It is not a finding of this round.** REH1r's code handles it as intended: the result is exercised, never failed. One
  thing is outside REH1r: the posted line gives only the error's type, not its reason. That is FL1's `guarded` design
  ("the error's type"). If the owner wants the reason in the line, it is a separate FL1 item. It is not a defect here.

## Findings

None blocking, none should-fix.

## Notes

- I saw only judge E's row in the README when I appended mine, after my checks and the reproduction above were done.
  I did not read its file.
