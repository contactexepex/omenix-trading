# Judge 569: O1's DRY2 fixes R1 (the indices' early limit) and R2 (one failed step never ends the day)

Judge B, 24 Oct 2026. Story/o1-r1r2-step-safety at e8dc9498d (from main d76c18adf); lane 1, money path. Story:
`docs/stories/O1-daily-run.md`, "Fix after DRY2".

**Verdict: FAIL, round 1 of 2: two should-fixes.** R1 is correct; R2's catch is correct but changes the rerun contract
unstated, and one claimed refusal is untested.

## R1: the indices wait for their own early limit

- **The limit:** `INDEX_EARLIEST_START = earliest_start(INDEX_WINDOW_START)`, 14:44, by the same arithmetic as NIFTY's
  14:38.
- **It now holds for a waiting part:** `start_due` requires both `_waited_for` and `_due`. `next_start` counts a waiting
  part once its predecessor has ended, so the run's waiter wakes at 14:44 when NIFTY ends earlier, and `service` calls
  `start_due` after committing NIFTY.
- **My plants:** the indices given NIFTY's limit (caught); `next_start` ignoring a waiting part (caught).

## R2: an unexpected error fails one step

- **The catch:** `_run_step` re-raises `CommitFailed` and `GitFailed`, so those still stop the run (my plant
  swallowing them fails 8 tests). Any other `Exception` becomes `STEP_FAILED` with its type and one line, plus one
  alert.
- **Downstream reads, checked:**
  - `fills` reads the snapshot's and decisions' logged results, so the `NEEDS` refusal is right.
  - `exits` reviews through its own gate.
  - `decisions` only observes the books' commits, so a failed pack leaves every book late. It never decides on a missing
    pack.
  - `fill` does not read the versions step.
  - A failed exits step makes every book unreviewed the next session, so no book opens anything new.
  - A failed owner-timing step already blocks opens (`_unfilled`).
- **My plant dropping the alert** is caught.

**Gates on e8dc9498d (run by me):** 15,115 passed, 1 skipped, 15 xfailed; ruff, format and check_imports clean. It
merges cleanly with current main.

## SF1 (should-fix): a step failed by an unexpected error is never retried by a same-day rerun, an unstated change

- **Path:**
  - Before R2, an unexpected exception in a step propagated out of `DailyRun.run`, so the step was never recorded and a
    rerun repeated it.
  - Now `_run_step` records it as `STEP_FAILED`. `RunLog.done` is "in the log", and `record` refuses a second record
    ("a run never repeats a step"), so every rerun that day skips it.
- **A normal case:** a transient failure inside `exits`, such as a Drive or HTTP timeout raising from a read the
  review makes. The positions whose exits were due today stay open until the next session's run, and the owner's
  rerun (CLAUDE.md: "A rerun the same day skips the steps already done") cannot recover it.
  - Tomorrow's `_unreviewed` blocks new opens, but the due exits themselves are a day late. On a stop-loss exit that is
    real paper loss.
- **The claims do not say this.** The story's R2 section describes the run going on, not that a failed step is final
  for the day.
- **Test it must pass:** pick one rule and pin it.
  - (a) A rerun after a step failed by an unexpected error runs that step again, with its inputs re-checked and nothing
    doubled, at least for exits.
  - (b) If the owner or orchestrator rules the failure final, the claims say so plainly, and a test pins that a rerun
    leaves it failed, with the alert naming that a rerun will not retry it.
- **Fix (reasoning only):** record unexpected failures so that `done()` does not count them (for example
  `done = step in steps and not failed`), with `record` replacing a failed entry. Exits and fills are already built to
  be rerun safely after a crash.

## SF2 (should-fix, test only): fills' refusal after failed decisions is untested

- **The plant that survives:** `NEEDS = {"fills": ("snapshot",)}`, with decisions dropped, passes `tests/daily`,
  `tests/timetable` and `tests/desk` (357 passed).
- **Why it matters:** the claims state the fills step is refused when either input fails, and fills decides trades.
  `test_step_error_run.py` plants only the snapshot's failure.
- **Test it must pass:** with the decisions step failed by an unexpected error, fills is `refused` naming decisions,
  and no fill is made. The plant must fail it.

## Addendum 1 (pending: round 2 not yet judged)

**Status: PENDING.** The head at the time of writing is f0bb2aa9c. The session is handing over (the orchestrator,
usage at 100%). The next judge finishes round 2 (the last allowed) on the builder's SF1 and SF2 commit.

**Already checked on f0bb2aa9c (holds):**
- **Fail closed:** fills is refused when its input step has not run, as well as when it failed.
- **One rule:** `run_log.problem_steps` and `book_results` give `{}` for a failed or refused step.
- **The scoreboard's `committed_runs`** is guarded. `uncollected()` raised `AttributeError` on a failed decisions step
  (I reproduced it); it now reads no books.
- **The reader list** matches my own map: opening_runs, reviews, health, the scoreboard's runs, snapshot_ids and
  missed, and `_unreviewed` are safe. The card's decisions reader goes in T1d, merged together with R2.

