# Judge 262: E2d code, per-trade daily marks (story/e2d-code at b8e1970a)

Judge B, 16 Oct 2026. Lane 1 (paper accounts, the daily run, the record scan). Claims:
`reviews/claude/response_246_e2d-trade-marks.md` addendum 3. Text: E2d in `docs/stories/E-paper-desk.md` (judge 250
addendum 2 PASS, merged 8908ba3c).

**Verdict: PASS.**

## Criteria

| # | Result | Evidence |
|---|---|---|
| 1 Same as S2 every session, a lost marking day included | MET | `mark_trade` calls S2's `trade_days` unchanged over the entry day to today, with `SnapshotMarks` built from the committed run logs' valid snapshot ids, and takes the last day. Nothing reads `trade_marks.csv` back. Test with a lost day 2 |
| 2 Equity row = closed + the open trades' values | MET | `record_marked_equity(day, open_trades_value, stale)`: marked = `closed_equity_rs + open_trades_value`; my note is applied (the name, the docstring, and a test that it is not closed plus the legs alone) |
| 3 Unmarked: no equity row, one alert | MET | `TradeMarker.mark` skips the equity row; `MarkingStep` sends one alert per unmarked trade |
| 4 Only the recorded valid snapshot | MET | `CommittedRuns.snapshot_ids()`, read when the step runs (today's snapshot step is in the log by then) |
| 5 Idempotent; a same-day top-up row is replaced | MET | `write_trade_marks` replaces the session's rows; `_replace_equity_row` is by date |
| 6 Account files refused by path | MET | `ForbiddenFolders` (`journal/*/account/`, `journal/shadow/*/account/`, `*` = one folder name), wired in `build_record_scanner` |
| 7 `daily_totals.csv` unchanged | MET | the step commits nothing (see deviation 1) |
| 8 No open trade: equity row, no trade rows | MET | `record_marked_equity(day, 0, [])`; no file created for an account that never had an open trade at a marking |
| 9 One account's failure never stops another | MET | per-account `try`, alerted |
| 10 Shadows in their own files | MET | `marked_accounts`: the books plus started shadow accounts |
| 11 `awaiting_settlement` is a label on S2's stale value | MET | `past_expiry` changes only the status |
| 12 S1-hashed and S2 files unchanged | MET | my check: `git diff origin/main...b8e1970a -- fno/scoreboard fno/books/equity.py fno/scorecard fno/desk/pricing.py fno/desk/snapshot.py` is empty, and no changed path is named in `research/evaluation/PROTOCOL.md` (script) |

## Rulings on the two changes from the text

1. **No `AccountSync.write` for marking: ACCEPT.** `DriveAccountSync.write` commits `write_daily_totals(root, book)`
   (`fno/desk/drive_sync.py:30`), which would publish a new public file per shadow account. The step opens the same
   locked, Drive-pulled and Drive-pushed journal and commits nothing. `PrivateFiles.push` replaces the Drive copy, so a
   rewritten `trade_marks.csv` is not refused.
2. **The step is named `trade_marks`: ACCEPT.** It avoids confusion with A16's marks in O8. O8's owner agreed in
   writing, with one condition I record here: the desk's `live_from` must be on or after this merge, or older run logs
   read as missed.

## Other owners' files

- O8's `DESK_RUN_STEPS` gains `trade_marks`, and its owner agreed.
- E3's run tests change expectations only: the new last step, the rejected-push tests on that step, and the Drive
  fixture.

I found no check removed or weakened.

## Mutations (real cases, all caught)

- Marked equity off by Rs 1: 3 tests fail.
- The shadow-account pattern dropped: 2 tests fail.
- One account's failure re-raised instead of continuing: 1 test fails.
- Marking with today's session only (no snapshot history): 3 tests fail.

## Notes only

- A Drive failure during marking is alerted per account, and the run goes on. That day has no equity row, and the next
  marking writes the rows again. S2 is unaffected. This was disclosed by the builder.
- The step's run-log result (public) lists trade ids and statuses only, no values. Trade ids are already in the
  fills and exits results.
- `TradeMark.row` uses a lambda with `noqa: E731`; a small helper function would read better. Style only.

## Gates (run by me on b8e1970a)

`env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto -p no:cacheprovider`: 7,167 passed. `ruff check`: clean.
`ruff format --check`: 1,274 files already formatted. `check_imports`: clean.
