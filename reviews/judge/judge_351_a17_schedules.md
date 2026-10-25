# Judge 351: A17 schedules, global cues and India VIX months on GitHub Actions (story/a17-schedules @ 32d3885d)

Judge F (independent). Claims `reviews/claude/response_260_a17-schedules.md` (renumbered from 256), base `22fc7439`,
head `32d3885d`. Lane 1 (schedules, outside services). Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 should fix, 3 minor)

The two workflows are small and follow the existing jobs' pattern. They commit only their own data paths, never
print secrets, and send failure rows through O10's watcher rather than a second format, as the orchestrator asked.
The run times are argued from the sources. One failure path posts nothing.

## Gates (exact head, full history)

| Gate | Result |
|---|---|
| pytest `-n auto` (env without the Slack token) | **7360 passed**, 2 warnings, 215 s |
| `ruff check`, `ruff format --check` | clean, 1314 files formatted |
| `tools/check_imports.py`, `tools/check_records.py` | clean; record scan clean (6610 files) |
| 350-line limit | workflows 76-78 lines, test 79 |

## Planted mutations (reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | morning cron 22:11 UTC (03:41 IST, before the Treasury file) | yes |
| 2 | alert grep drops STALE | yes |
| 3 | VIX month = next month | yes |
| 4 | the cue alert step disabled (`if: ${{ false }}`) | **no**: 5 passed (part of SF1) |
| 5 | the VIX sweep command removed | yes |

## Claims vs reality

1. **Run times fit the publication times** [strong for the code; some for the publication times]. The test pins
   04:30 <= morning < 09:15 and 13:30 <= afternoon < 19:00. Real start times are another matter (see the note
   below): the builder states the 4-5 hour delay openly, and I confirmed it. market-publish's three scheduled runs
   (cron 01:40 UTC) started at 06:41, 06:24 and 06:20 UTC, that is 4 h 40 min to 5 h 01 min late. **True as
   stated.**
2. **Every `python -m fno` command parses with the real parser.** Test plus plant 5. **True.**
3. **The alert names exactly the failed or stale cues.** I checked the regex against the real output lines in
   `fno/global_cues/job.py`: `<cue>: FAILED, ...` (lines 35, 54, 61) and `...; STALE: older than ...` (line 72). Cue
   names are lowercase with digits and `_` (`sp500`, `nasdaq100`, `us10y`, `usdinr_rbi`, `usdinr_fbil`, `brent`).
   **True.** The one exception, `checks FAILED (...)` (job.py:48), has no colon after "checks", so it reads "the
   run" (minor 1).
4. **The VIX job asks for the previous IST month.** Test plus plant 3. **True.** `fill` exits 1 while NSE has not
   published the month (`VixFillReport.complete` is false on `not_published`), so each morning until NSE publishes
   posts one line. That is loud, not silent; fine.
5. **Failure rows come from O10's capture-watch, no second format.** **True for the design**, with two
   dependencies. (a) capture-watch must list `global-cues` and `vix-history`, otherwise O10's own test
   `test_every_job_is_watched` (judge 350) fails on the tree that holds both. Whichever merges second adds them.
   (b) Under O10 at c31ec103, a `failure` run is recorded but not alerted, which matters for SF1.
6. **Gates.** Reproduced: 7360 passed.

## Should fix

**SF1. A cue (or VIX) failure followed by a failed commit posts nothing [strong: Actions semantics plus code
read].** In both workflows, the "One line to #fno-desk" step has `if: ${{ steps.fill.outcome != 'success' }}` with no
status function. GitHub then applies `success()` to it, so the step is skipped once an earlier step has failed. The
commit step (pull, then push, no retry) is that earlier step.

The other alert step, "Alert #fno-desk when the job itself failed", runs only when `fill` succeeded
(`failure() && steps.fill.outcome == 'success'`, and also `sweep` for VIX). So when a cue fails and the push also
fails (a push race at 04:41 with another job), neither step runs. The run ends `failure` with nothing posted, and
O10's watcher does not alert on `failure`. That is the silence the owner ruled out.

No test covers the alert condition: plant 4 disabled the cue alert step and all 5 tests passed.

Fix expected: `if: ${{ always() && steps.fill.outcome != 'success' }}`, and the same for VIX with `sweep`. Or make
one `always()` alert step that names the cues and the commit result together. Add a test that reads the alert steps'
`if` and fails when it lacks `always()`, or one that evaluates both conditions over the four fill/commit outcomes.

## Minor

1. A failure in the checks (`checks FAILED (...)`) is named "the run"; add `checks` to the names.
2. The unquoted step name `Alert #fno-desk when the job itself failed` is cut to "Alert" in GitHub's UI and in
   O10's rows: YAML reads ` #` as the start of a comment (O10's claims noted the same). Quote it.
3. The commit step pushes once with no retry, so on a race the data waits for the next run (Drive keeps the copies;
   the 31-day look-back refills). It would be better to retry as capture-watch does.

## Note for the orchestrator and the owner (not a finding against this change)

