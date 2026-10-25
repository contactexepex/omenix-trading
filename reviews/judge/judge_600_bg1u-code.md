# Judge 600: BG1-u code "no monthly AI cap", story/bg1u-no-cap at 4d8b825bf (judge J, round 1 of 2)

**PASS**, lane 1, no findings. Diff vs main: `config.yaml` (+4), `fno/budget/{cap,constants,items,report,signal}.py`,
two test helpers, `tests/budget/test_no_cap.py` (new), the story. Gates on a trial merge with main d63700347
(ca2989ed6), `FNO_SLACK_BOT_TOKEN` set: 15,844 passed, 1 skipped, 15 xfailed. On main + BG1-u + G11 (eb49d77f0):
ruff, format, check_imports (2,692), check_records (9,160), check_numbers clean.

## Criteria
| C | Verdict | My evidence |
|---|---|---|
| 1 Switch | MET | `config.yaml` `budget.cap: none` lands in the same commit as the code (text m1). `from_config` raises a ValueError on a missing or unknown value (`cap.py`). My plants U1 (default share), U2 (default none) and U9 (config share) were caught |
| 2 Level | MET | `no_cap`, cap and pct None, minutes kept: the real meter shows 34.46 minutes. U3 (`unknown` on no_cap) and U4 (minutes zeroed) caught; U5 (none read as share) caught |
| 3 Nothing alerts or stops | MET | the real `budget signal --month 2026-10` wrote level `no_cap`, `stop_ai_roles` false, empty alert text, and printed "no alert: no AI cap (owner, 24 Oct 2026)". U7 (stop on no_cap) and U8 (send line) caught. The post-mortem test goes through `PostMortemRoutine` |
| 4 Meter | MET | the real output prints the reveal-wait line and "AI cap: none (owner, 24 Oct 2026: unlimited); books and roles 34.46 minutes this month". U6 (old lines) caught |
| 5 G11's stop | MET | on main + BG1-u + G11, `MeterBudgetStop(build_month_meter).check(24 Oct)` returned `BudgetCheck(stop='', note='')`: no stop, no fail-open alert. The ai, budget, learning and role_value tests pass: 542 |
| 6 Nothing deleted | MET | `share` still reaches alert and stop (test); the share settings stay in config, read and checked only under `share` |
| 7 Gates | MET | above; no file over 350 lines (suite's size test) |

**Test helpers not loosened:** `test_items_and_cap.py` and `test_meter.py` only add `cap: share` to the settings they
build; every assertion is unchanged (diff read). No other reader of `cap_minutes`, `pct_of_cap` or the level exists
(grep: report.py returns early on `no_cap`; signal.py's alert template is only for alert or stop).

## Plants
9 planted (U1-U9), 9 caught.

## Notes
- During the full run, #fno-desk got five "DRY RUN, 2026-10-23 replay" lines (15:49-15:52 UTC): cards and the candles
  and card steps. That is the same rehearsal pattern judge 586.1 and 586.2 traced to builders' dry runs.
  #fno-forecast and #fno-intraday got nothing. Orchestrator asked to confirm.
- `fno/ai/usage_gaps.py:3` (text m2) is G11/F8c's docstring and is unchanged here, as the gap list says.