**What remains to check on the next head:**
1. **SF1, under the orchestrator's ruling (24 Oct 06:24):** a step failed by an unexpected error is recorded failed
   and retried on a same-day rerun, while a finished step never repeats.
   - Verify `RunLog.done` and `record`: a failed entry is replaced, and an OK or refused one never is.
   - Verify the builder's table of each desk step as safe or not safe to retry, against the code: in particular,
     whether a retried `fills` or `exits` after a partial write can double a fill, an exit or a ledger row, and how the
     partly written step's commit behaves. A step not safe to retry stays final, with its reason stated.
   - A test: a rerun after a planted exits failure runs exits again, with nothing doubled.
2. **SF2:** with the decisions step failed, fills is refused naming decisions. My plant
   `NEEDS = {"fills": ("snapshot",)}` still passes `tests/daily`, `tests/timetable`, `tests/desk` and
   `tests/scoreboard` on f0bb2aa9c (489 passed). It must fail.
3. **The full gates** on the head, and the merge with main (and with T1d, which merges together).

## Addendum 2

Judge B, 24 Oct 2026, round 2 of 2 (the last). Head judged: **story/o1-r1r2-step-safety-b at 2c80be430** (contains
main 404452481). c9fba7584 is superseded and was not judged. Addendum 1's checks were re-run here, not taken on trust.

**Verdict: FAIL, round 2 of 2: one should-fix (SF3). After two rounds the owner decides.** SF1 and SF2 are fixed.

| Item | Verdict | My evidence |
|---|---|---|
| SF1: a failed step retried by a same-day rerun | ACCEPTED | `run_log.py`: `done` is false only for `failed` with `retry is True`; `record` pops only that entry. `RETRIED_ON_RERUN` holds fills, exits and trade_marks; the other desk steps stay final, each with its reason in the alert |
| SF1: safe-to-retry table | ACCEPTED | fills: `EntryDesk.enter` returns an entry event's recorded outcome; fill IDs are `trade:action:contract`. exits: event IDs per trade, outcome and snapshot or day; a closed trade is no open position. A write cut off by an error is not pushed (`open_account_writer`), and the next write's pull overwrites every file Drive holds. Drive errors are `PrivateFilesUnavailable(CommitFailed)`, so they still stop the run. versions, pack, decisions and snapshot: final, reasons checked against `_plan` |
| SF1: same-day guard, retry key survives the public log | MET | `self.clock().date() == day` (`now_ist`); `PublicResult` keeps booleans |
| SF2: fills refused naming decisions, no fill | ACCEPTED | `test_final_step_failures.py[decisions]`; my plant `NEEDS = {"fills": ("snapshot",)}` now fails 2 tests |
| The orchestrator's finding: any problem status refuses fills | MET | `_refused` uses `problem_steps` plus a missing check; my plants (refused ignored; missing ignored) are caught |
| Addendum 1's holds: book_results, scoreboard, health, readers | MET | re-read; plants on `_decided`, `_unreviewed` and `_problems` are caught |

**SF3 (should-fix): a fills retry has no time limit, so a rerun after the close fills at 15:15 prices with hindsight.**
- **Evidence:** my probe, built on the builder's own fakes and not committed. Fills fail at 15:16 and the rerun comes
  at 23:50 IST the same day. Both trades are `opened` at `exec_20261014_151500`, 8.5 hours after `fills_by` (15:20,
  `config.yaml`). The window check reads the capture's times, never the clock, and no other guard exists.
- **Why it matters:** a rerun is a human choice made after the price is known. Fills decide trades and feed the
  scores, an evaluation record. A trade that went well can be filled late; one that went badly can be left out by not
  rerunning. The alert invites the rerun ("a rerun today retries it").
  - The exposure also existed on main for a crash, which was then unrecorded. This change is where the retry rule is
    now set, and the builder named it as an open point. It is absent from the Claims, as is the scratchpad-restore
    point.
- **Fix expected (reasoning only):** retry fills only before a stated bound, `fills_by` or another the owner rules.
  After the bound, the failure is final with its reason in the alert. Tests at the bound and one minute past it. The
  Claims state the bound, and also the skip-side selection risk of an exits retry.

**The builder's open points:**
- **Per-book exit-review errors are not retried:** an acceptable stated limit, unchanged since judge 84.
  - A correction to my round 1: my example there, a Drive or HTTP timeout inside a book's review, is caught per book
    by `review_exits`, `PrivateFilesUnavailable` included. So SF1's fix covers only a step-level error (`pack`, books).
  - A due stop-loss exit then waits a day. That is a follow-up for the orchestrator, not a regression here.
- **Marks, E6's reviews and the card are not rerun:** an acceptable stated limit. E6 already marked the still-open
  positions at the same snapshot. The day's equity row and T1d's card line ("exits (failed)") stay stale until the
  next session.
- **The selection risk of a manual rerun:** SF3.
- **A shared-scratchpad restore:** no residue. I read the whole diff, my 14 plants were all caught, and the full suite
  is green.

