# Judge 523: MS-P1j follow-up, the instructor wired into the fleet (second judge)

**Scope:** story/ms-p1j-ins-wiring at 4f5f8297 (builder session_01CmKJ6taCLzfEGg7wt6RC4N): its own commits eb5ec57a,
bcf9ab21 and 4f5f8297. The branch also carries an older, pre-rebase state of MS-INS part e (63cabe67), which is mine
under judge 522 (FAIL) and not judged here. Lane 1, second judge; I wrote this without reading Judge B's 507.12.
Round 1 of 2. Judge K (session_019ZApRwkUiNMKDsf1k4W44z).

**Verdict: FAIL.** 1 should-fix, 2 minor, and a merge condition.

## Checked
- `after_outcomes` runs after the outcomes and drift seals and before the counts' write, and again on the rerun fast
  path (`runner.py`, eb5ec57a). A replay passes `no_step`. `IsolatedSessionStep` turns a failure or a time-out into
  one alert by class, never a stop.
- `SessionFilesCommitter` commits only the session's three counts files plus the record root's
  `instructor_counts_path(session)`. A replay's `FleetStores` names no extra, and `.gitignore` ignores
  `research/school/counts/**/.*.part`.
- `SealedDayInputs.why` carries part e's lines (no contract or price; part e's own privacy tests).

## Findings
1. **Should-fix: a timed-out instructor can still race the school's own counts commit in git.**
   - After 300 s `isolated` returns, but the worker thread keeps running (`fleet/isolate.py` says so).
   - The instructor's write path ends in `GitReceiptPublisher.publish`: `recorder.commit` (git add, commit, pull,
     push), then `git fetch`/`log` in the same repository.
   - Meanwhile the main thread goes straight on to `counts.write` and `SessionFilesCommitter.commit` (git add, commit,
     push).
   - Two git writers in one checkout can collide on `.git/index.lock` or interleave a pull. That makes the school's
     own counts commit fail: exactly what "can never stop the school's record" rules out. [reasoning only: the code
     path is direct; I did not force the race.]
   - Expected, one of:
     - the instructor run in a child process, ended at the limit;
     - the step not committing inside the thread (its receipts committed by the main thread after it returns);
     - the counts commit waiting for, or serialising with, any git work the step left running.
   - A test with a step that sleeps past the limit and then commits.

**Minor:**
- (a) `UnfilledEntries._fired` reads each decisions file without catching `StaleSeal`. A damaged file stops the
  instructor's comparison instead of listing the session (part e's `sealed_decisions` lists it as unsealed).
- (b) `build_unfilled_entries` builds the whole record fleet to reach three stores. On `main`, `build_fleet` now
  returns `SwitchedOff` when the school is off, which has no `dashcam` or `books`. Build the stores directly.

## Merge condition
This branch depends on MS-INS part e, which failed judge 522 and will change in round 2. Rebase onto part e's passed
tip and current `main` (the switch now lives in `build_fleet`, with the card check beside it). I will judge that tip
as round 2 together with part e's.

## Plants
None planted this round: the branch sits on part e's pre-rebase base, and the rebased tip is what merges.

## Addendum 1: round 2 at 7d76b05d

**Verdict: PASS** (second judge). It is rebuilt on MS-INS part e's passed tip 136f5890 (an ancestor; part e is on
`main`). I judged its own changes against `main` (14 files, `git diff origin/main 7d76b05d -- fno`).

| Round-1 finding | Result | My evidence |
|---|---|---|
| SF1 a timed-out instructor racing the counts commit in git | ACCEPTED, by construction | `StagedSessionStep` runs `prepare` (one fetch) on the run's thread, then the work on a thread. The work returns its writes, which run on the run's thread only when the work ended in time. `DeferredInstructorStore` keeps writes until `flush`. `RunReceipts` only calls `RemoteReceipts.find` (`git log`/`show`, read-only) and never refreshes or commits on the thread. One `NamedFiles` commit takes the counts and `instructor_files(session)`. Plants caught: a flush inside the work, the time-out branch removed, the writes never run, `prepare` skipped, a refresh inside `publish`, deferred reads ignoring pending writes, a deferred write going straight through |
| Minor (a) `StaleSeal` in `UnfilledEntries` | ACCEPTED | caught (plant narrowing the catch) |
| Minor (b) `build_unfilled_entries` | ACCEPTED | builds the dashcam and books itself, not through `build_fleet` |

