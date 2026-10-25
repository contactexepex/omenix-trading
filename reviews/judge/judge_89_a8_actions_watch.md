# Judge 89: story A8 on GitHub Actions, `story/a8-actions-watch` at f9c6b4e (claims in response 91)

Standard: `docs/JUDGE.md`. What I checked:
- the full diff;
- the cron evidence against the Actions API and the git history of the workflow files;
- a real git union merge;
- my own probe and 6 mutation plants;
- the full gates on a trial merge with `main`.

## Gates

On a trial merge of f9c6b4e with `main` (ec24b60):
- 3,139 passed, with `FNO_SLACK_BOT_TOKEN` unset;
- `ruff check` and `ruff format --check` clean;
- `check_imports` clean.

No file is over 350 lines.

## Criteria

| Criterion | Result | Evidence |
|---|---|---|
| `check-once`: one check per run; nothing once the file is present; a closed day checks nothing | MET | Code read; tests; my plants. |
| Rewrite re-read "at most once a day" | **NOT MET (must-fix 1)** | See finding 1. A late-night run for the previous day makes the next day's re-read skip. |
| (b) Due day: a run before 12:00 IST checks the previous day | MET | `due_day`. My plant (always today) was caught: 2 failed. Reasoning below. |
| Still-absent alert once a day, from 23:15, including after midnight | MET | My plant (`return True`) was caught. |
| (c) `merge=union` safe for the append-only log | MET | Real git merge, below. Planting the removal was caught. |
| Workflow: cron, concurrency, hook, no `--no-verify`, Slack secret only | MET | My plant (`cancel-in-progress: true`) was caught. The cron `7,22,37,52 11-17 * * *` UTC is 16:37-23:22 IST, as claimed. |
| Workflow: crash or not-committed alert step | PARTLY (should-fix) | My plant `always()` -> `failure()` passed all 13 tests. With `continue-on-error` on the check step, `failure()` skips this step when only the check failed. A crash would then send no alert, and the run would show green after alerts. Nothing pins `always()`. |
| (a) Cron-lateness evidence | PARTLY (must-fix 2) | See finding 2. The direction is right; two of the six rows are false. |
| (d) "A8 safety unaffected, only measurement suffers" | PARTLY | True for the availability rule. Not true for rewrite detection while finding 1 stands. |

## Finding 1 (must-fix): the once-a-day rewrite re-read is skipped after any late-night run

`_rechecked_on(day)` treats any row with `c.day < day` and `checked_at.date() == day` as "today's re-read already ran".

A run after midnight that checks the previous day (the due-day path this story adds) writes exactly such a row. So
the next evening's runs skip the re-read of the last 5 seen files.

Probe:
- Friday's file is present.
- Monday's file is found by a 00:30 Tuesday run.
- NSE rewrites Friday's file on Tuesday.
- Tuesday 18:00 run: no REWRITTEN alert and no re-read rows. The probe failed: "Tuesday's run skipped the re-read".

Why it matters:
- The skip repeats on every day whose previous file was first found after midnight. That is the case this story exists
  to handle, given GitHub's lateness.
- A file can leave the 5-session window unread.
- A rewrite that goes unlogged leaves `LastWriteBoundRule` with the old write time. That is the look-ahead risk judge 15
  set this check to catch.
- The monthly sweep (`participant-oi-sweep.yml`) limits the damage to weeks, not forever.

Root cause: the design infers "re-read done" from rows that are not re-read rows. A fix must mark or identify the
re-read itself, not any earlier-day row. It also needs a test with a late-night due-day row.

## Finding 2 (must-fix, record): two lateness rows in response 91 are false

Checked against the Actions API and `git log` of the workflow files.

