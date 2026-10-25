# Judge 253: G4 calendar label (story/g4-calendar-label at a9552c4e)

Judge B, 16 Oct 2026. Lane 1 (scoring and forecast records' reports). The owner's decision is in
`docs/DESK_DECISIONS.md` (16 Oct 2026, option A of response 241, no frozen-code change). Builder: R2/G7
(session 0185gR5D). The orchestrator asked me to check the labelling rule and that the FREEZE_v3 hashes are unchanged.

**Verdict: FAIL.** One should-fix: the report's line states a wrong fact about Book 1.

## Criteria

| Criterion | Result | Evidence |
|---|---|---|
| No frozen file touched; FREEZE_v3 hashes unchanged | MET | touched: `calendar_gaps.py` (new), `forecast_scoring/cli.py`, `score_report.py`, a test. None is in FREEZE_v2, v3 or v4's lists (grep); the freeze tests pass in the full suite |
| Reporting only, never rescored | MET | the field is added to the document after `score_forecasts`; no score input changes |
| Labelling rule matches the frozen cause | MET | frozen `ForecastHistory.horizon_day` asks `trading_days(day+1, day+45)` and returns None on `CalendarError` (`fno/forecast/history.py:86-92`). With the calendar ending 31 Dec, that is exactly "day + 45 crosses the year". Baseline A empty while the pack has no problems and an IV30 excludes other causes. Test: 16 Nov is not labelled, 17 Nov is |
| Days that don't match their receipt are left out | MET | test |
| Older reports without the field still read | MET | `document.get(...) or []`, test |
| Register row | MET | "G4 calendar label (O)" |
| **The weekly line is true** | **NOT MET** | see the should-fix |

## Should-fix: Book 1 used one baseline, not two

The summary line reads "Book 1's Q1 and Q2 averaged two baselines on N live days (baseline missing: calendar)". The
module docstring says the same ("Book 1 averages the other two baselines"). For Q1 and Q2, Book 1 is the mean of
exactly two baselines, risk-neutral and base rate (`fno/forecast/comparisons.py:46-50`; `book1_method.py`: "One
available: that one"). With the risk-neutral baseline missing, Book 1's Q1 and Q2 are **the base rate alone**.

Real records prove it (`research/forecasts/live_v2/2026/2026-10-15_forecasts.csv`, a day whose risk-neutral rows are
empty for another cause):
- `baseline_b_base_rate` Q1 = 0.5893333 and `book1_rules` Q1 = 0.5893333;
- `baseline_b_base_rate` Q2 = 0.352 and `book1_rules` Q2 = 0.352.

The owner reads this line to judge Book 1 on those days. "Averaged two baselines" hides that Book 1 had become
baseline B (a pure base rate) on Q1 and Q2. The fix is wording only. For example: "Book 1's Q1 and Q2 were the base
rate alone on N live days (baseline missing: calendar): ...". The test's expected line and the docstring should change
with it.

The same wrong sentence is in the owner's decision row in `docs/DESK_DECISIONS.md` (16 Oct 2026: "Book 1 averages the
other two baselines"). That is a lane-3 decision row, not this builder's file. I'm flagging it to the orchestrator.

## Notes only

- A labelled-window day whose pack also lists a problem (15 Oct's pack had three, "no ... observed by 15:00") is
  not labelled: its baseline A is empty for another cause too. That is defensible, but the count can be lower than the
  sessions in the window. One line in the report's wording ("days where the calendar was the only cause") would
  say so.
- The line says "Q1 and Q2" even when a day's `questions` lists only one. Both drop together under this cause, so
  this is harmless.

## Mutation (real case)

The year-crossing condition replaced by `True`: 1 test fails (16 Nov would be labelled). Caught.

## Gates (run by me on a9552c4e)

`env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto -p no:cacheprovider`: 6,967 passed. `ruff check`: clean.
`ruff format --check`: 1,237 files already formatted. `check_imports`: clean.

## Addendum 1: story/g4-calendar-label at c65daea4

**PASS.** The should-fix is closed.
- The weekly line now reads "Book 1's Q1 and Q2 were the base rate alone on N live days (baseline missing: calendar):
  ...".
- The docstring says the same, and adds the "only cause" note: a day with an input problem is not labelled, so the
  count can be below the window's sessions.
- A new test calls `book1_probabilities` itself: with baseline A it is the mean of A and the base rate; without A it
  equals the base rate. So the wording rests on the method, not on a reading.

I checked the builder's 14 Oct figure in the claim: 0.5560525 is the mean of 0.5214385 and 0.5906667. Response 241's
copy of the error is corrected on main (8a02f7b5). The diff since a9552c4e is the wording, the docstring and the test
only, so the rest of the verdict stands.

Gates (run by me on c65daea4): 6,968 passed (`-n auto`, Slack token unset). `ruff check`: clean. `ruff format --check`:
1,237 files already formatted. `check_imports`: clean.
