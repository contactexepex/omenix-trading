# Judge 675: REH1r code, a command not yet in its routine is exercised (story/reh1r-code @ 5695be3d5), judge E

**PASS (round 1 of 2; no blocking, should-fix or minor finding). Lane 1** (it changes what a rehearsal counts as a
routine's failure; judge 1 of 2). Judge E, own session; judge F's verdict not read.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| R1 before `since`, exercised | MET | `Command.exercised_on`: a not-live key, or `day < since`. `run_routine` sets apart every such command; its outcome goes into `exercised` with `since`, never into `failed`. P1 (`since` ignored): 7 failed. P4 (set-apart commands counted as failed): 5 failed. P6 (the line without "(in its routine from ...)"): 1 failed |
| R2 on and after `since`, the real rule | MET | P2 (`<` made `<=`): 4 failed. The 22 Oct and 24 Oct tests hold the real rule on those days |
| R3 the constants are the table's rows | MET | The four constants equal the 673.1 table: pre-open 23 Oct, index-close 23 Oct, certify 24 Oct, evening 22 Oct. The lab editions keep their key and take no `since`. P3 (`EVENING_SINCE` 21 Oct): 3 failed. P8 (index-close 22 Oct): 2 failed |
| R4 no `since`, never set apart; a set-apart command needs a record | MET | P5 (the `NO_EXERCISED` guard dropped): 2 failed. P7 (a `since` recorded for a keyed edition): 4 failed |
| R5 real runs unchanged | MET | `routines.py` is read only by the rehearsal (`cli.py`, `rehearse.py`); `not_live_result` adds `since` only when given. The full suite is green |
| Gates | MET | The branch already holds origin/main eb1b5a817, so its tip is the trial merge. ruff clean, format clean (2,746 files), check_imports clean (2,909 files), record scan clean (9,531 files). Full suite with the token kept: **17,571 passed, 13 xfailed, 0 failed** |

## Plants

8 planted, each alone on `tests/rehearsal` (265 tests), restored after with `git checkout --`. 8 caught.

## The orchestrator's question: "lab close failed: ... (RuntimeError)" in the 21 Oct sample

- **It is marked exercised.** The sample's own line reads "not live in real runs (exercised): ...; lab close failed:
  ...", and the routine ended "7 commands done", so it is not counted as a failure.
  - It is set apart by REH1k's edition key: `forecast_lab.live_from.evening` is 23 Oct.
  - That is why it carries no "(in its routine from ...)". That qualifier is only for a `since`, and a keyed edition
    takes none (P7 caught).
- **The premise is off by a day.** 5c3195ba0 was committed on 21 Oct at 22:44 UTC, which is 22 Oct 04:14 IST: after
  21 Oct's 19:53 evening. So on 21 Oct `lab close` was neither in its routine nor live.
- **Its cause is a true replay outcome.** Strong evidence by data, plus reasoning; not reproduced by me, since
  re-running posts to #fno-desk.
  - `build_composer` syncs G13b's Drive areas first and raises `RuntimeError` on any sync problem
    (`forecast_lab/wiring.py:101-103`). `guarded` reports only the error class (`edition_run.py:155`).
  - G13b's first live receipt (`receipts/data/price_ranges/v1/live/2026/10/*_2026-10-22_1545`) was committed on
    22 Oct at about 15:23 IST (f03430276).
  - So the record as of 21 Oct 19:53 has no receipts under `data/price_ranges/v1/live`. That is exactly the cause REH1k
    reproduced for 22 Oct's morning ("no receipts under it", in this story's REH1k samples).
- **Not this round's, and no finding.** The edition's input did not exist that day, and REH1r does not touch keyed
  editions. A separate story would only be needed for the line to show the error's reason as well as its class.

## The builder's answer, verified (the orchestrator's follow-up)

- **Both not live and before its `since`: the line form.** `run_routine` gives `since = None if c.live_key in
  not_live else c.since`. A keyed edition's item therefore carries no "(in its routine from ...)", whatever its
  `since`. No command today has both a key and a `since` (R3 test), and P7 (a `since` recorded for a keyed edition)
  was caught.
- **The receipts on main at that time.** At 21 Oct 19:53 IST, main's last commit was 4398c013d (14:21:56 UTC), and its
  tree holds **0** receipts under `receipts/data/price_ranges/`, in all three areas `build_composer` syncs (live,
  scores, backfill). Today all three hold receipts.
  - `DriveCache.sync` adds `NO_RECEIPTS` ("no receipts under it") to its problems (`drive_cache.py:47`), and
    `build_composer` turns any problem into its UNSYNCED `RuntimeError`.
  - The builder's cause is confirmed by data and code, still not reproduced.