| Row in response 91 | My check |
|---|---|
| index-closes, 13 Oct 15:41 "never, dropped" | **False.** `index-closes.yml` was first committed at 17:28 UTC on 13 Oct, after that slot. Its first run was a manual dispatch at 17:28. |
| participant-oi-release, 13 Oct 11:41 "never, dropped" | **False.** The workflow was first committed at 14:58 UTC on 13 Oct (c0e2663), after that slot. |
| index-closes, 14 Oct 02:11 -> 07:30 and 06:11 -> 11:49 | Started times confirmed (runs 2 and 3, `schedule`). The API does not name the slot a run belongs to. The 11:49 run is at least 5 h 38 m late whichever slot it served. Strong evidence for at least one run about 5.6 h late. |
| participant-oi-release, 13 Oct 17:15 -> 21:52, cancelled | Confirmed (run 4, `schedule`, ended 03:43 UTC as cancelled). |
| participant-oi-release, 14 Oct 11:41 not started | Confirmed: no run 5 at 13:45 UTC, more than 2 h late. |
| (extra, mine) forecast-capture, cron 08:30 UTC | **Zero runs ever.** The 14 Oct 08:30 slot had not started 5 h 15 m later. It existed since 16:30 UTC on 13 Oct. |

Conclusion: GitHub schedules on this repository start hours late (strong evidence). "Some never" is supported only by
today's forecast-capture slot so far, not by the two 13 Oct rows. Correct the table in response 91.

## (b) The due-day rule: agreed (reasoning plus tests)

- NSE publishes in the evening (Last-Modified 18:48 and 19:19 IST on 12 and 13 Oct). So a run between 00:00 and 12:00
  can only usefully check the previous evening's file.
- A morning run on a day after a closed day (Monday checks Sunday) prints "not a trading day", which is correct.
- First-seen times from such runs are at most 12:00 the next day. That is before the 15:00 decision, so the lag is still
  next session.
- Limitation (pre-existing; the old routine shares it): a file first published after noon the next day is never seen as
  present. It is alerted as "still absent" but never measured. That day is missing from the measured rule's maximum.

## (c) `merge=union`: safe for this log (strong evidence: a real git merge)

Base: header plus one row. Each side appends two rows, one of them identical on both sides.

Result:
- the header appears once;
- every distinct row is kept;
- the identical row is kept once;
- no conflict.

For this log, identical rows cannot come from two writers (`checked_at` has microseconds). Merging them would lose no
evidence anyway.

Limits:
- Rows end up in merge order, not time order. Every reader I found sorts by `checked_at` (`first_seen_times`) or takes
  the minimum (`first_present`).
- Union would silently keep both versions of an edited line. That is safe only because the log is append-only; the
  header check in `ReleaseLog.append` stays.

## (d) Safety versus measurement: partly agreed

- **Availability rule: agreed (strong evidence, from code).** `sessions_until_usable` only increases with `first_seen`.
  A late check gives a later first-seen time, so the lag is equal or larger: the safe side.
- **Measurement: agreed, and worse than the response says.**
  - The log has 22 rows and **zero measured days**. 12 Oct is present with no absent row before it, and its present row
    has an empty Last-Modified. 13 Oct has one absent row only. 14 Oct has 17 absent rows so far.
  - With runs about 5 h late, the first run starts around 21:50 IST, after NSE's release. Such a run can never produce
    an absent row before the present one.
- **Rewrite detection: not unaffected** while finding 1 stands.

## The builder's Last-Modified proposal: my view (an A8 rule change for the owner; reasoning plus data)

Do not adopt NSE's Last-Modified as the release time as it stands.

- It records when NSE last wrote the file, not when the public could fetch it. The unsafe case is a file written before
  it is reachable: Last-Modified would then be earlier than the real availability, which means look-ahead.
- Our own data show the time moves. The 13 Oct archive scan has 2019 files with a 17 Jan 2019 write time, and the
  sweep log shows a 2023-09-11 file written on 2023-09-16. A moved time errs later, which is safe, but it shows the field
  is a write time, not a publication time.
- One present row (12 Oct) has no Last-Modified at all.
- It could be used only after calibration: on days with an absent check followed by a present check within 15 minutes,
  Last-Modified must lie between the two. Any day with Last-Modified before the last absent check rules it out, or forces
  a margin. Today there are no such days to calibrate on.

A simpler option exists. It is still a rule change for the owner (reasoning only, not built):
- A first-seen time is an upper bound on the release whether or not an absent row precedes it.
- Because the lag only grows with `first_seen`, counting days with no absent row would still be safe for the rule.
- Then cron lateness would no longer block reaching the 20 days.
- What it gives up: a true release-time distribution. The rule never needed that, because it only asks which session's
  15:00 decision may use the file.
- The selection bias against very late days remains in both designs.

## Follow-ups (not blocking)

