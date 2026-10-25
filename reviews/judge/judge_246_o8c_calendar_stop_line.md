# Judge 246: O8c calendar stop line (story/o8c-calendar-stop-line at 2b2af9b0)

Judge B, 16 Oct 2026. Lane 1 (an outside service's alert line, a workflow). Claims: `reviews/claude/response_153_o8-health-check.md`
addendum 4; story O8c at the end of `docs/stories/O8-health-check.md`. The orchestrator's check for this batch: fails
loudly and by name, never silently; nothing posts twice; no date invented.

**Verdict: FAIL.** One should-fix: one stop now posts more than one line, against the batch's "nothing posts twice"
and against the workflow's own step text.

## Criteria

| Criterion | Result | Evidence |
|---|---|---|
| A `CalendarError` from any command gives one named line and exit 1, not a traceback | MET | `fno/cli.py` `except CalendarError` goes to `calendar_stop`; my runs on 2b2af9b0 for 2027 dates: `data-librarian index-close`, `data-revisions sweep`, `pipeline index-closes` and `data-librarian span-bod` each print "Omenix F&O `<command>` stopped: 2027-01-01 is outside the calendar (...): add every row of NSE's 2027 holiday circular ..." |
| No date invented | MET | the calendar's own words; no fallback |
| Commands that handle the calendar themselves post once | MET | the 3 pm recorder, A16 and the back-fill catch it before `main`; test covers a self-handling command |
| panel-days.yml unchanged (v3 freeze) | MET | byte-identical to main; its Python step gets the named line through `main` |
| **Nothing posts twice** | **NOT MET** | see the should-fix below |

## Should-fix: one stop posts several lines (concrete paths)

1. **index-closes, a named append stop, normal year.** The diff drops `steps.append.outcome == 'success'` from the
   final alert's `if:`. When the librarian succeeds and `IndexCloseAppender.run` stops with its own `STOPPED` line (a
   `PanelBuildError`), it posts that line and returns 1. The "Fail the run when the append stopped" step then exits 1,
   so `failure()` is true and "the job itself failed" posts as well: **two posts for one stop**. One such path: the
   warm-up file is more than 7 days behind after an outage. The librarian's range is the last 7 days, but the append
   starts from the last warm-up day plus one, so the append stops on an older day the librarian never covered. The
   step's new text says the opposite ("a named stop posts its own line; any other crash is alerted below").
2. **Every calendar-touching workflow from 1 Jan 2027 until NSE's 2027 rows are added.** `main` now posts for every
   command, and the workflows' own alert steps still post too. Per run, from my runs above and the workflow files:
   - `index-closes.yml`: librarian, revisions and append each post their own calendar line (3), plus the librarian
     alert step: **4 posts**.
   - `nse-margins.yml`: `margins nse-span --due-day` posts from the librarian step and again from the revisions step
     (2), the margins job posts its own `CalendarError` line (judge 245), plus the librarian alert step: **4 posts**,
     at two runs a day.
   - Workflows whose final alert is a bare `if: failure()` (`flows-download`, `forecast-scores`, `market-publish`,
     `participant-oi-*`, `postmortem-weekly`) post the named line plus "the run failed" for any calendar stop in their
     commands: **2 posts**.

   Before this diff, each of these runs posted once (wrongly worded, or for index-closes and nse-margins blaming Drive).

The root cause is that two layers now alert for the same stop: the cli-level handler and the workflows' per-step and
`failure()` steps. Neither knows about the other. The design is the builder's call. Whatever is chosen, one stop in one
run should post one line, and the generic line should post only when nothing else did. Possible routes:
- a distinct exit code for "already posted", which the alert steps read;
- the cli handler only prints, and the workflow posts the step's last line;
- or the owner accepts N lines per run in writing in the story.

The panel-days limit (a freeze, an owner call) is fine as reported.

## Claims vs reality

- "Nothing is posted twice": true only for the self-handling commands. Not true across a workflow run (above).
- "the final failure() step is no longer gated on steps.append": true, and it is the cause of path 1.
- Real run `pipeline index-closes --to 2027-01-04`: reproduced, named line, exit 1.

## Project rules

`calendar_stop.py` 31 lines; the template is a module constant; `send` is injectable for tests. Fine.

## Mutation (real case)

`except CalendarError` in `fno/cli.py` changed to an unrelated type: 2 tests fail. Caught. No test covers the
workflows' alert gates (path 1), which is why it went unseen.

## Gates (run by me on 2b2af9b0)

`env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto -p no:cacheprovider`: 6,972 passed. `ruff check`: clean.
`ruff format --check`: 1,237 files already formatted. `check_imports`: clean.

## Addendum 1: story/o8c-calendar-stop-line at 7fadc85f (O8b merged in at 1fe47875)

**PASS.** The should-fix is closed at its root. O8b's part was judged in judge 240 addendum 1 (PASS at 9232281d). Its
private helper is now the shared `StepOutputAlerts`, with the same behaviour and tests.

| Item | Result | Evidence |
|---|---|---|
| No second alert layer: the cli handler prints, never posts | MET | `calendar_stop` only prints. My runs at 7fadc85f, `pipeline index-closes --to 2027-01-04` and `data-librarian index-close` up to 2027-01-04, print the named line and attempt no post (no "alert NOT sent" line, the Slack token unset) |
| The gap still reaches Slack | MET | O8b's once-only 45-day warning, and from the first uncovered day the health check: `health check --dry-run --at 2027-01-04T20:00` prints "health check FAILED: CalendarError" (the check catches it inside its `try` and posts it) |
| index-closes: one line per failing run (path 1 of the should-fix) | MET | the index-close sender is wrapped in `StepOutputAlerts`, so a named STOPPED append records `posted=true`; the final step runs on `failure() && librarian success && append posted != 'true'`. A calendar gap fails the librarian, which posts its one line. An unexpected append crash posts nothing, so the final step speaks |
| A posted mark only after Slack accepted | MET | `StepOutputAlerts.send` writes only on `SENT` (test) |
| panel-days.yml unchanged (v3 freeze) | MET | byte-identical to main |

**My mutations (real cases):**
- The index-close sender not wrapped: 1 test fails.
- The final step's `posted` condition removed: 1 test fails (the test reads the workflow).

**Notes only:**
- nse-margins in a 2027 run still gives two different lines: the librarian step's alert, then the margins job's own
  `CalendarError` line (judge 245). The duplicate `--due-day` posts are gone. This is the pattern judge 245 noted.
- panel-days (frozen): if its librarian succeeds and its append then stops on the calendar, no line is posted for that
  run. The health check's daily "FAILED: CalendarError" covers the same gap. Changing it needs a new protocol version
  (the owner's call), as the builder reported.

**Gates (run by me on 7fadc85f):** 7,128 passed (`-n auto`, Slack token unset). `ruff check`: clean. `ruff format
--check`: 1,267 files already formatted. `check_imports`: clean.
