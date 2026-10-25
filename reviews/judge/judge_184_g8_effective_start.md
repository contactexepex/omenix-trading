# Judge 184: G8 effective_start: `story/g8-effective-start` c645f662 (lane 1, scoring)

Judge B. A16/G8 builder. Source: the owner's row of 16 Oct 2026 (`docs/DESK_DECISIONS.md` line 213: "v4 misses count
from each slot's declared effective_start", which replaces "from the first live forecast"), ChatGPT review 119 and
judge 177 addendum 3. Four files change: `records.py`, `scoring.py` and two test files.

## Checks
- **The code matches the owner's row.**
  - `SlotRegistry.registered()` now returns `Registration(forecaster, effective_start)`.
  - After the freeze, `_miss_start = max(effective_start, freeze + 1 day)`. `miss_report` uses `start` in place of the
    first forecast (`first = start or ...`), so misses count from it even before a slot's first forecast.
  - Before the freeze, nothing changes (None: from the first forecast, exploratory).
  - `NoRegistrations` still returns `{}`, so live wiring is unchanged until the freeze's ledger adapter exists.
  - A registered slot that never forecasts now counts every baseline day missed, and so becomes "undecided,
    operations". Before, it showed 0 of 0. This is the intended stricter rule.
- **Tests.**
  - The old G9 test, which expected 0 misses for a late starter, is replaced, as the owner's change requires. It is not
    weakened: the same data now gives 3 misses of 8 observable days for a slot registered from the day after the
    freeze.
  - A later `effective_start` counts no misses before it.
- **My plants.** Each fails 1 test:
  - ignore `effective_start` (always freeze + 1): fails the later-start test;
  - drop the freeze floor (`effective_start` only): fails `test_after_the_freeze_misses_count_from_the_day_after_it...`,
    whose registration starts before the freeze.
- **Gates.** `tests/forecast_scoring_v4` + `tests/forecast_v4`: 211 passed. The builder's full suite shows 6,119 passed
  and 3 failed; those 3 are the known red tests on `main` (judge 177 addendum 4).

## Notes (not blocking)
1. The checklist's rule "effective_start before the slot's first eligible session" is not checked in code. Nothing
   reads registrations yet. G8's ledger adapter, built in the freeze commit, should refuse a registration whose
   `effective_start` is after its first eligible session. Check it at the freeze commit.
2. `fno/forecast_scoring/v4/` is byte-checked at the freeze, so merge this before the freeze commit, once `main` is
   green.

**Verdict: PASS for c645f662.**
