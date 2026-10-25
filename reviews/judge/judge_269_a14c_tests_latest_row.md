# Judge 269: A14c red-main test fix (story/a14c-tests-latest-row at 8016ec6a)

**Verdict: PASS. Lane 2 (tests only). Merge first: it turns main green.**

## What was wrong
Main has been red since df9bfaff. That commit was A14c's first live row: `2026-10-16,2.1,...`. Three C2d tests in
`tests/risk/test_manager.py` and `tests/risk/test_stress_factor.py` assumed the repository file's latest row was the
owner's seed (1.45). That was true only until A14c appended its first row. The code was right; the tests were wrong.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Only test files change | MET | `git diff origin/main...8016ec6a`: the 2 test files only |
| 2 | Age-rule tests no longer read the live file | MET | they use the `SEED_ONLY` fixture (1.45 seed in a tmp file) |
| 3 | The real-file test pins what stays stable | MET | the file starts with HEADER plus the seed row (append-only), and the seed is in force on 15 Oct |
| 4 | New test: C2 uses the real file's latest row strictly before the day | MET | `test_the_repository_s_file_is_read_by_its_own_rule` checks 15 Oct (gets the seed) and latest+1 (today gets 2.1) |
| 5 | Gates on the exact SHA plus a trial merge with origin/main df08e457 | MET | 7352 passed; ruff clean; check_imports clean; ruff format clean |

## Planted mutations (in `fno/risk/stress_factor.py`, all reverted)
| Mutation | Caught |
|---|---|
| Pick the earliest row instead of the latest (`[-1]` to `[0]`) | yes, 3 failed |
| Let a row dated on the day itself count (`<` to `<=`, so a replay sees same-day data) | yes, 2 failed |
| Remove the before-day filter entirely | yes, 6 failed |
| Age rule off (`max_age_days + 1000`) | yes, 4 failed |

## Note (not a should-fix)
The new test takes `before[-1]` in file order, so it assumes rows are appended in date order. A14c writes
`as_of` = run day, which only moves forward, so normal running cannot break this. A hand-written back-dated row
could, and the test would then fail loudly, not pass wrongly.

## Not judged here
A14c's per-family k (one global k = 2.1 also roughly halves lots for credit structures). That stays a queued owner
item.
