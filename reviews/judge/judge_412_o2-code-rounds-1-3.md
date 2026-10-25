# Judge 412: O2 code, rounds 1-3 (story/o2-failure-handling at e6483952)

**Verdict: PASS for rounds 1-3. Lane 1. They may merge on their own,** so the git limit and the silent-part alert reach
production now. O2 as a story is not done: round 4 (kill-and-rerun, hung git and hung command end to end, the trade
fixture rows, the shadow cases with (c) as a strict xfail, the source-tree-unchanged test) comes later, with its own
verdict. The text is judge 204 addenda 3 and 5.

## Round 1: one hard limit on every git call (`fno/desk/git_limit.py`, `git_sync.py`, `steps.py`)
| Check | Result | Evidence |
|---|---|---|
| Each call in its own process group; at the limit the group is killed and reaped | MET | `LimitedRun`: `start_new_session=True`, `os.killpg(SIGKILL)`, then `communicate()` |
| Only the call's own new locks are removed, never while a git process lives | MET | `GitLocks.remove_new(before)`: the new set only; `_git_alive` scans `/proc`, and with no `/proc` nothing is removed |
| A lock already there fails the call with the hand fix | MET | `HELD_LOCK` and `HAND_FIX` in `Git.__call__` |
| A stopped push is "push not confirmed", unpushed | MET | `PushNotConfirmed(PushRejected)` |
| No path bypasses the limit | MET | `unshallow`, `content_sha256` and D3's `decided_runs` now go through `Git._run` or `Git.show` (the builder's test found the last bypass) |
| `CommandStep`'s 600 s stop removes its own new locks | MET | `steps.py`; `GitLocks(root)` wired in `fno/daily/wiring.py` |

Planted mutations (real git, hanging hooks):
- old locks removed too: caught (1 failed);
- the live-git guard off: caught (1 failed);
- no lock removal: caught (1 failed);
- **`popen.kill()` instead of `killpg`:** the test run **hung** rather than failing, because the hook kept the pipe
  open. A regression would still show in CI as a timeout, but put a per-test time limit on `tests/daily/test_git_limit.py`
  (for example `pytest-timeout`, or a `signal.alarm` guard) so it fails, not hangs. This is a note, not a should-fix.

## Round 2: the end-to-end harness (`tests/e2e/`) and two root fixes
- `OUTSIDE_SEAMS` lists:
  - the clock;
  - Slack;
  - the owner's Drive (both builders);
  - the raw NSE stores and NSE's archive;
  - Groww's 15:15 capture;
  - the child-process runner;
  - the quote store's default folder.

  A test keeps the list. The child commands are scripted, and the story text names them as a seam (line 48), with NIFTY's
  part running A4's real `record_today` over a fake Groww. So the weather, v4 and card children are not run end to end.
  They are `not_live` in production anyway; say so when they go live.
- **Root fixes, each tested:**
  - `build_book1_orders(cfg, root)`;
  - the capture's quote folder is root-relative (`fno/desk/daily_wiring.py`).

  Both are harmless in production, where root == ROOT.

## Round 3: outage families and G1
- Slack up and down, the twin multiset, NSE failing, Drive at the download, Drive for the raw files, and never-starts:
  each family has its test.
- **G1:** a 3 pm part that failed without its own alert now gets one O1 alert (`PART_NOT_OK`).
  - Planted mutation: that alert removed fails 5 tests.
  - A part that alerted itself (its lines hold "alert sent" or "alert NOT sent") gets no second alert.
- **G2:** "A4's child prints the unsent outcome without the text" is a **strict** xfail
  (`tests/e2e/test_outages.py` 115).

## Gates
On a trial merge with main plus main-green (76f5d1f7): **8130 passed, 19 xfailed, 0 failed**; ruff and check_imports
clean. tests/e2e: 9 passed and 1 xfailed in 117 s on 4 workers.

## Merge order (must read)
G2's strict xfail XPASSes, and so fails, as soon as the A4 unsent-alert fix (story/a4-unsent-alert-text) lands.
Whichever of the two merges second must turn the xfail into the real assertion in the same push, or main goes red.

## Addendum 1: merge-order correction
My merge-order caveat above was wrong. I merged O2 (e6483952) with the A4 fix (cac35232) and main-green: tests/e2e plus
tests/daily give 87 passed and 1 xfailed. G2's strict xfail does **not** flip, because the e2e children are scripted and
never go through `cmd_quotes`. Either branch can merge first.

