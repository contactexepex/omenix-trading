# Judge 581: G7b completion build step 1, `first_v4_expiry`, `story/g7b-completion` at e863dd1cc (round 1 of 2, judge K)

**PASS, lane 1.** The step can merge alone. 2 minor. Scope judged: `fno/forecast_v4_rules/v4_expiry.py`,
`tests/forecast_v4_rules/test_v4rules_v4_expiry.py`, and "Claims, build step 1" in `docs/stories/G-forecasts.md`. A
trial merge of e863dd1cc into origin/main (f5bc2d82e) changes only these 3 files.

## Criteria

| # | Criterion | Verdict | Own evidence |
|---|---|---|---|
| 1 | Protocol 1.4: the nearest listed expiry `e > d` with at least 5 scored sessions in `(d, e]` | MET | `v4_expiry.py:25-32`: sorted, deduplicated, `e > day`, the first with `>= HORIZON_SESSIONS[V4]` (= 5, `terms.py`); no fallback to a farther or nearer expiry |
| 2 | A7 regular sessions only | MET | `scored_sessions_until` uses `sessions.is_scored_session` (`session_kind == regular`); the plants "any session" and "weekdays only" are both caught |
| 3 | Window `(day, expiry]` | MET | `range(1, days + 1)`; the plants "count the day itself" and "exclude the expiry" are caught (5 and 6 failures) |
| 4 | Pure: no I/O, no clock | MET | imports only `constants`, `forecast_v4.sessions`, `forecast_v4.terms`, `research_data.calendar` (lines 9-15); no `now`, no file access |
| 5 | CalendarError, never a guess | MET | `day` is looked up first (line 28); `CsvSessionCalendar.session_kind` raises outside `first..last` (`calendar.py:99-100`). I reproduced: 22 Dec 2026 with Jan 2027 listed raises "2027-01-01 is outside the calendar" |
| 6 | Signature as G10 imports it (d4e72f20d) | MET | `first_v4_expiry(day, listed_expiries, calendar) -> date \| None`, as in G10 text line 1110 |
| 7 | Judge 578's criterion 20 cases (this step's part) | MET | 1-session Monday weekly skipped (3 Nov, 6 sessions); 5 taken, 4 not; 8 Nov 2026 muhurat and 20 Jan 2024 special not counted; none qualifies gives None; empty gives None. The pack cases (`no_v4_expiry`, mismatch) belong to the V4-terms step |
| 8 | Calendar facts in the tests | MET | `nse_sessions.csv`: 20 Oct, 10 Nov, 24 Nov and 25 Dec 2026 holidays; 8 Nov muhurat; 2024-01-20 special; 2024-01-22 holiday |
| 9 | Real output sample | MET | re-run on the merged tree: 26 Oct -> 3 Nov (6), 27 Oct -> 3 Nov (5), 28 Oct -> 9 Nov (8), 3 Nov -> 17 Nov (9). Identical |
| 10 | Size and standards | MET | 32 + 93 lines; constants not repeated; `ruff format --check` clean |
| 11 | Gates on the trial merge | MET | `pytest -n auto`: 15,192 passed, 1 skipped, 15 xfailed, exit 0; `ruff check` clean; `check_imports` clean (2,576 files); `check_records` clean; `check_numbers` clean |

## Plants

- **The builder's 6, re-run:** every one caught.
- **My 10, each against the test file:**
  - minimum 4: caught (3 failures)
  - count the day itself: caught (5)
  - exclude the expiry: caught (6)
  - fallback to the farthest expiry: caught (1)
  - any session counted: caught (3)
  - weekdays only: caught (3)
  - reversed order: caught (5)
  - day lookup removed: caught (1)
  - Monday expiries skipped: caught (1)
  - **survivor:** December bypass (`or expiry.month == 12`). It is contrived, but no test covers year-end (minor m1).

## Minor (not blocking)

1. **m1:** the claimed year-end behaviour has no test. On the committed calendar, 21 Dec 2026 takes 29 Dec and 22 Dec raises; I reproduced both by hand. A test for these two days would pin it and would catch the December survivor.
2. **m2:** this is the operations risk the builder already reported, with its owner named. The calendar ends 31 Dec 2026, so from 22 Dec 2026 every call raises until NSE's 2027 rows are added. G10's capture must turn that `CalendarError` into a recorded `v4_expiry: None` or a loud failure, never a silent skip. That is G10's handling, so it gets checked in G10's code round.

## Notes

- `e > day` against `e >= day`: the builder's equivalence holds. An expiry on or before `day` has 0 sessions in `(day, e]`.
- The file is not yet in `wiring.METHOD_FILES`. That is correct while no record uses it; it must join the method hash in the V4-terms step.
