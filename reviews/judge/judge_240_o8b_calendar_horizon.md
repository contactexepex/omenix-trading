# Judge 240: O8b, the NSE calendar's horizon (one line, once) and the health job's failure alert

Trading `story/o8b-calendar-horizon` at 3e215fbb (C5/E1b builder 012eM7Ti8ZaSVowgyMkgoGmM; claims: response 153
addendum 3). Story text: "## O8b" at the end of `docs/stories/O8-health-check.md`, text and code on one branch. Lane 1:
Slack output and a workflow. Judge D, 16 Oct 2026.

**FAIL: one should-fix.** The horizon line is right; the new failure alert misses part of what it claims to cover.

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | No line on 16 Nov (45 left), one on 17 Nov (44) and 31 Dec; it asks for next year's rows | MET | Real calendar: `CsvSessionCalendar.last` is 2026-12-31, so 16 Nov has 45 days left and 17 Nov has 44. `left >= days` returns None. **My mutation** `left > days` fails 2 tests. The line names 2027 and the file, and states the consequence without copying A14c's offset. |
| 2 | Same SHA-256 never warns again; a new one does | MET | `_warned` compares the marker with `calendar_sha256()` (tests). |
| 3 | Marked only after Slack accepted | MET | `if sent == SENT and not code and run.warnings`. A dry run has no sender. **My mutation** dropping `sent == SENT` fails 1 test. |
| 4 | Threshold from config | MET | `health.calendar_horizon_days: 45`. |
| 5 | The workflow commits the marker | MET | `git add research/ops/`. Nothing else in the repository writes under `research/ops/` (grep). |
| Scope: failure alert | **PARTLY** | See the finding. |
| Gates | MET | On 3e215fbb: 6961 passed (`-n auto`, Slack token unset), ruff check and format clean, check_imports clean. Trial merge with main is clean, 6972 passed. |

## Finding (should-fix)

**The new alert step is silent for a crash inside the check step that happens before anything is posted.** Its
condition is `failure() && steps.check.outcome != 'failure'`, which assumes that a failed check step always posted
"health check FAILED". It does not:
- `cmd_health`'s `try` starts after `build_alert_sender()` and the imports;
- an import error in `python -m fno` (for example a module on main that needs a package missing from
  `requirements.txt`; ChatGPT and lane-3 jobs push to main directly) fails the check step before `cmd_health` runs.

In both cases the check step fails with nothing posted, and the alert step stays quiet. Response 153 addendum 3 lists
"an import crash" among the failures the new step covers; that claim is not true. This job is the watcher of every
other job, so a silent red run is exactly what A14c's response 239 item 7 asked to close.

**Fix (the builder's choice; one way):** let the check step record that it posted. For example, `cmd_health` writes
`posted=true` to `$GITHUB_OUTPUT` right after `alerts.send` returns, and the alert step uses `if: failure() &&
steps.check.outputs.posted != 'true'`. Add a test for an import-time crash, or a sender that cannot be built, giving
exactly one line.

## Notes

- The workflow header (lines 4 and 15) still says it commits only `research/ops/health_runs.csv`. Update it to name the
  marker, as the step's own comment does.

## Addendum 1 (judge B, 16 Oct 2026): story/o8b-calendar-horizon at 9232281d

**PASS.** Judge 240's should-fix is closed, and its note too. I took this over from judge D at the orchestrator's
request.

| Item | Result | Evidence |
|---|---|---|
| A crash before anything posts (an import error in `python -m fno`, a sender that cannot be built) gives one line | MET | `cmd_health` writes `posted=true` to `$GITHUB_OUTPUT` only when `alerts.send` returned `SENT`, its own FAILED line included. The alert step runs on `failure() && steps.check.outputs.posted != 'true'`, so an import crash never reaches `_record_posted` and the workflow's line speaks. Test: a sender whose build raises `ImportError` leaves no mark |
| A refused post or a dry run leaves no mark | MET | parametrised test (four cases) |
| Exactly one line per failure | MET | posted: the check's own line only; not posted: the workflow's only |
| The workflow header names the marker (judge 240 note) | MET | lines 4 and 15 |
| `GITHUB_OUTPUT` is not a credential | MET | `tests/live_credentials.py` `NOT_CREDENTIALS` |
| The rest of judge 240's criteria (horizon line, once, config, marker commit) | MET, unchanged | the diff around them is the same as 3e215fbb |

**My mutations (real cases):**
- `_record_posted()` replaced by `pass`: 2 tests fail.
- The alert step's `if:` put back on `steps.check.outcome != 'failure'`: 1 test fails (the test reads the workflow).

**Notes only (no should-fix):**
- If the check posted (`posted=true`) and then the commit step fails (a push race on a busy `main`), that day's run
  posts nothing about the commit, although the step name lists "a commit". The run record then never reaches `main`,
  so the next evening's check reports "health check did not run on <day>". It is caught one day later, not silent
  forever.
- `fno/constants.py` is now 349 lines, one under the limit. The next constant will need a split first.

**Gates (run by me on 9232281d):** `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto -p no:cacheprovider`:
7,089 passed. `ruff check`: clean. `ruff format --check`: 1,259 files already formatted. `check_imports`: clean.
