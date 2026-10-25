# Judge 350: O10 part 1, capture watcher and capture-error log (story/o10-capture-health @ c31ec103)

Judge F (independent). Story `docs/stories/O10-capture-health.md`, claims `reviews/claude/response_254_o10-capture-health.md`,
base `63632347`, head `c31ec103427b567ae532dc96d933d1dbaa2327fc`. Lane 1 (a new GitHub workflow, Slack output).
Evidence labels: **strong** (test, run log, code read and reproduced), **some**, **reasoning only**.

## Verdict: FAIL (2 should fix, 3 minor)

The design is sound and simple: one `workflow_run` watcher, no watched workflow edited, one CSV row per bad run,
names and conclusions only (no log text), union merge, no concurrency group. Gates are green and 8 of my 9 planted
bugs were caught. It fails on two things: one realistic failure path still posts nothing, and the participant-OI
day fix is only half done inside the same job.

## Gates (run by me on the exact head, full history)

| Gate | Result |
|---|---|
| `env -u FNO_SLACK_BOT_TOKEN PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider -n auto` | **7386 passed**, 2 warnings, 221 s |
| `ruff check fno tests tools` | All checks passed |
| `ruff format --check fno tests tools` | 1319 files already formatted |
| `python tools/check_imports.py`, `python tools/check_records.py` | clean (1409 files, 1 archival skipped) |
| 350-line limit | new files 47-82 lines; test file 203 |
| Composition only in `fno/health/wiring.py` | yes (`build_capture_error_log`, `build_run_source`) |

## Planted mutations (each reverted after)

| # | Plant | Caught |
|---|---|---|
| 1 | `SILENT_KINDS` without `timed_out` | yes (1 failed) |
| 2 | duplicate-run check removed | yes |
| 3 | `one_line` keeps newlines | yes |
| 4 | watch default day back to `now_ist().date()` | yes (2 failed, as claimed) |
| 5 | `git add research/ops/capture_errors.csv research/data` in the watcher | **no**: 24 passed (minor 1) |
| 6 | first bad step skips cancelled/failed steps | yes (3 failed) |
| 7 | one watched name misspelt | yes |
| 8 | exit 0 when the Slack line was not accepted | yes |
| 9 | date taken in UTC, not IST | yes |

## Criteria (part 1 only; part 2 is not built yet)

| # | Builder's claim | My evidence | Status |
|---|---|---|---|
| 1 | One row per failed, cancelled or timed-out run; never twice; none for success | Tests plus plants 2, 6 and 9. The real job JSON of run 38801338770, read through the GitHub API, matches the fixture: job `release` cancelled, step 6 "Watch NSE's archive ..." cancelled 20:22:16Z to 02:12:16Z, step 10 "Alert" (`failure()`) **skipped** | MET |
| 2 | One line for cancelled or timed-out runs, none for `failure`; with no token the row is kept and the run exits 1 | Tests plus plants 1 and 8. The rule "a `failure` already posted its own line" is false for at least one watched job (SF1) | PARTLY |
| 3 | One line of at most 200 characters, names only | `run_failures.py` reads only `name` and `conclusion`; `one_line` joins whitespace and truncates; plant 3 caught | MET |
| 4 | Watches every workflow except `checks` and itself; `actions: read` + `contents: write`; commits only the log; no secret | List equals the 15 `name:` values (I checked every file). Permissions right; no `${{ }}` inside a script; secrets only as step env. The "commits only" test lets an extra path through (minor 1) | MET (test weak) |
| 5 | O8 rows, the error-count line, misses appended once | part 2, not built | NOT MET (pending) |
| 6 | `watch` at 01:52 IST takes the previous day and checks once | Tests plus plant 4. The next step of the same workflow still uploads today's date (SF2) | PARTLY |
| 7 | Run logs: the first real watcher run; 16 Oct's health-check and quote-recorder-nse runs; the first nse-margins catch-up run | not yet possible (the watcher is not on `main`; those runs had not happened when I judged) | NOT MET (pending) |
| 8 | Gates, size, composition | see above | MET |

## Should fix

**SF1. A failed `forecast-capture` gate job posts nothing, and the watcher stays silent too [strong, code read].**
`capture-failed` alerts only when the run's conclusion is `cancelled` or `timed_out`. It assumes every `failure`
already posted its own line. In `forecast-capture.yml`, the `gate` job (checkout, setup-python, `capture_gate`) has no
`failure()` alert step. Its only alert step is in `capture`, which `needs: gate` and so is skipped. A gate crash
gives conclusion `failure`, nothing is posted, and the watcher writes the row but posts nothing. That is exactly the
silent failure the owner ruled out.

