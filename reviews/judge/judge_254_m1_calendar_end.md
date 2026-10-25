# Judge 254: M1 at the calendar's end (story/m1-calendar-end at a7a91d65)

Judge B, 16 Oct 2026. Lane 1 (a forecast record's fields and a screen). Claims: `reviews/claude/response_245_m1-calendar-end.md`
(builder 013xqaNTCbSBytKgqpfaYFqZ). The orchestrator asked me to check that the operative colour is unaffected, and
that adding the field to future records touches no frozen M1 or G file.

**Verdict: PASS.**

## Criteria

| Criterion | Result | Evidence |
|---|---|---|
| From 24 Dec, null events are shown as "not known yet", never as "no event" | MET | `weather_parts._events`: `events_next_5_sessions is None` gives one named driver; an empty list still gives none. Test on 28 Dec 2026 |
| v0's "not scored" now says why | MET | `ChecklistV0.unscored_reason`: inputs missing, or beyond the calendar (names the A7 fix). The record gets `v0_status` (`scored` or `not scored: <why>`) |
| The operative colour is unaffected | MET | the colour, probabilities and status lines in `day.py` are unchanged; the operative model is the VIX model (decision 71), which does not use the calendar. The change adds a key and a pure method only |
| No frozen M1 or G file touched | MET, with one point checked | `day.py` and `v0_live.py` are in M1's `METHOD_FILES` (`fno/weather/wiring.py:28`), so new records carry a new `method_sha256`. Nothing compares it across records (grep: only `fno/weather/` and `forecast_v4_rules` write their own). The v4 freeze has not been made: `PROTOCOL_v4.md` section 10 hashes the deciding files and writes the ledger row at the freeze, and only forecasts after the freeze count. So a change before it is allowed, not a new counted version. Neither file is in FREEZE_v2 or v3 |
| Back-fill records untouched; no reader needs the field | MET | records are written once; no reader validates the key set (grep of `weather_block`, `weather_history_block`, `weather_parts`, `learning/weather_section`, v4 records) |
| Register row | MET | one row for this change |

## Claims vs reality

All hold. "Nothing compares the method hash with old records": true by grep.

## Project rules

Files 132, 72 and 127 lines. The new strings are named module constants. Editing an existing test's key set is lane 1,
as here.

## Mutations (real cases)

- The unknown-events driver replaced by `return []` (the old "no event" behaviour): 1 test fails.
- `unscored_reason` always `None`: 1 test fails.

## Notes only

- `WeatherRecords.write` is write-once (any difference except `made_at` raises `RecordConflict`). A rerun of a day
  already captured before this merge, or a re-run back-fill over the 2,409 committed records, would now differ (the new
  key and method hash) and stop on `RecordConflict`, loudly. Neither is a normal daily path.
- Counting "unknown" events as `riskier` is a choice for the page only; it feeds no score.

## Gates (run by me on a7a91d65)

`env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto -p no:cacheprovider`: 7,071 passed. `ruff check`: clean.
`ruff format --check`: 1,257 files already formatted. `check_imports`: clean.
