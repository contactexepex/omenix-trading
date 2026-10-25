# Judge 268: G7's V7 rule voids across a missing VIX close (story/g7b-vix-gaps at 19e681a5)

Judge B, 16 Oct 2026. Lane 1 (forecast records and scoring), before the v4 freeze. Builder: R2/G7 (session 0185gR5D),
acting on judge 267's note.

**Verdict: PASS**, with one merge condition, and main is red for an unrelated reason (below).

| Item | Result | Evidence |
|---|---|---|
| `t+horizon` counts regular sessions, not VIX rows | MET | `vix_up_outcomes(vix, horizon, sessions)` zips the session list with itself shifted; a day whose own or end VIX close is missing has no outcome |
| A 20-session side window holding a gap has no side | MET | `VixSideRate._below` returns None when the window has a missing value |
| The capture passes the regular sessions | MET | `DayForecasts.days = [c.day for c in inputs.closes]` |
| Back-fill unchanged except the method hash | MET, checked | all 14 regenerated CSVs: same 2,410 rows, and `method_sha256` is the only column that differs from the merge base (my script over every row) |
| Planted-gap test | MET | session 10 missing: days 5 and 10 void, day 4 still resolves at session 9, and the windows holding session 10 have no side |
| Freeze | OK | `fno/forecast_v4_rules/` is byte-checked only from the v4 freeze, not made yet |

## Merge condition

G8's adapter (story/g8-v7-shared-rule, judge 267 PASS) calls `series.vix_up_outcomes(vix, horizon)` with two
arguments. That branch merges first. This branch must then pass `sessions` from G8's `G7Series` (one argument) in the
same merge, or the merged tree fails. The full suite on the merged tree is the check.

## Mutations (real cases, all caught)

- The old shifting `zip(vix, vix[horizon:])` restored: 2 tests fail.
- A gap no longer voiding the side window: 2 tests fail.

## Main is red, not because of this branch

The full suite on 19e681a5 gives 7,318 passed and **3 failed**, and the same 3 fail on `origin/main` (d0192068):
- `tests/risk/test_manager.py`: `..._through_its_30th_day[day1]` and `..._from_the_31st_day_...`;
- `tests/risk/test_stress_factor.py::test_the_repository_seed_row_is_read_by_c2_and_c4`.

The cause is A14c's first full run, `df9bfaff` "A14c Actions: stress factor 2026-10-16", which appended a row with
**factor 2.1** (from the owner's seed of 1.45; "PDS 300 entered 2020-04-08 peak 2020-05-04 needed 2.0817"). These
tests pin the seed row. Two points for the orchestrator:
1. Main has failed these three tests since df9bfaff. The tests should read the file's latest applicable row, not
   assert 1.45.
2. More important for money: C2 and C4 now stress margins by 2.1 instead of 1.45 (about 45% more stressed margin),
   so more trades will be refused at entry. That is the measured result A14c was built to give, but the owner should
   hear it as a desk fact, not discover it from refusals.

`ruff check`: clean. `ruff format --check`: 1,308 files already formatted. `check_imports`: clean.
