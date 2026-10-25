# Judge 410: main-green, two date-dependent tests (story/main-green at 76f5d1f7)

**Verdict: PASS. Lane 1 (tests in lane-1 areas). The main steward may merge it: it turns main green.**

## Root causes, checked
1. **`test_g7_series.py::test_v1_reads_only_the_a16_rows_it_is_given`** hard-coded a 16 Oct A16 row and asserted
   "unresolved, because 16 Oct is not yet in the closes file". That file is real committed data and grows every day,
   so once 16 Oct's close landed the assertion broke. The test was wrong, not the code.
2. **`test_forecast_history_page.py::test_every_point_is_the_reports_own_scored_count_and_mean_brier`** built its
   expected points from every report file. The reader (`fno/market_read_models/forecast_history_inputs.py`
   `ScoreReportsReader.on`) takes only reports dated on or before the day, by design (point in time). The daily reports
   of 17-21 Oct made the two differ.

## Neither change loosens a test
| Test | Before | After |
|---|---|---|
| g7 series | one negative case on a fixed date | the negative case on a date a week after the file's last close, **plus a new positive case**: a row on the last close resolves exactly the session before it, with value 4e-05 |
| forecast history | expected built from all reports | expected built from exactly the rule the reader uses (`stem <= DAY`) |

**Planted mutation:** removing the reader's `<= day` filter makes 4 tests fail with the new expectation, so the page
test still bites on point-in-time reading.

## Gates (trial merge with main)
- Both files: 6 passed.
- Full suite: 8099 passed, 18 xfailed, **0 failed**.

## Note (not should-fix)
The second test now copies the reader's filter. If the reader's rule ever changes on purpose, both must change together.
That is acceptable, because the test's job is "the page shows exactly what the reader returns".