Two things remain for round 4:
1. G2 stays xfail until the harness runs the real `cmd_quotes` path.
2. O2's own-alert detection reads `lines()`, which the A4 fix now strips of unsent lines, so on Slack-down days a part
   gets a second unsent alert. Count relayed lines instead (judge 415).

## Addendum 2: ruling on gap F1 (the O2 builder's question, round 4a at 3abd5dc5)
**Ruling: F1 is a real gap and is fixed in O1. I agree with the direction, with one change to the design. It is a
small O1 story amendment, judged before the code.**

**Why it is real.** If the routine's container dies before about 14:55, the 3 pm parts' child processes die with it. The
rerun's log already holds `quotes`, so under judge 178 note 4 it starts no part, and NIFTY's and NSE's records are lost
while their window is still open until 15:10. That means no pack and no decision. A container death or a restarted
routine is normal enough (16 Oct showed hung and killed sessions). Note 4 was right about a dead run's *files* (never
commit what a dead part half-wrote); it was not meant to give up a window that is still open.

**My change to the design: an OS lock instead of a pid lease.** A pid can be reused, and "is pid N alive" can be wrong
after a container restart or a pid wrap. Instead:
- Each part, meaning A4's recorder process itself, holds an exclusive `fcntl.flock` on a git-ignored per-day,
  per-part lock file for as long as it runs. The kernel releases it when the process dies, whatever the cause.
- **The rerun takes the lock without blocking.**
  - If it gets the lock, no recorder is alive: release it, then restart the part if it has no canonical marker and its
    window is still open (NIFTY and NSE until 15:10, the indices until 15:13).
  - If it does not get the lock, the part is alive (same container): adopt it. Wait until the lock frees, then commit
    the part's files as usual. It never starts a second recorder.
- A4's recorder stays the guard of last resort ("already recorded" once a canonical exists). Never rely on it alone:
  two recorders racing to the canonical marker is exactly the risk.

**The amendment must also state:**
1. "Started at, restarted, adopted" for each part, in the run log (this also closes my criterion-9 note on start
   times).
2. `NOT_IN_THIS_RUN` stays only for a part whose window has closed, with one alert.
3. The tests:
   - a kill before 14:55, then a rerun in a new process: NIFTY and NSE recorded, byte-identical to the twin day;
   - a run that crashed while its part lives: the part is adopted, there is one recorder, and its files are committed;
   - a rerun after 15:10: `NOT_IN_THIS_RUN`, one alert.

   Then F1's strict xfail becomes the real assertion.
4. The indices part ("kill at versions..decisions: only the indices' record is lost") gets the same rule.

## Addendum 3: rulings on F1 (repeated) and G4 (round 4b at 2ba9dd2e)
**F1: my ruling stands as addendum 2: an OS `flock` held by the recorder, not a pid lease.** Add the builder's new
observation to the same amendment: a rerun after a stop must read each part's **committed** canonical marker. A part
the stopped run already recorded and committed is reported "recorded earlier (commit X)", with no alert. It is never
`NOT_IN_THIS_RUN`, failed and alerted. This has the same root as F1, so it is one amendment and one fix.

**G4 is a real gap. I checked the mechanism on main.** `GitCommitter._refuse_stray` (`fno/desk/git_sync.py` 159-172)
accepts exactly one `OwnCommit`, the one passed to that call. A quote part's commit whose push failed stays local, and
the desk's next commit then refuses it as "an unpushed commit the run did not make", so the desk stops before `exits`.
How often this happens is reasoning only (it needs three rejected push attempts, or a hang). The cost when it does is
the whole day, so it is worth fixing.

**Ruling on the design:** the builder's direction is right, and it should be kept simple.
1. **One committer per run.** The run builds one `GitCommitter`, which the parts and the desk's `PendingCommitter`
   share. Today `fno/daily/wiring.py` builds a second `GitCommitter(git)` for the parts. The shared committer
   remembers every commit it made that is not yet pushed, as `OwnCommit` (message plus each file's SHA-256), and
   `_refuse_stray` accepts any of them, still checked by content. A commit the run did not make is still refused
   (decision 51 is kept).
2. **Across a rerun in the same container,** the list is kept in one git-ignored file the run writes before each push
   and clears once the push succeeds, so a rerun accepts its own earlier commits by the same content check. A new
   container has no such local commits, so nothing changes there.
3. **I agree with rejecting the reset alternative,** for the builder's reason: after a merge pull, a soft reset can leave
   origin's changes staged.
4. **The wording:** a part whose commit is made but not pushed must say **"committed, NOT pushed (the next push carries
   it)"**, not O1's "NOT committed" hand fix. Telling someone to `git add` and commit again would be wrong advice.