The same rule also says nothing for the other run conclusions GitHub can report (`startup_failure`,
`action_required`, `stale`). I have not seen one on this repository, so that part is reasoning only.

Fix expected: decide whether to alert from the run's jobs, not from the conclusion alone. Alert unless the failing
job shows its own alert step actually ran (not skipped). Alternatively, alert on every conclusion except `failure`
and give the gate job its own alert step; that second option needs the forecast-capture owner's agreement. Add a test
built from a gate-failure job list.

**SF2. A late `participant-oi-release` run now watches the previous day, but the next step uploads today's date
[strong, code read].** At c31ec103, the watch's default day is `due_day(now)`, which is yesterday before 12:00 IST.
The next step, "The day's file into Drive with its manifest row (A9)", still runs
`day=$(TZ=Asia/Kolkata date +%F)` whenever `watch.log` contains ": present at".

So a run that starts at 01:52 IST on 16 Oct and finds 15 Oct's file present asks the librarian for 16 Oct, a file
NSE has not published. The librarian then returns 1 (`report.complete` false) or uploads nothing. Either way, 15 Oct's
file is not archived by this run, and the run summary reports a download failure. The fix changes the day in one
step and leaves the job's other step on the old day. The step name "until today's file appears" is also now wrong.

Fix expected: compute the day once and pass the same day to both steps. Either the workflow passes `--day` to
`watch` and to the librarian, or `watch` prints the day it checked and the librarian step reads it. Add a test or
a workflow check that the two cannot differ.

## Minor

1. `test_commits_only_the_capture_error_log` reads only the first path after `git add`
   (`re.findall(r"git add (\S+)")`). Plant 5, `git add research/ops/capture_errors.csv research/data`, passes. Compare
   the whole `git add` line instead.
2. A re-run attempt of an already-recorded run that is cancelled again posts nothing: `has_run` returns "already
   recorded" before the alert check (`capture_cli.py`). Re-runs are started by hand, so this is low risk; one line
   in the known limits would do.
3. A pending run that GitHub cancels in a concurrency group, or a run the owner cancels by hand, will alert as
   "posted nothing itself" at "before any step". I found no such run in the history, so this is reasoning only; the
   alert text could say "cancelled before any step (possibly a queued run replaced)".

## Claims vs reality

- "fixtures trimmed from real runs 38801338770 and 38745053176": run 38801338770's jobs, read by me through the
  GitHub API, match. A job-level timeout shows as `cancelled`, not `timed_out`, so the claim and the fixture agree.
  **True.**
- "with the fix reverted, 2 of its tests fail": plant 4 gives 2 failed. **True.**
- "Runs 4, 6, 8 ... cancelled after exactly 5 h 50 min": run 38801338770's step 6 ran 20:22:16Z to 02:12:16Z,
  which is 5 h 50 min. **True** (I checked one of the three).
- "a `failure` already posted through the workflow's own step" (story scope 1): **false for `forecast-capture`'s
  gate job** (SF1).
- Story context: "A job GitHub never starts posts nothing". I found it is worse than stated for
  `participant-oi-watch`. That workflow runs on a cron with 28 slots a day from 14 Oct 13:29 UTC. GitHub's run list
  shows **3 runs ever** (14 Oct 18:50, 15 Oct 15:32 and 19:20 UTC), so about 45 of 48 slots never started. O10's
  `workflow_run` cannot see these, by design. Part 2's O8 row for participant OI is the only backstop, so it must
  treat "no check row by 23:30" as missed. For the orchestrator and the owner: a 15-minute cron on GitHub's free
  scheduler is not a reliable capture clock **[strong, run list]**.

## Rules

- Secrets: none in files. Token values never printed; `RunSourceError` names the HTTP status only, tested.
- Sources' terms: GitHub's own API with the run's `GITHUB_TOKEN`, read-only on runs. Fine.
- SOLID, KISS, DRY: `RunSource` interface plus `GitHubRuns` adapter, injected in the CLI. Small modules. No
  over-engineering.
- Lane: 1 (a new workflow, Slack output). Merge only after this FAIL's two should-fix items pass re-judging. Part 2
  is judged separately.