**Plants: 14 planted, 14 caught, no survivor.** SF2's `NEEDS`; `done` without retry; the retry key alone; the same-day
guard; snapshot retried; a refused input ignored; a missing input ignored; `RUN_STOPS` swallowed in `_run_step` and in
`fill`; the failed entry kept in place; `_unreviewed`, `_problems` and the scoreboard's `_decided` reverted; every
alert saying "retries".

**Gates on 2c80be430 (run by me):** 15,150 passed, 15 xfailed; ruff, ruff format, check_imports and check_records
clean.

**Trial merge with T1d:** clean at 647232903 and at its moved head 5cbd3c4c7, which contains 2c80be430 and changes
nothing in `fno/desk` or `fno/daily`. tests/daily, timetable, desk, scoreboard and cards: 631 and 633 passed.

**Note:** a fills retry runs after run 1's exits, so `blocking_trades` and `taken_units` may see that run's close fills
at the same snapshot. A retried entry can then differ from an uninterrupted day's, either way. Nothing is doubled.

## Addendum 3 (owner's ruling 1A, own session)

Judge B, 24 Oct 2026, in its own session (session_013TeXdnxSdUSYWCHjfyQA3N). Head judged: **story/o1-r1r2-step-safety-b
at ee5711075**; the builder's delta from 2c80be430 is 067709db0, 5ca1fd0bc, 7fd93779b and d1b29a968 (the rest is main).
Scope: only whether round 3 implements the owner's ruling ("1 - A", "2 - yes") and closes SF3.

**Verdict: PASS: the change implements the ruling. SF3 is closed.** One minor and one merge condition below.

| Check | Verdict | My evidence |
|---|---|---|
| Failed fills final, logged `retry: false`, no trade on a rerun | MET | `daily_run.py`: `RETRIED_ON_RERUN = ("exits", trade_marks)`; `_run_step` sets `retry = name in RETRIED_ON_RERUN`; `done` is false only for `retry is True`. Plant J1 (fills back in the list) fails 3 tests |
| The alert says final, no new trade | MET | `NOT_RETRIED["fills"]` "failed fills are final for the day: no other new desk trade opens today (fail closed)" matches DESK_DECISIONS line 318 |
| `_too_late`: 15:20:00 fills, 15:20:01 refused, only for a run that did not take the snapshot | MET | `now <= by` and `"snapshot" in self.ran_here`, reset in `run()`. Plants J2 (`<`), J3 (+1 s grace), J6 (seconds dropped), J4 (snapshot rule dropped), J5 (no reset), J15 (never added), J9 (not called), J7 (no alert): all caught |
| SF3's 23:50 probe now refused | MET | `test_..._past_fills_by_is_refused_and_opens_nothing[30600]`: refused, book 3 opens nothing, the written trades unchanged, a clock set back still refused |
| A late snapshot cannot reopen it | MET (read) | a rerun that takes the snapshot itself needs a new capture inside 15:15-15:20 (`SnapshotInWindow`, `take_snapshot` requires this attempt's record), else `valid` is false and nothing fills |
| `desk:FILLS_LATE` and `NEEDS_*` codes | MET | `reason_codes.py`; plant J12 caught |
| Exits and trade_marks still retried | MET (code), see M1 | `_too_late` returns at once for any name but `fills`; the round-2 retry tests pass |
| Last line "; a rerun today retries it: <steps>" on its own day only | MET | `runner.py` `_retries` with `on_its_day`; plants J10 (any day), J11 (any failed step), J14 (no suffix): caught |
| CLAUDE.md step 2b | MET | reruns once, at once, once only, never later; fills never retried; 14:05 unchanged (only 2b added). Narrows no lane-1 rule, touches no hard line |
| J6 pinned | MET | plant J13 `written = len(result)` fails `test_the_written_count_leaves_out_a_blocked_book` |

**M1 (minor, test only): the late-rerun test does not prove the exits and marks ran.** It asserts only `"exits" in
log.steps`. My plant J8 (`_too_late` also refuses exits and trade_marks) survives all 690 tests. A probe asserting
neither is `refused` passes on the head and fails 3 tests under J8, so the code is right. No test runs an exits retry
after 15:20, the immediate rerun's usual time. Fix expected: assert their status is not refused there.

**Merge condition (caused by this change, not a ruling defect):** with T1d (5cbd3c4c7) merged in, cb87fd6be fails
`tests/cards/test_problem_steps.py::test_the_runner_s_last_line_and_the_card_name_the_same_steps_for_one_log`:
`AttributeError: 'types.SimpleNamespace' object has no attribute 'on_its_day'` (`runner.py:69`). The runner now calls
`daily_run.on_its_day`. Adding `on_its_day=lambda day: True` to that fake gives 646 passed. Whoever merges second makes
that edit before pushing.

**Plants: 15 planted, 14 caught, one survivor (J8, M1).** Restored with `git checkout --`; `git status` clean.

**Gates (run by me):** trial merge with origin/main b61907a2a (547f51f94): 15,233 passed, 1 skipped, 15 xfailed; ruff,
ruff format, check_imports, check_records and check_numbers clean. Trial merge with T1d: tests/daily, timetable, desk,
scoreboard and cards 645 passed, 1 failed (above).