5. **Tests:**
   - a part's push refused or hung: the desk goes on, the next desk push carries the part's commit, and there is one
     alert;
   - a stranger's unpushed commit is still refused;
   - a same-container rerun after a part's failed push accepts it by content.

   Then G4's strict xfail becomes the real assertion.

Both F1 and G4 are lane 1 (O1's wiring, E2b and E3's `git_sync` and `pending_commit`). Each is a small story amendment
first, judged before code. Each may be its own change, as the orchestrator directs.

## Addendum 4: the O2 scope split (story/o2b-split at 49b81669, docs only)
**Agreed. It is a status change, so lane 3; the orchestrator may merge it.** The text matches the record:
- O2 rounds 1-3 merged at cdd59db6 (judge 412);
- F1 (judge 417), G4 (judge 419) and the double-alert regression (judge 418) are O1 changes, each judged on its own;
- the round 4a/4b kill and hang rows join main with those fixes, their strict xfails made real;
- O2b (the trade rows and the source-tree-unchanged test) is paused, due before the first paper approval, with
  revision 6 (judge 204 addendum 5) as its contract.

**One line to keep in view:** D2's shadow-loop gap (judge 204 addendum 5, `fno/playbook/evaluate.py` 52-59) is a
production fix, not an O2b test. It must land before the first paper approval too, and needs its own owner and row.

## Addendum 5: rounds 4a and 4b at 39fbdf6e (the G4 xfail flipped)
**Verdict: PASS for the tests. Do NOT merge 39fbdf6e as it is: merge it after F1 (00e9da61, judge 421 addendum 1),
rebased.**

- **The G4 row is real now.** `test_a_quote_part_s_push_that_hangs_is_alerted_not_pushed_the_next_push_carries_it_and_the_desk_goes_on`
  asserts:
  - the alert "committed, NOT pushed (the next push carries it)" with "push not confirmed";
  - the part's commit on origin, carried by the desk's next push;
  - the exits reviewed;
  - no lock left.

  **Planted mutation:** G4's own-commit acceptance removed makes this test fail (1 failed).
- **The kill and hang rows:** tests/e2e/test_hangs.py plus test_kill_rerun.py give 16 passed and 6 xfailed. The F1
  cases are still strict xfails.
- **Two product lines in this head:**
  - `fno/desk/git_sync.py`: `Git` reads `GIT_CALL_LIMIT_SECONDS` when built, so the e2e suite can shorten it. That is
    harmless and accepted.
  - `fno/daily/quote_steps.py`: a new `NOT_IN_THIS_RUN_ALERT` on `FinishQuoteParts`' "not started" branch. **F1 removes
    that branch** (it is unreachable once a rerun resumes the parts). Merged after F1, this change must be dropped, not
    carried as dead code.