## Addendum 1: re-judge at f3ab7413 (code at 97213d61; also covers f1a0f4e1, 3dc1675f and 14446e7a, which came after c31ec103)

**Verdict: PASS for part 1** (criteria 1-4, 6 and 8 met; criteria 5 and 7 are part 2 and the live runs). 1 new
minor.

Gates on f3ab7413, full history: **7397 passed**; ruff, ruff format (1319 files), `check_imports.py` and the record
scan (6613 files) are all clean.

| Finding | Builder's answer | My check | Result |
|---|---|---|---|
| SF1: a failed job without an alert step is silent | `needs_alert(error, jobs)` stays quiet only on `failure` when every failed job ran a step named "Alert..." or "One line to..." (conclusion success or failure); every other conclusion alerts. A test makes every step that calls `build_alert_sender` start with one of those prefixes | Code read. Plant "skipped counts as ran": caught. Plant "only the 'Alert' prefix": 2 failed. forecast-capture's gate case is tested (gate failure, capture skipped). participant-oi-watch's always() step posts exactly when the job fails, so quiet is right there | **Accepted** |
| SF2: the librarian used today's date | step `due` (`participant-oi due-day`) feeds `DAY` to both `watch --day` and the librarian | Plant: the librarian goes back to `date +%F`: caught. Plant: `--day` dropped from the watch: caught | **Accepted** |
| Minor 1: `git add` test | every path on every line | the extra-path plant from round 1 is now caught by the new test (same regex logic, read) | **Accepted** |
| Minor 2: re-run attempts | the row link names `/attempts/<n>` after the first attempt | Plant: the attempt suffix removed: caught | **Accepted** |
| Minor 3: queued runs cancelled in a group alert | kept on purpose: that slot's capture did not run | Reasonable: no watched workflow uses cancel-in-progress, and the owner prefers a line to silence | **Accepted** (the owner's rule) |

Since round 1 (not in judge 350):
- `record-error` writes the same row for routines, with no alert because the routine posts its own line. It is
  small and tested.
- The duplicate key is now (run URL, kind), so A19's episode rows, which share a run's URL, cannot hide that run's
  later cancel. Plant "key on the URL only": caught.
- The new known limit (nse-margins can give a duplicate line) is stated, and a duplicate beats a silence.

**New minor:** `needs_alert` needs all failed jobs to have run their alert step. Changing `all` to `any` passes every
test (139 passed), because no test has two failed jobs with only one alerting. No watched workflow can produce that
today: forecast-capture's `capture` needs `gate`, and the others have one job. Add the two-job case when a workflow
gains a second independent job.

Merge note: part 1 may merge. Criterion 7's run logs can only exist after the merge; cite them in part 2. Whichever of
O10 and A17 (judge 351) merges second adds `global-cues` and `vix-history` to the watcher's list.

## Addendum 2: 0db3f682 (one commit after the PASS head f3ab7413)

**Verdict: PASS; part 1 may merge at 0db3f682.**

The change: a `news-capture` run (A19's poller) that is cancelled before any step ran counts as replaced, so it gets no
row and no line. Every other workflow's cancelled-before-start run still records and alerts (judge 350, minor 3
kept). That answers judge 352 SF2 from O10's side.

The rule is scoped by name (`REPLACEABLE = ("news-capture",)`) and needs both `cancelled` and no step that ran. The
three tests cover the replaced run, a news run cancelled after a step (still a failure), and another workflow
cancelled before a step (still a lost slot).

Accepted risk: an owner who cancels a queued news run by hand is also silent. That is harmless, because the kick
workflow dispatches again.

## Addendum 3: 7aaa0259 (0db3f682 plus a merge of main plus two watched names)

**Verdict: PASS. Merge 7aaa0259.** Against its merge base with main (2451d678), the branch changes only O10's own 18
files. The one new change is `capture-watch.yml` listing `global-cues` and `vix-history` (A17 merged first, as judge
351's merge note asked). The builder reports 7852 passed and 15 xfailed on that tree.

Merge notes:
- O12 is now on main, so the merged tree must pass `tools/check_numbers.py`. `response_254_o10-capture-health.md`
  needs its registry row: re-seeding is the merger's job, done only with the orchestrator, and never by hand.
- After O10 merges, A20a and A20b add `fo-masters` and `circulars` to this list, as judges 358 and 359 say.