On the observed delays (4 h 40 min to 5 h 01 min on every morning scheduled run I checked), the 04:41 IST run will
usually land at about 09:20-09:40 IST. The US closes will then be marked late at 09:15 on most days, so the "cues
known before the open" purpose will mostly fail. The builder states this and the as-of rule keeps it honest (late,
never wrong) **[strong for the delays]**.

Remedies, each **reasoning only**:
- (a) an earlier slot, which needs proof of when Cboe and Nasdaq publish the close, because `once_a_day` locks the
  first copy of the day;
- (b) a runner outside GitHub (a scheduled Claude routine already runs at 14:33 IST);
- (c) accept late-marked cues.

That choice is the owner's. The same delay makes the 07:11 IST VIX job run at about noon, which is harmless for
month files.

## Addendum 1: re-judge at 97fe83ea (014b4cd1 the judge 351 fixes; 97fe83ea the orchestrator's earlier slot; main merged)

**Verdict: PASS. A17 schedules may merge** (the second of O10 and A17 to merge adds `global-cues` and `vix-history`
to capture-watch's list).

Gates on 97fe83ea: **7715 passed**; ruff, ruff format (1388), `check_imports.py` and the record scan (6704) are clean.

| Finding | Builder's answer | My check | Result |
|---|---|---|---|
| SF1: a failed cue or VIX step plus a failed commit posted nothing | one alert step, last, `if: ${{ !cancelled() && (steps.fill.outcome != 'success' \|\| failure()) }}` (VIX adds `sweep`); the test evaluates the `if:` for clean, failed-step, failed-commit, skipped and cancelled runs and asserts one sending step that ends `exit 1` | Plants: the `!cancelled()` guard removed (back to an implicit success): 1 failed. `sweep` dropped from the VIX condition: 1 failed. `!cancelled()` rather than `always()` is right, because O10 posts cancelled and timed-out runs (judge 350 add. 1). O10's needs_alert sees this step: the name starts "One line to" and is quoted | **Accepted** |
| Minor 1: `checks FAILED` named "the run" | the grep also takes `<name> FAILED` | read | **Accepted** |
| Minor 2: unquoted step names | quoted | read | **Accepted** |
| Minor 3: no push retry | 3 tries, 10/20/30 s | read | **Accepted** |
| Note: the 04:41 run lands after 09:15 | main run 03:41 IST (22:11 UTC), 04:41 as the Treasury backup, 14:11 for RBI. The test asserts main after 02:30 IST, main + 5 h before 09:15, and backup in 04:30-09:15 | 03:41 + 5 h 01 min = 08:42, before the open. It is 71 min after the winter (EST) close, 02:30 IST, which applies from 1 Nov 2026 | **Accepted** |

**Condition to measure (some risk, stated by the builder):** under the owner's once-a-day download rule, if Cboe's
or Nasdaq's file at 03:41 IST does not yet hold the US close, that close is first seen a day late every day, and
nothing alerts: the 7-day stale limit never fires on a one-day lag. The builder will measure it after a week. The
orchestrator should hold them to that measurement, with the first-seen versus value-date lags per day cited.

**Other workflows (reported by the builder, checked by me):** index-closes, nse-margins and panel-days have the same
implicit-`success()` alert after a commit step. When the librarian fails and the commit then fails, neither alert
step runs. O10's watcher at 0db3f682 now covers this: the run is a `failure` whose failed job ran no "Alert" or "One
line to" step, so the watcher posts. No change is needed in those frozen or other-owner files once O10 merges.

## Addendum 2: the lag condition measured (response 298 and A17e amendment 1, story/a17e-global-markets @ a6a8c641)

**The condition is met: it was measured, and it found a real defect. The fix is accepted, with one minor.**

The measurement, read back from every archived copy in Drive [strong as reported]:
- Cboe's S&P 500 copy held the previous US close on every weekday morning (lag 0);
- Nasdaq's Nasdaq-100 copy lacked it on 17, 20 and 21 Oct (lag 1 US trading day every time);
- nothing alerted, which is exactly the silent systematic lag this condition was set to catch;
- the cause: Nasdaq's API still lacked the 21 Oct close at 17:17 New York.

The fix (A17e amendment 1): a twelfth Yahoo cue, `nasdaq100_yahoo`. The `nasdaq100` reading takes Yahoo's previous
close until Nasdaq's copy has the date, and the overlap check guards the pair: equal on 15, 16 and 20 Oct, 0.01 apart
on 19 Oct. A test uses the 20-21 Oct copies.
- Rejected, rightly: a second Nasdaq download breaks the owner's once-a-day rule and would still miss 09:15.
- Until A17e merges, the S&P 500 is the on-time US cue and the Nasdaq-100 is one day late, never wrong. That is
  stated, not hidden.

**Minor: the class of defect can still be silent.** The fix repairs Nasdaq, but nothing yet alerts when any cue's
newest value is behind its market's expected date at 09:15. That covers Yahoo lagging too, or another publisher
slipping. A17b's reader already computes `behind` against each cue's calendar. Name every cue that is `behind` at
the 09:15 as-of in the run's line (once per episode). Then a lag like this one is seen the first morning, not found
by a judge's measurement a week later. This belongs in A17e's code round.