- `git push` has no retry. A race with another writer loses that run's rows; an alert line covers it.
- The secret's presence is unverified: no run has sent an alert yet. Same as the O6 workflows.
- Response 91's recommendation not to disable the Claude routine on one evening's evidence: agreed.

## Project rules

- No orders placed; no secrets in files.
- Composition: `build_alert_sender` comes from `composition`, and the recorder from its builder. Fine.
- Constants are at the module top.
- Files are under 350 lines.

## Verdict: FAIL for f9c6b4e

Must-fix:
1. The once-a-day re-read is skipped after a late-night due-day row. Fix the root cause and add a test.
2. Correct the lateness table in response 91 (two false "dropped" rows).

Should-fix: a test that pins `always()` on the alert step.

## Addendum 1 (14 Oct 2026): re-review at b33f2c0 (code tree 23fe636)

| Item | Result | Evidence |
|---|---|---|
| Must-fix 1: re-read skipped after a late-night due-day row | MET | The re-read is now recorded per due day in `release_rereads.csv` (`RereadLog`). The record is written only when every re-read file answered. My exact sequence is a test (`test_a_late_run_for_the_previous_day_does_not_stand_for_the_next_days_re_read`). My 4 plants were all caught: `done()` matching earlier days (3 failed); always recording, even when unreachable (1 failed); always re-reading (1 failed); recording the wrong day (1 failed). |
| Must-fix 2: lateness table | MET | Both false rows are removed and the correction is stated. The builder's correction of my line is right: forecast-capture's first run ever is run 1, event `schedule`, started 13:56:51 UTC on 14 Oct. That is the 08:30 slot 5 h 26 m late, and it ran on 73ec163. participant-oi-release still has no run for today's 11:41 slot (latest is run 4). |
| Should-fix: `always()` pinned | MET | My plant `always()` -> `failure()` is now caught. The YAML defect the builder found is real: an unquoted ` #` starts a comment, so the step name was cut. It is now quoted, and my plant removing the quotes is caught. |
| Last-Modified proposal | MET | Struck through and not built. |
| Composition | MET | `build_release_check_once` sits in `fno/composition.py`; the path constant sits in `fno/storage/wiring.py`. |

Remaining design notes (follow-up, not blocking):
- While NSE stays unreachable during a re-read that found a rewrite, every run re-alerts REWRITTEN. This is noisy but errs on the safe side.
- `RereadLog` has no header check, unlike `ReleaseLog`.

Gates, on a trial merge with `main` (40118da):
- First full run: **1 failed, 3,143 passed.** I could not identify the failing test: the run used `-p no:cacheprovider` and I had not passed `-rf`.
- Two more full runs on the same tree with `-rf`: 3,144 passed each time.
- Five runs of `tests/research_data` and `tests/pipeline`: all passed.
- `ruff check`, `ruff format --check` and `check_imports` are clean. All files are under 350 lines.

Since 73ec163, `main` changed only data and log files under `fno`, `tests`, `tools`, `.github`, `config.yaml` and `db`. That diff is empty.

**Follow-up (open):** a test somewhere fails intermittently, about 1 run in 3 today. It is not shown to come from this branch. I will name it the next time it shows; CI on the merge is the next check.

**Verdict: PASS** for b33f2c0. Merge it. After the merge I check `main` and CI.

## Addendum 2 (14 Oct 2026): merge 66cb98d MET

- **Merge matches the recomputation.** Parents are 4639a9b and b33f2c0. My recomputed `git merge-tree` of the two
  parents equals 66cb98d exactly (empty diff).
- **No unjudged code on `main`.** From 66cb98d to `main` 467b74f, nothing changed under `fno`, `tests`, `tools`,
  `.github`, `config.yaml`, `db` or `.gitattributes`. The later commits are logs and judge files.
- **CI is green** on ea6fe1d (the first push that carried the merge), on 14105e8 and on f0ab8a8.
- **The 3,145-pass claim matches.** 3,144 tests at b33f2c0, plus `main`'s new test, makes the builder's count of
  3,145 consistent.
- **The flaky-test follow-up was very likely my own plant harness, not a project flake** (judge 90). A stale `.pyc` was
  left behind when a file was restored within the same second at the same size. The builder's hunt may find nothing.
