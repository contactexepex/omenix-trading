# Judge 469: O1-desk-freeze story text (story/o1-desk-freeze at e76e9bc9)

**Verdict: PASS (text). Lane 1. Round 1 of 2.** One condition before the code is judged:
- the owner's answer to the open-position question (design 3) is recorded in `docs/DESK_DECISIONS.md`;
- the code is judged against that answer.

Two notes, not blocking. Merge timing as the story says: after Monday 26 Oct's run, never 14:00-16:15 IST.

## Findings, with evidence
| Claim | Result | Evidence |
|---|---|---|
| Matches the owner's cut-list item 2 | MET | DESK_DECISIONS line 294: freeze the paper desk's daily steps from Mon 26 Oct; risk and data checks unchanged |
| Skipping frozen steps would lose the day's quotes, so a frozen step must keep its wait | CONFIRMED (strong evidence) | `DailyRun.run` waits only on steps whose plan has a time (`_plan`: only the desk steps carry one). `quotes_done` (`quote_steps.py:58`) calls `parts.finish(wait)` with no `not_before`, so its limit is `now + FINISH_LIMIT` (20 min, `quote_parts.py:166`). Run at about 14:10, it ends near 14:30, before `EARLIEST_START` 14:38, and each part is "never started". Only the runner's stop path (`runner.py:69`) waits until `fills_by` |
| The block readers break on a frozen log unless changed | CONFIRMED | `_unreviewed` iterates `log.result("exits").items()` as book entries; a `{status, reason}` result would be read as books |
| Health and scoreboard B need the frozen rule | CONFIRMED | `RunLogCheck` judges the `decisions` finish time against the deadline. A frozen step recorded at 15:12 could read "late". `CommittedRuns.missed_runs` would count Book 1 as missed |
| `frozen` and `desk:FROZEN` survive O1-status-only's public log | MET | both match the identifier pattern in `public_log.VOCABULARY`; the story still adds the code to the registry, as the rule requires |
| `desk` is an allowed config key holding `timetable` | MET | `config.yaml` `desk.timetable`; `frozen` sits beside it |
| One switch; a planted freeze of a non-desk step is refused | MET (as a criterion) | acceptance 7 |

## Notes (not blocking)
1. **One more later reader: the card's "last session" line.** `cards/rule_checks.py` `ExecutionOutcome._last` reads
   the previous session's `snapshot` result. On a restart day with no snapshot yet, it would print "no valid execution
   snapshot (desk:FROZEN ...)". Cosmetic, but add it to design 4's list so the code treats it like the others ("last
   session: desk frozen").
   I checked the other run-log readers, and a frozen day breaks none of them:
   - `books/opening_runs.py`: only days with fills, and a frozen day has none;
   - `daily/reviews.py`: frozen itself;
   - `role_value/*`: does not read run steps.
2. **The open-position default.** Until the owner answers, the text should say which way the code goes. My reasoning
   only: the exception matches "risk checks unchanged", and no trade is open today, so either answer freezes the whole
   desk in practice.

## What the code round must show (from the acceptance, no new scope)
- The e2e frozen day keeps the twin's quote tree, and `quotes_done` runs after 15:15.
- The restart day does not block `fills`.
- Health and scoreboard B show the day as frozen.
- No alert, and the day ends "day done".
- An absent or false switch leaves the suite untouched.

## Addendum 1

**O1-desk-freeze code (story/o1-desk-freeze at f7ad40e0): PASS. Lane 1, round 1 of 2.** Merge only after Mon 26
Oct's run, never 14:00-16:15 IST. `desk.frozen` stays false; setting it to true is its own judged commit.

| Criterion | Result | Evidence |
|---|---|---|
| 1. Frozen day keeps the timetable and quotes; no desk child or private write | MET | `DailyRun.run` keeps every wait and swaps only the action (`_frozen`). The e2e twin test compares `started_at` and the quote tree. P1 (a frozen step skips its wait) is caught |
| 2. Non-desk steps unchanged | MET | e2e `test_every_step_outside_the_desk_has_the_twin_s_result`; `DESK_FROZEN_STEPS` is the desk plus book1, owner_timing, reviews and card. P5 (quotes_done added to the set) is caught |
| 3. No alert; "day done" | MET | `frozen` is not in the runner's PROBLEMS; the e2e and unit tests check that no alert is sent |
| 4. Restart day blocks nothing | MET | `_unreviewed` returns early on a frozen exits step; `_unscored` passes `frozen`. P2 (guard removed) is caught: a crash on the restart day |
| 5. Health and scoreboard B read frozen | MET | `RunLogCheck` gives NOT_EXPECTED, or MISSED when another step failed; `missed_runs` counts a frozen decisions step as collected and still counts a missed exit review while a trade was held. P6 and P7 are caught |
| 6. Open-position exception (owner, option A) | MET, extended | `DeskFreeze` keeps `OPEN_POSITION_STEPS` while `open_trades` > 0 (shadow accounts included). Exits fill inside the exit review (`daily_steps.py` 196-218), so a frozen `fills` never stops a close. P4 and P8 are caught; P3 (snapshot dropped) is caught by the open-trade test |
| 7. The switch is the only control | MET | absent switch means false, and a non-bool is refused; the existing suite is untouched. P10 (absent counts as frozen) is caught |
| Judge 469 note 1 (the card's last-session line) | MET | `_verdict` gives "desk frozen by the owner"; P9 is caught |

**Gates** on a trial merge with main (3c6a95bb, removed):
- 9,843 passed, 16 xfailed;
- ruff check clean, format clean;
- check_imports clean, check_records clean (7,872 files), check_numbers clean.

**Plants:** 10 planted, 10 caught.

**Notes (not blocking)**
1. **Beyond the owner's literal answer:** the open-position set also keeps `pack` and `snapshot` (strong evidence:
   the exits' data gate needs the capture and spot) and `reviews` (reasoning only: E6's loss rules on a held trade). All
   three are more protective, consistent with "risk checks unchanged", and named in the story so they can be refused.
   The orchestrator should put `reviews` to the owner in one line; dropping it means removing one name from
   `OPEN_POSITION_STEPS`.
2. The open-trade count is read once, at the run's start, after the private files are downloaded. A trade cannot open
   during a frozen run (`fills` is frozen), so one read is enough.
