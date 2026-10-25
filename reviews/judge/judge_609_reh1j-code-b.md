# Judge 609: REH1j code, a step not live in real runs is exercised (story/reh1j-not-live @ 2b902569d), judge B (2 of 2), round 1 of 2

**PASS (no findings). Lane 1** (rehearsal posts to #fno-desk; rehearsal writes). I did not read judge E's verdict. Code:
`fno/rehearsal/built_commands.py`, `exercised_line.py` and `exercised_parts.py` (new), `live_wiring.py`, `rehearse.py`,
plus `fno/cli.py` (`build_parser` split out of `main`), `daily/quote_steps.py` (`parts_result` split out), and one
line each in `daily/wiring.py`, `reason_codes.py` and `constants_operations.py`.

## Criteria (the orchestrator's three checks first)

| Check | Result | My evidence |
|---|---|---|
| A real run is unchanged | MET | the wrappers take their notes from `rehearsed_live`, which returns `live, {}` without a rehearsal mode (`live_wiring.py:24-27`). So `rehearsed_not_live` wraps nothing, and `rehearsed_quotes_done` returns the step itself (`exercised_parts.py:19-21`). `build_parser`/`main` and `parts_result` are pure extractions (diff read). Plants "real run gets notes" (1 failed) and "real run's quotes_done altered" (3 failed) are caught |
| A not-live step never counts as a failure | MET | `NotLiveInRealRuns.run` records the real day's `not_live` with the step's own result under `exercised` (`live_wiring.py:59-77`), so `problem_steps` and the last line follow the real day's rule. A not-live quote part is kept apart under `exercised_parts`, and only the live parts decide `quotes_done` (`parts_result`). Plants "exercised result counted as the step's own" (5) and "exercised part decides quotes_done" (1) are caught |
| A command not built is never run | MET | `is_built` walks fno's own parser (`built_commands.py`), never an error text. A missing child (`margins stress-broker-check`) and a bare group prefix are both not built. Plants "not-built command run anyway" (2) and "prefix read as built" (2) are caught |
| Writes stay under `dryrun/<run_id>` | MET | nothing new writes outside the rehearsal: the exercised steps run unchanged behind REH1's `rehearsed_drive` (unchanged); a not-built command is not run; `report_exercised` only reads the checkout's full log |
| Posts are labelled, #fno-desk only | MET | `report_exercised` posts through `build_alert_sender()`, which is `rehearsed_alerts(SlackChannelAlerts(token, FNO_DESK_CHANNEL_ID))` (`composition.py:162-165`), inside `in_this_process(mode)`. `test_exercised_line.py:52` goes through the real sender. Plants "line not posted" (3) and "parts left out" (4) are caught |
| A stop still stops | MET | `NotLiveInRealRuns` catches only around the built-check; an exception from the inner step (e.g. a commit failure) propagates as before |
| Gates | MET | trial merge into origin/main e06ec20fc (clean, 12d256fb6): ruff, format (2,576), imports (2,705), record scan (9,184), check_numbers clean; **16,170 passed, 1 skipped, 14 xfailed** (token kept) |

## Plants

8 planted, 8 caught (each named above).
