# Judge 408: A20c macro release calendar (story/a20c-macro-calendar @ d29bbbd5; code as at 08301ef4), for response 285

Judge F (independent). Story `docs/stories/A20-rules-and-dates.md` (text at 9ed3c071: A20c extends A6 through
`macro_events.py`, because `events.py` is frozen by experiment 1). d29bbbd5 only renumbers the claims to 285. Lane 1
(MOSPI, the Fed, BLS, Drive, Slack, a workflow). Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (2 should fix, 1 minor)

Gates on 08301ef4: **7410 passed** (with `pypdf==5.4.0` installed); ruff, ruff format (1331), `check_imports.py` and
the record scan (6628) are clean. `tests/macro_calendar`: 27 passed.

What is right:
- `events.py` and `events.csv` are untouched.
- Withdrawal counts only inside the new document's period: the builder's own blocking fix, and my plant removing it
  fails 2 tests.
- A date first seen on or after its day is dropped (plant: 1 failed).
- The 30-day stale bound is pinned (plant at 29: 1 failed).
- MOSPI's weekend rule keeps the planned date.
- FOMC dates are noted as US dates.
- BLS's refusal is real. The probe run 38900266338 log shows 403 for `cpi.htm`, `empsit.htm` and `bls.ics` with both
  user agents, while the Fed (200, 165,751 bytes) and MOSPI's API (200) answer the same runner.

## Should fix

**SF1. US CPI and payrolls fail every run by design, so the job is red every day and a real MOSPI or Fed failure is
buried in it [strong, code read].** `UnconfiguredCalendar.fetch` always raises, `MacroCalendarJob.run` turns any
problem into one alert and exit 1, and the workflow runs daily. So every day brings one "NOT complete" line, one O10
row and a failed run. The day MOSPI's PDF layout changes, the alert reads the same as yesterday's. The owner has since
approved FRED and a key exists (orchestrator, 16 Oct).

Fix expected: build the FRED adapter (St. Louis Fed release dates for CPI and the Employment Situation), with the key
as a secret through `env` and never printed. If that must wait, keep US CPI and payrolls out of the daily run until the
key is wired, and record the gap once (one alert and one O10 row per episode, A20b's pattern), not every day.

**SF2. The fallback alert step still has the old condition, so O10's watcher adds a duplicate line on every failed
run [strong: same as judges 358 and 359].** `macro-calendar.yml`:47 is
`if: ${{ failure() && steps.calendar.outputs.posted != 'true' }}`. When the job posts, this step is skipped, so O10
(on main since 54312c31) sees no alert step that ran and posts again. With SF1 that is two lines every day. Apply A20a
and A20b's fix (`if: ${{ failure() }}`, exit 0 when `POSTED == 'true'`) and its two tests.

## Minor

1. A date that a snapshot drops **on its own day** (`key[1] == seen`) is treated as standing, not withdrawn. Changing
   `>` to `>=` passes all 27 tests. Pin the boundary with a test, whichever reading is chosen, and say which in the
   docstring. Is a release dropped from the calendar on its day "held" or "withdrawn"?

## Merge notes (for later)

Add `macro-calendar` to capture-watch's list. Gate the exact merged tree, `check_numbers.py` included.
