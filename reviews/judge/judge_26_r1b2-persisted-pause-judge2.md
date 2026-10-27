# Judge 26: R1b2 the pause remembered between runs, story text (judge #2)

Branch `story/R1b2-persisted-pause`, SHA `c705ef5`, story only. **FAIL** (round 1), lane 1: 1 blocking, 3 should-fix.
The live-window rule is right; the commit mechanics have a hole that hits manifest commits exactly during an NSE block.

## The live-window question: my ruling

**Never weaker, not an owner trade-off** (reasoning from the code, no measurement). While a host is cooling, a live
run sends one paced probe. Today a new process has no memory at all and sends its whole retry loop plus every other
request of the run, and its own in-process pause after two refusals is unchanged. So the rule is more polite than today
on every run, and it keeps today's guarantee of at least one attempt for the windows that cannot be redone. The cost,
that a refused live probe doubles the cool-down for the archive runs that follow, falls on data the catch-up repairs.
I accept it.

## Criteria

| Item | Verdict | Evidence |
|---|---|---|
| The live-window rule | MET | above |
| `force_probe=False` library edit | MET (design) | the default keeps R1a's behaviour; to be planted at build |
| `merge=union` on the log | MET | `.gitattributes` `research/data/resilience/*.csv` |
| Commit step: last, `always()`, `continue-on-error`, one path, stops when unchanged | PARTLY | B1, S2 |
| Restore from the log | NOT MET as written | S1 (clock) |
| The live set (5 commands) | PARTLY | S3 |
| `preopen record` edge | acceptable | note 1 |

## Findings

1. **B1 (blocking): the log file is dirty during the run, which breaks the Python committers' pull, during an NSE
   block.** The pacer appends to the tracked `research/data/resilience/paced-hosts.csv` while the run is going, and the
   new commit step adds it only at the end. Before that, six workflows' `GitManifestRecorder` (and the owned-paths
   committers) run `git pull --no-rebase` (`manifest_commit.py:115`, no autostash). If another workflow has pushed a
   change to the same CSV meanwhile, git refuses the pull: "Your local changes ... would be overwritten by merge", or,
   for a first-time untracked file, "untracked working tree files would be overwritten". The manifest rows of that run
   are then **not pushed**, so Drive files exist without their receipts. The trigger is correlated: an NSE block opens
   breakers in many workflows at once, so concurrent log writes are most likely exactly when they happen. Fix (one
   option): during the run the pacer appends to a run-local, git-ignored file (for example under `$RUNNER_TEMP`, or a
   path in `.gitignore`). Restore reads the tracked CSV plus that run-local file. Only the last step, after its own
   `git pull --no-rebase`, appends the run-local rows to the tracked CSV and commits. Then nothing tracked is dirty
   while the Python committers pull. Add a test (or a scripted git test like `test_union_merge`) where a tracked-log
   change on the remote plus a run's log rows still lets the manifest commit push.
2. **S1 (should fix): restore needs a real UTC clock, and the story does not say so.** R1b1's breaker clock is
   `EPOCH + monotonic` (`nse_pacer.py`, `_wall_clock`; my judge 25, carried note). Rows written with it hold
   2000-01-01-plus-uptime times, and another process with a different monotonic origin would misread every cool-down.
   Claim 1's "fake clock" test would not catch it. Fix: the breaker writes and compares real UTC (`now_utc`); claim 1
   adds a test with two processes whose monotonic origins differ.
3. **S2 (should fix): the commit step must commit with the record scan on, and with an identity.** CLAUDE.md: every
   commit runs with the public-record scan (`core.hooksPath .githooks`), never `--no-verify`. Several workflows set
   `core.hooksPath` and `user.name` only in steps that a dry run or a failure skips. A last step under `always()` can
   run when those were skipped. The step must set both itself (as `pipeline-staging.yml`'s "Commit identity" step
   does), and the YAML test (claim 5) must assert it.
4. **S3 (should fix): the live set misses the latest-day-only reports.** A miss is also permanent once the next day
   replaces these files:
   - `data-snapshot fii-dii-cash-by-session` and `fpi-daily-by-session` (`flows-download.yml:57-58`): "serve only
     their latest day" (`flows-download.yml:1-4`, `snapshot_source.py:89-94`);
   - the F&O ban list in `fo-masters` (`STALE_REFUSED = True`, `snapshot_source.py:167`: valid only for its own
     session).

   With a cool-down that can double up to 24 h, a carried-over pause can skip every run in their window. Add them to
   `LIVE_WINDOW_COMMANDS`, or show from the schedules that a run always falls after the longest cool-down inside each
   one's window, which is false once the cool-down has doubled.

## Notes

1. `preopen record` runs in no workflow (`grep`), so it never receives the committed log and behaves as today.
   Leaving it in the set is harmless, and it is never weaker. The owner should still state where it runs, and that
   environment must not commit the log file, or it would add an unmanaged writer.
2. Deferring the Groww-side live captures to R1d is right; the rule has to come with them.

## Addendum 1: round 2, `3ff3358` (story text)

**PASS**, lane 1, judge #2.

| Round-1 finding | Verdict | Evidence (round-2 text) |
|---|---|---|
| B1 the dirty tracked log | FIXED | the run only reads the committed CSV and appends to a git-ignored `research/data/resilience/.run/paced-hosts.csv` (`LayeredLog`); only the last step pulls, appends the new rows, commits and pushes. Claim 9 requires the two-clone git test of the refused-pull case and `git check-ignore` |
| S1 the clock | FIXED | real UTC for the persisted log and restore, monotonic only for in-process spacing; claim 9 tests a restore across differing monotonic clocks |
| S2 hooks and identity | FIXED | the step sets `core.hooksPath` and the identity itself; the YAML test reads both |
| S3 the live set | FIXED | `fo-masters` and the two `data-snapshot ...-by-session` kinds added under a stated rule |

**On the rule and the set (my view, reasoning only):** `fpi-daily-by-session` belongs. It is a latest-day-only report
like its sibling, and the live rule acts only when that host's own breaker is open, so it costs NSDL at most one request
a run. Under the rule, nothing I can find is missing: index closes, VIX history, flow history, filings and `global-cues
fill` are all backfills from sources that keep history.

### Minor (wording only)

The rule "a source that overwrites in place" also fits the excluded reference lists (equity list, Nifty 500), which NSE
replaces in place, but rarely. State the exclusion in the rule itself: "overwrites in place **within the window in
which the next run would read it**", so the static test's set and the rule agree.
