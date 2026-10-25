# Judge 170: story O8, the daily health check (code; judge F)

**Commit judged:** `83cb35d0b4718f3790b663a0a21ad53527b6fdba` on `story/o8-health-check` (claims: response 153,
addendum 2), checked against the text that passed judge 164 addendum 1 (`c5bbfbd2`). Builder:
session_012eM7Ti8ZaSVowgyMkgoGmM. Lane 1 (new workflow and schedule, Slack, GitHub).

**Verdict: PASS.** Nothing blocking and no should-fix finding. There are 3 minor findings, and 1 deviation, which I
accept on the data. Merge after the orchestrator's trial merge. The only conflict is the index row in
`reviews/claude/README.md`.

## Gates (run by me at the commit)
- `pytest`: 5,989 passed.
- `ruff check`, `ruff format --check` and `tools/check_imports.py` are clean.
- No new file is over 350 lines: the largest is 177, a test file; the largest in `fno/health/` is 80.
- `fno/constants.py` is at 343 lines.
- Trial merge onto `origin/main` at 1044a520: the code merges clean. The one conflict is the claude README index row.

## Lane 1: schedule, token scope, what the job commits (strong evidence: the workflow, read line by line)
- **Schedule:** cron `21 12 * * *` is 17:51 IST, plus `workflow_dispatch`, with `concurrency` set so runs never
  overlap and a 15-minute timeout.
- **Token scope:**
  - The workflow grants `permissions: contents: write` only, the same as `forecast-capture.yml:31`.
  - The run's `github.token` reads GitHub's activity log with that scope: the 15 Oct audit file records
    `commitment_received_at` 09:45:12Z, read by F1 from Actions.
  - `FNO_SLACK_BOT_TOKEN` and `GITHUB_TOKEN` are set on the check step only.
  - Nothing prints a token: receipt errors carry only the HTTP status.
- **What the job commits:**
  - It runs `git add research/ops/health_runs.csv` only (not `-A`) and commits only when that file changed.
  - The commit runs through the O5 hook (`core.hooksPath .githooks`) and does `pull --no-rebase` before the push.
  - The commit step runs `if: always()`, so a failed run's row is still committed.
  - A push by the Actions token starts no other workflow.

## Criteria

| # | Builder's claim | Judge's evidence | Result |
|---|---|---|---|
| 1 | The window is defined once; session D is checked from D to D+6; muhurat and `live_from` handled | `window.py` uses `calendar.sessions(run_day - 6, run_day)`. Planted M5 (window one day short): caught | MET |
| 2 | Each status from its evidence | Planted M1 (deadline exclusive), M2 (`none` accepted), M7 (unknown made ok), M11 (row key without its comma), M12 (a not-fired book accepted) and M13 (panel status ignored): all caught. For my M8 (absent exactly at the deadline counted `not due`), see minor 3 | MET |
| 3 | Deadlines from their owners | `LATEST_START`, `GENERATION_DEADLINE`, `receipt_deadline`/`reveal_deadline` and `timetable.decision_deadline` are imported (`expectations.py`, `forecast_checks.py`). The only `time(` literals are the four health-owned constants. The count is `(FORECASTERS − AI_BOOKS) × questions`. Planted M14 (FLOWS_BY back to 23:59): caught | MET |
| 4 | Push times only from GitHub | `Evidence._received` calls F1's `PushReceipts`; the commit is found by `--diff-filter=A` or the pickaxe. A commit date is used only as git's `--since` search bound, never for timing | MET |
| 5 | One message | `report.py` gives one line per check, with sessions grouped by status and reason. Planted M15 (a Slack refusal exits 0): caught | MET |
| 6 | Watcher watched | `run_record.py`: missing days only inside the window and after the first row. Planted M10 (first row ignored): caught | MET |
| 7 | Workflow | See above. Planted M16 (`contents: read`): caught | MET |
| 8 | Real sample | Reproduced exactly: `--dry-run --at 2026-10-15T23:30:00` with no tokens gives the same 9 lines. See "What the first real run will say" | MET |
| 9 | Engineering rules | Every check sits behind `SessionCheck`, wired only in `fno/health/wiring.py` (added to the CLAUDE.md list); constants and config keys are in place | MET |

My plants: 13. Caught: 11. The two not caught are minors 2 and 3.

## The deviation: `FLOWS_BY` is 12:00 the next day, not 23:59. Accepted (some evidence: two sessions)
I re-ran `git log -S "<date>," --reverse` on the manifests (commit time in IST):
- FII/DII flows: the 13 Oct row was added 14 Oct 09:37 (the market publish); the 14 Oct row was added 15 Oct 01:11.
- With 23:59, both days would be `late` in normal running, from GitHub's measured lateness alone.
- 12:00 the next day matches the closes and is met on both days.
- Participant OI (21:50, 21:28, 21:14) and the closes (22:59; 01:11 the next day) meet their deadlines, as claimed.

## What the first real run will say (my simulation; reasoning on real data)
I replaced the push receipt with each commit's own committer time (a stand-in, since there is no token here) and ran
the real repository at 15 Oct 23:30. The output is 4 problems:
- NSE `missed (none)` on 14 and 15 Oct;
- forecast v2 late on 14 Oct (19:27:39);
- **Book 2 and Book 3 commitments late on 15 Oct: pushed 15:15:10, due 15:15.**

The last is a real finding the desk should see. It agrees with the AI audit file: GitHub received the commitment at
15:15:12 IST, and all five answers are `counted: null`. The Groww canonicals and the evening jobs are `ok`.

## Minor
1. **The O1/O8 run-step contract is not written down on this branch.** O8 keeps the step names as a local copy,
   `DESK_RUN_STEPS` in `fno/health/desk_checks.py`, kept equal to `fno/desk/daily_run.py` by a test that parses that
   file's source. This is consistent with the agreed rule if O8 merges first: one `DAILY_RUN_STEPS` in
   `fno/constants.py`, made by whichever merges second. But neither the story, response 153 nor the work register
   says so. Add one line, for example in O1's register row: "O1 moves `DESK_RUN_STEPS` to
   `constants.DAILY_RUN_STEPS`, O8 imports it, and the source-parsing test goes." Constants has room: 343 lines.
2. **No test pins which rows are live.** My M17 set the Groww recorder's `live_from` to `None` (silent), and all
   tests still passed. One assertion on the set of live check names would catch a silently dropped check.
3. **No boundary test for an absent file at its deadline.** At exactly the deadline, `absent()` says `missed`; my M8
   made it `not due` and nothing failed. The deadline is a one-second instant, so this is a note-level gap: the late
   and ok boundary is tested.

## Claims vs reality
- "31 of 31 breaks caught": I did not re-run the builder's script. My own 13 plants: 11 caught, 2 gaps (minors 2-3).
- "Tokens to the check step only": true.
- "Commits only the run record": true.
- "Real sample": reproduced byte for byte.
- "Review agent findings 1-5 fixed": failed-run row (`cli.py`), Slack exit code (M15 caught), `--at` read as IST
  (`ist_time`), malformed evidence as `unknown` (`checker.MALFORMED`), distinct forecast pairs (`forecast_checks.py`).
  Each is present in the code.
- Known limits (push race, 2027 calendar rows, receipts verifiable only in Actions): stated in the story, acceptable
  under the simplicity rule.

## Project rules
- One builder: work-register row NF step 6 is this builder's. There is no other health checker in `fno/`.
- Simplicity rule: one job, one message; nothing re-runs or fixes another job.
- Secrets: none in any file or log.
- Records: no frozen file is touched. The only new data path is the job's own lane-3 output.
