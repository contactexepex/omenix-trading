# Judge 359: A20b, NSE and SEBI circulars kept point in time (story/a20b-circulars @ 3dd9ba9f)

Judge F (independent). Story `docs/stories/A20-rules-and-dates.md` at e50ca714 (text PASS, judge 353 add. 1), claims
`reviews/claude/response_266b_a20b-circulars.md`. Lane 1 (NSE, SEBI, Drive, Slack, a workflow). Labels: **strong**,
**some**, **reasoning only**.

## Verdict: FAIL (1 should fix, 1 minor)

The job itself is careful:
- circulars listed at first sight with a file status;
- a 3-day retry, then `abandoned`;
- the 14-day window, which I measured at 320 items;
- a calendar-based stale rule;
- a known episode stays quiet;
- a refused Slack post is never saved as "alerted" (the builder's own blocking fix).

Gates on 3dd9ba9f: **7424 passed**; ruff, ruff format (1330), `check_imports.py` and the record scan (6626) are clean.
My window plant (14 → 13 days) fails 2 tests.

The failure is in how the job's workflow and O10's watcher fit together: together they post every hour during an
episode.

## Should fix

**SF1. During an open episode, O10's watcher posts a line every hour, undoing "once per episode" [strong: code read
of both].** With a known problem the job posts nothing, calls `spoken()` (which writes `posted=true` to the step's
outputs) and exits 1 (`job.py`, `run`: "Any open problem makes the run exit 1"). The workflow's alert step has
`if: ${{ failure() && steps.circulars.outputs.posted != 'true' }}`, so it is **skipped**.

O10's watcher (0db3f682, judge 350 add. 2 PASS) stays quiet on a `failure` only when every failed job ran a step named
"Alert..." or "One line to..." with conclusion `success` or `failure` (`needs_alert` / `_ran_alert`). A skipped step
does not count. So every hourly run while a problem stays open gets O10's line "the GitHub Actions run was failure at
... and posted nothing itself". That is up to about 15 lines a day for one episode, and those lines are also false,
because the job did speak, once, at the episode's start.

Fix expected, in the workflow and not in O10: the alert step runs on every failure and decides inside itself.
`if: ${{ failure() }}`, and the script exits 0 without sending when `steps.circulars.outputs.posted == 'true'`. Then the
step's conclusion is `success`, O10 counts the run as having posted, and only O10's committed row remains (one row per
failed run, which is the record the owner asked for). Add a workflow test that the alert step's `if:` is exactly
`failure()` and that the script reads `posted`.

## Minor

1. The workflow's header still says the NSE circulars API is asked "for yesterday and today"; it is 14 days now
   (`WINDOW = timedelta(days=14)`).

## The same pattern elsewhere (for the orchestrator; not this story's to fix)

Every workflow whose job posts through `StepOutputAlerts` and whose fallback step is skipped by `posted == 'true'`
(A20a's `fo-masters.yml`, judge 358; `index-closes.yml`; `nse-margins.yml`; the frozen `panel-days.yml`) gets one
extra O10 line per failed run once O10 merges. O10's builder listed this as a known limit ("a duplicate is preferred
to a silence"), and I accepted it in judge 350 add. 1. For a job failing once a day it is one duplicate. For an hourly
job inside an episode it is spam. The same one-line workflow change removes it everywhere except the frozen
panel-days.

## Addendum 1: re-judge at a92c20a7 (c4bd3afc the fix; a92c20a7 only renumbers the claims to 284)

**Verdict: PASS. A20b may merge, after a fresh merge of main gated on the exact merged tree.**

| Finding | Fix | My check | Result |
|---|---|---|---|
| SF1: O10 posted every hourly run of an open episode | The fallback step runs on every failure and exits 0 without sending when the job's `posted` output is `true`. The job sets it both when it posted and when the episode was already alerted (`spoken()`). So O10's watcher sees an "Alert" step that ran and adds no line; it still writes its row for each failed run | `tests/circulars` 44 passed. Putting back the old `failure() && posted != 'true'` fails 1 test. A test runs the step's script with `POSTED=true` (exit 0, "already spoke", no python call) | **Accepted** |
| Minor 1: stale header | "the last 14 days" | read | **Accepted** |

The cron comment now says NSE issued circulars on 13 non-session days of 2026, which corrects my own note in judge
353 addendum 1 (my 14-day sample happened to have none on the 2 Oct holiday). Hourly every day is right.

Merge notes:
- add `circulars` to capture-watch's list on main;
- merge main and run the full gates, `check_numbers.py` included, on the exact tree you push.
