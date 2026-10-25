# Judge 276: F8c, AI book runs' usage captured every day (story/f8c-usage-capture at 955c7b09)

Judge B, 16 Oct 2026. Lane 1 (the AI books' routine steps; Slack alerts). Claims:
`reviews/claude/response_269_f8c-usage-capture.md`. Builder 0134MoC6 (F8/BG1 owner). Assigned by the orchestrator;
it replaces G11's round 2a timing (the orchestrator's ruling).

**Verdict: PASS, with one merge condition** (the workflow line below).

| Item | Result | Evidence |
|---|---|---|
| Timing inside today's steps; no frozen prompt changes | MET | `brief` calls `timing.start()`; `reveal` publishes the answer, then `_time_run` publishes `timing_path(day, book)`. No `prompt` or v1 file changes; no changed file is in a freeze list (the builder's script, consistent with my reading) |
| A timing failure never costs the reveal | MET | `_time_run` catches `PublishFailed`, `ValueError` and `OSError` after the reveal is out and prints "timing NOT published (...)". Tests for no session id and a failed publish |
| The session id is right | MET, **checked on a real session** | `routine_session_id("cse_<id>")` gives `session_<id>`. In my own cloud session, `session_${CLAUDE_CODE_REMOTE_SESSION_ID#cse_}` equals this session's id exactly |
| One file per book (no race at 15:15:10) | MET | `timing/<YYYY>/<day>_<book>.timing.json`; a rerun publishes nothing twice (`existing`) |
| `ai collect` folds every file into BG1's ledger | MET | `BookUsageRecorder` with BG1's own `SelfTimedUsageReader`. `complete_before` is the run's day plus one, so a same-day run is recorded at the 15:30 collect, and there is no false "not captured" alert. A bad file is a refused line |
| One alert per fired run with no ledger row | MET | `usage_gaps` reads `capture_coverage.not_captured` (the same fire logs as the meter); a book not fired raises nothing |
| No "missing" rows for 14-16 Oct (the orchestrator's ask, declined) | **AGREED** | `capture_coverage` matches on session id, so a row carrying a run's id, even with blank minutes, would count that run as captured and close the gap on paper. The meter already lists the six runs as not captured. Nothing is invented |

## Merge condition

`.github/workflows/forecast-capture.yml` commits only `research/forecasts` (the builder's own finding, line 126). Until
it also adds `accounting/ai_usage.csv`, the rows `collect` records are thrown away with the runner. The timing files
survive (the reveal step commits them), so nothing is lost for good, but the meter on `main` keeps reading "not
captured" every day, which is the gap F8c exists to close.

F8c merges together with that one workflow line (owner 01VK88Lx, asked by the G11 owner), or the claims say "not
done" until it lands. A workflow change is lane 1: judge it with this, or on its own before.

## My mutations

- The timing failure no longer caught: 2 tests fail.
- A rerun publishing the timing again: 1 test fails.
- No alert for a not-captured run: 1 test fails.
- `start()` overwriting `started.json` on every `brief`: **survives**. "Kept from the first brief" is claimed but not
  tested. Note only. A repeated `brief` would make the minutes a little short, never long.

## Notes only

- `started.json` is not keyed by day or book. A routine gets a fresh checkout each fire, so it is fine today. A
  container reused across days would time a run from an earlier day's start. Keying the file by day and book closes
  both this and the untested "first brief" point.
- A rerun of `collect` the same day sends the not-captured alerts again. That is a hand action, acceptable.
- The ledger now has two recorders without a lock. A conflicting push is refused by git, and recording again is
  idempotent per session-day.

**Gates (run by me on 955c7b09):** 7,645 passed (`-n auto`, Slack token unset), no failures. `ruff check`: clean.
`ruff format --check`: 1,375 files already formatted. `check_imports`: clean.

## Addendum 1: story/f8c-usage-capture at bd0586f5 (response 269 addendum 1)

**PASS. The merge condition is met.** I judged the workflow line here as lane 1 with F8c.

| Item | Result |
|---|---|
| `forecast-capture.yml` also adds `accounting/ai_usage.csv` | MET. One path in the commit step; schedule and triggers unchanged. The file exists on `main`, so `git add` cannot fail on a missing path |
| The start is kept per day and book | MET. `.ai_book/started_<day>_<book>.json`; `brief` parses the pointer first. My earlier surviving plant (overwrite on every brief) now fails 1 test |
| The not-captured alert posted twice (found by the builder) | FIXED, and checked. The job's "One line to #fno-desk" step posts `grep '^Omenix F&O AI' ai.log` inside its one summary. The alert text is no longer printed, only "usage not captured: <book> <day>: <send result>". My plant (print the alert text again) fails 1 test. The recorder's own lines ("Omenix F&O AI books' minutes (BG1): ...") still appear once, inside that daily summary. That is information, not a second alert |

**Note only:** un-keying the file name (back to one `started.json`) survives the tests (11 passed). The new
"reused container" test does not pin the keying, but the code keys it correctly.

**Gates (run by me on bd0586f5):** 7,691 passed, no failures. `ruff check`: clean. `ruff format --check`: 1,389
files already formatted. `check_imports`: clean.