**Condition:** after F1 lands, rebase round 4 on main:
- drop the `quote_steps.py` alert;
- turn the F1 strict xfails into real assertions (`test_kill_rerun` BEFORE_PARTS and `test_hangs`' rerun-after-stop);
- change the kill-rerun assertions that still name `NOT_IN_THIS_RUN` to F1's per-part outcomes (`how`, "recorded
  earlier", restarted).

Then send that head; I check that diff.

## Addendum 6: round 4 rebased on F1 (story/o2-failure-handling at ba205014)
**Verdict: PASS. Addendum 5's condition is met; it may merge after the full gates pass on the exact pushed tree.**

- **The dead alert is dropped.** The only product line left is `git_sync.py` reading the limit when `Git` is built
  (accepted in addendum 5). F1's per-part `NOT_IN_THIS_RUN` replaces the whole-step alert, so a part that is not
  recorded still alerts once.
- **The F1 xfails are real.** One parametrized test covers a kill after every step before `quotes_done`. Each case
  asserts:
  - the rerun ends `(0, "day done")` with no alert;
  - the committed tree differs from the twin's only in the run log;
  - Drive equals the twin's;
  - each part's `how` (snapshot to reviews: every part "earlier run"; versions to decisions: nifty and nse "earlier
    run", indices "restarted"; before versions: every part "restarted").

  It replaces the old `NOT_IN_THIS_RUN` assertion, the lost-indices assertion and the xfail. The hang rerun asserts
  "day done", with every part "earlier run".
- **Planted mutation:** F1's "earlier run" branch removed (every part restarted instead) fails 10 of the kill and hang
  tests.
- **Gates on a trial merge with main (F1 included):** 8849 passed, 16 xfailed, 0 failed; ruff clean.

This closes O2's kill-and-rerun and hang rows in phase 1. O2b (the trade rows) stays paused.

## Addendum 7: the hung-git test flake fixed (story/o2-git-limit-test at 138c135b)
**Verdict: PASS. Lane 1 (`fno/desk/git_limit.py`). It may merge after the full gates pass on the exact pushed tree.**
This also answers my addendum 5 note: the killpg plant used to hang.

**Root cause 1 (judge E's report; reproduced by the builder with a slow-git shim): the test's 1 s limit applied to every
git call.** The fix:
- `LimitedRun(started=...)`, a callback before the limit counts (production passes nothing, so production is
  unchanged);
- the test gives the short limit only to the hung call, starting once its hook is reached; all other calls keep 120 s.

**Root cause 2 (the A4 builder): "stopped with its hooks" was said while the hook, git's grandchild, could still be
dying.** `_until_gone` now waits, at most `GROUP_GONE_SECONDS` = 5, until no live member of the group remains, read from
`/proc`. A zombie counts as gone, and the stat field parsing is correct: state, ppid, pgrp after the last `)`.

**My checks:**
- `tests/daily/test_git_limit.py` three times in a row: 7 passed each time.
- The `started` callback removed (the limit races git's start): caught, 1 failed.
- Zombies counted as live (the wait would hang the full 5 s every time): caught, 1 failed.
- Trial merge with main: 9751 passed, 16 xfailed, 0 failed; ruff clean.

**Environment note:** main now needs `xlrd`, which this container lacked. The first gate run failed on import errors
until `pip install -r requirements.txt`. Routines use `routine_setup.sh`, which installs it.

**Named, not changed:** `tests/e2e/test_hangs.py` sets a 2 s limit for every git call of a whole fixture day, the same
class of risk. The builder will test it under the slow-git shim next.

## Addendum 8

**O2 e2e hang tests, test-only follow-up (story/o2-git-limit-test at 8e766fe6): PASS. Merge after the orchestrator's
14:00-16:15 IST window today.**

The head holds:
- 138c135b (passed in addendum 7);
- 002d64c5 (test-only);
- a merge of main;
- the claims in response_203.

`fno/desk/git_limit.py` is byte-identical to 138c135b. Against main, the branch changes only that file (already
judged), `tests/daily/hung_calls.py`, `tests/daily/test_git_limit.py`, `tests/e2e/test_hangs.py` and response_203.

| Claim | Result | Evidence |
|---|---|---|
| The e2e hang tests' day-wide 2 s limit stops a slow normal call | CONFIRMED | 138c135b's `test_hangs.py`, with every git call slowed by 2.5 s (my own shim on PATH): both push-hang tests failed with "git ls-files -z ran past 2 s" |
| With the fix, the short limit goes only to a push made while the hang is on | CONFIRMED | same shim, same run, the new file: both push-hang tests passed (2 failed, 2 passed in 29:15). The command-hang test needs no git timing and was left out |
| `HungCallRun` moved unchanged apart from `when=` and `locks=`; the unit tests are unchanged in substance | MET | diff 138c135b..002d64c5 |
| Nothing in `fno/` changed after 138c135b | MET | `git diff 138c135b 8e766fe6 -- fno/desk/git_limit.py` is empty; the other `fno/` lines in that range come from main's merge |

**Plants**

| Plant | Caught |
|---|---|
| `when=lambda: True`: a push with no hang is treated as hung | yes, 2 failed: "the push hook never started" (the 120 s hook-start wait gives a test error, never a pass) |
| The hung call given the run's 120 s instead of the short limit | yes, by `test_git_limit` (the hook-start timing check). Not by the e2e tests, which pass at 120 s: they check the outcome (stopped, alerted, recovered), not the limit's size. Acceptable, since the unit test owns the timing |

**Gates on a trial merge with main** (57993d8c, scratchpad worktree, removed):
- 9,810 passed, 16 xfailed;
- ruff check clean, format clean;
- check_imports clean, check_numbers clean.
