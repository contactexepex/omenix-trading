# Judge 435: the weather and v4 forecasts switch-on (story/g6-switch-on at 7f1c0f8d)

Judge B, 22 Oct 2026 (IST). Lane 1: config, the routine's schedule text, and scoring and record gates.
- Builder: R2/G7 (session_0185gR5DmoDh2zBAvgRU4CEB).
- Owner row: DESK_DECISIONS 280 (21 Oct, response 299: "Yes, switch on now", "No, don't wait"). It says: "the weather
  and the v4 forecasts switch on before the freeze (a judged config change) and the 14:33 routine moves to 14:05 IST
  now (the owner moves the scheduled task); forecasts made on or before Frozen on never count".
- Number claimed with `tools/claim_number.py`.

## Verdict: PASS (notes only); may merge before 14:05 IST on 22 Oct

## Criteria

| Claim | Result | Evidence |
|---|---|---|
| 1. `daily.live_from.weather` and `.forecasts_v4` = 2026-10-22 | MET | `config.yaml` as row 280 says; the header comment now says live rows on or before `Frozen on:` never count |
| Safe for scoring | MET | see "Why the scoring is unaffected" below |
| 2. CLAUDE.md and README: 14:33 -> 14:05 | MET | the scheduled task itself is untouched (the owner moves it), which is right under my hard lines too |
| 3. O11's strict xfail removed | MET | `test_the_daily_routine_starts_before_the_1430_forecast_cutoff` is now a real check; my plant (CLAUDE.md back to 14:33) fails it |
| 4. The live-dates test | MET | it now names weather and forecasts_v4 as 22 Oct; my plant (weather moved to 23 Oct) fails it |
| 5. The method-hash gates read back-fill rows only | MET, and right | see "The method-hash gates" below |
| The 14:05 start against every other step | MET (reasoning plus code) | see "The 14:05 start" below |

### Why the scoring is unaffected
- `scoring._counted` keeps only live rows of days after `Frozen on`.
- `_first_eligible` uses only live days after the freeze.
- G10's cohorts score live and close-proxy apart.
- So live rows from 22 Oct until the freeze can never enter a verdict. Before the freeze, reports are exploratory, as
  the protocol already says.

### The method-hash gates (claim 5)
- **Why the change is needed:** a live record is made once, on its own day, and never regenerated. Without this
  change, the first method-file change after 22 Oct would have failed the suite forever.
- **What still holds:** both gates still require a non-empty back-fill per file. Piece 4 is to add the check on
  counted rows (each live row after `Frozen on` carries the frozen hash).
- **My plants on 7f1c0f8d:**
  - a 2017 back-fill day file's hash changed: fails 1 test;
  - a 2026 day file relabelled live with another hash: passes, as intended.

### The 14:05 start
- **Weather and v4 forecasts** run first (`DAILY_RUN_STEPS`), at about 14:08 by the 21 Oct timing (about 2.5 minutes
  of setup), before the 14:30 refusal.
- **Inputs:** O6's closes for d-1 land the evening before. On main today, `warmup_closes.csv` ends 21 Oct (committed
  21 Oct, 18:48 UTC), and 20 Oct was a holiday (Dussehra, in A7's calendar).
- **The quote parts** keep their not-before of 14:38.
- **The desk** waits on its absolute timetable.
- **The desk and Book 1 do not depend on weather:** no import of weather in `fno/desk` or `fno/books`, and the card is
  not live.

## Gates (run by me on 7f1c0f8d)

| Gate | Result |
|---|---|
| `pytest -q -n auto` | 8,943 passed, 16 xfailed, no failures |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,658 files formatted |
| `check_imports` | clean |

## Notes (one line each)

1. **A late O6 close now ends the day "with problems".** If O6's close for d-1 is late, the weather step refuses ("the
   closes end at ..."). The run then ends "day done with problems: weather" (exit 1) and alerts #fno-desk. On 21 Oct
   O6's close was committed by hand, so this can happen in normal running. It is loud, and harmless before the freeze.
   Say so in the owner's note for 22 Oct.
2. **21 Oct is in neither M1's back-fill (it ends 19 Oct) nor its live records.** The exploratory reports have a
   one-day gap. No counted number is affected.
3. **The first real run against Drive is 22 Oct itself**, as the builder says. If the owner has not moved the task by
   then, both steps refuse at 14:33 and nothing is written.
4. **Merge before 14:05 IST**, with a pull and the full suite on the merged tree.
