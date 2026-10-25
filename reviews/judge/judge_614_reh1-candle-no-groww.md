# Judge 614: REH1 follow-up "the candle source without the Groww SDK", story/reh1-candle-no-groww at 409b064ca (judge J, round 1 of 2)

**PASS**, lane 1 (Groww's composition root), no findings. Diff: `fno/intraday/backfill_wiring.py` (+5 -3),
`fno/rehearsal/candle_wiring.py` (+8 -4), `tests/rehearsal/test_routine_wiring.py` (+30 -2), the story note.
Gates on a trial merge with main 0cdfdfe97 (97621dd4a), `FNO_SLACK_BOT_TOKEN` set: 16,284 passed, 1 skipped, 14 xfailed.
ruff, format, check_imports (2,721), check_records (9,203) and check_numbers are clean.

## Checks (my own evidence)
| Check | Verdict | Evidence |
|---|---|---|
| Only caller | MET | `rehearsed_candle_source` is called only by `build_candle_backfill` (git grep), so no caller passes a built source to the new builder argument |
| A rehearsal never imports or builds the SDK | MET | A probe with `sys.modules["growwapi"] = None`, so any SDK import raises, under `FNO_REHEARSAL`: the branch builds `RecordedCandles`, while main 0cdfdfe97 raises "Install the Groww SDK first". The SDK import is inside `GrowwProvider.__init__` (`providers/groww.py:132`), and the module-level import of `fno.providers.groww` loads no SDK |
| A real run builds what it did before | MET | With a stand-in `growwapi` and a counting wrapper: one `GrowwProvider`, the source a `GrowwCandleSource` whose `api` is `ReadOnlyGroww` (the same read-only allow-list), built inside `build_candle_backfill` as before. Without the SDK a real run still refuses with the same error |
| Tests | MET | rehearsal: the builder fails the test if called; real run: exactly one provider built |

## Plants
5 planted, 5 caught:
- the rehearsal calls the builder first;
- a real run returns the builder uncalled;
- the provider built eagerly again;
- a real run builds twice;
- the read-only wrapper dropped.

## Notes
- One #fno-desk post in the run's window (17:33:36 UTC): a "DRY RUN, 2026-10-23 replay" taiex line, the same
  rehearsal pattern as judges 586.1 and 600. #fno-forecast and #fno-intraday got nothing. Orchestrator asked to
  confirm.