- **Plants:** 9 planted, 8 caught. The survivor is `NamedFiles.owns` forced to True. That guard stops the commit's
  pull from also pushing someone else's unpushed local commits to `main`. The code is right, and the base recorder's
  own guard is tested, but not this subclass. **Minor:** add one test.
- **Merge:** `git merge-tree` with current `main` conflicts only in `docs/stories/MS-market-school.md`. The code merges
  cleanly. A doc-only resolution needs no new judgment.
- **Limit accepted [reasoning only]:** the writes on the run's thread have no step limit beyond Drive's own
  time-outs, as the builder states. Adding one would bring back a late write.
- **Gates (my run):** pytest -n auto 14,338 passed, 16 xfailed. ruff check and format, check_imports and
  check_records are clean.

## Addendum 2: the final tip 94d3acb1

**PASS confirmed** (second judge). 7d76b05d..94d3acb1 adds one test, that every session call builds its own path
reader (`test_instructor_receipts_wiring.py`), plus a merge of `main`. No other code changes. `git merge-tree` with
current `main`: clean. The fleet and instructor tests pass (354). The `NamedFiles.owns` minor (addendum 1) is still
open, as a minor.
**Note:** `recover()` (story/ms-ins-adopt) failed judge 525. If it lands later, the deferred store must implement it
and adopt only on the run's own thread.

## Addendum 3: bda6a49d

**PASS, last minor closed.** 94d3acb1..bda6a49d is test and doc only:
`test_an_unpushed_commit_of_another_writer_still_blocks_the_push`. My plant (`NamedFiles.owns` forced to True) fails
it (1 failed, 103 passed); without the plant, `tests/school/fleet` gives 104 passed. `git merge-tree` with current
`main` is clean.

## Addendum 4: round 3 at 98d16fcd (second judge, independent)

**Scope:**
- 52cf0224: judge 507.13 SF1, a refused counts commit is loud.
- Two merges of main: the publisher move and the instructor's cut-off.

Against bda6a49d (523.3), the builder's own changes are:
- `fleet/counts_commit.py`, `counts_file.py`, `runner.py`, `contracts/fleet.py`;
- the wiring;
- `tests/school/fleet/test_counts_not_pushed.py`.

I did not read Judge B's 507.14 first.

**Verdict: PASS.** No blocking or should-fix findings.

| Claim | Result | My evidence |
|---|---|---|
| A refused commit returns its line | MET | `SessionFilesCommitter.commit` returns None on success, else the outcome that starts with `REFUSED` ("school session files NOT committed: "). `_not_committed` names the files to commit by hand |
| Alerted by name to #fno-desk | MET | `SessionCounts.commit` sends `counts NOT pushed <session>: <outcome>` through `alert`. `build_fleet` wires `build_alert_sender().send` |
| Exit 1 on the first run and the rerun | MET | The runner adds the refusal to `SessionRun.warnings` on both paths. The CLI test, on real git with the remote pointed nowhere, exits 1 twice with 2 alerts, then 0 once the push works |
| A rerun with nothing new pushes the earlier commit | MET | `NamedFiles.commit`: on "nothing new" with a named file in `origin/main...HEAD`, it runs `_publish`. The test shows the file on origin afterwards |
| The run's own unpushed commits never block a later session | MET | `run_paths` = the counts folder plus `RECEIPTS_PREFIX`. These pass O9's off-main guard. The test: day 1 refused, day 2 pushes both |

**Plants (mine, `tests/school/fleet`): 9 of 9 caught.**
- The unpushed retry dropped.
- The committer always silent.
- No alert.
- The rerun drops the refusal.
- The first run drops it.
- The alert not wired.
- The receipts prefix missing from the run paths.
- No run paths at all.
- `_unpushed` never true.

**Notes (no change needed):**
- The alert line carries git's first error line, as O9's lines already do.
- `_unpushed` compares against `origin/main` as last fetched. A stale ref only causes one extra pull and push, never a wrong "done".
- A fresh container loses the local unpushed commit. The rerun then rebuilds from Drive as before (unchanged design).

**Gates (my run, a trial merge of 98d16fcd with main 85ced401):**
- `pytest -n auto`: 14413 passed, 16 xfailed, 2 failed.
- The 2 failures are `tests/intraday/test_feed_tls.py`, and they fail on main itself in this container: `ModuleNotFoundError: growwapi`, because the test imports Groww's package without a skip. They are not from this branch; reported to the orchestrator.
- ruff check, ruff format, check_imports, check_records (8650 files) and check_numbers: clean.
