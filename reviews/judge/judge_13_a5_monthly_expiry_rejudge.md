# Judge 13: story A5 re-judged (round 2)

**Verdict: PASS.** Judge 7's should-fix finding is fixed, and I verified the fix against real NSE files. Judge 7's two
minor findings stay open by the orchestrator's decision, and I accept that, with the reasons below. Two new minor
findings, neither blocking.

**What I judged:** trading `main` after 42d9a6b, with fix commits 90d3d53 and 42d9a6b. The claims are in the section
"A5 judge-7 fix" of `reviews/claude/response_39_2026-10-13-a7-session-calendar.md`. I read in full
`fno/quotes/monthly_contracts.py` and `fno/quotes/expiry_listing.py`, plus the diff of `recorder.py`, `cli.py` and
`composition.py` since 4d99d83.

## Checks run by the judge

```
$ git diff --quiet e1fd4e1^ HEAD -- tests/quotes/test_recorder_baseline.py tests/quotes/test_quote_recorder.py tests/fixtures
A4 tests+fixtures unchanged
$ python -m pytest -q                 440 passed
$ python -m pytest -q tests/quotes    40 passed
```

**Real-data run.** I used the real NSE files from the shared Drive, read through the app's own library, with no
fakes. For each day I took the expiry list as it stood on that day and asked `PointInTimeMonthlies`:

```
2025-04-02 listed near: 03 Apr, 09 Apr, 17 Apr, 24 Apr, 30 Apr, 29 May
  monthly: 2025-04-24, 2025-05-29, 2025-06-26   files: 11 Feb, 17 Feb, 25 Feb, 4 Mar, 10 Mar 2025   10.9 s (Google Drive)
2025-04-03 same answer, 7.5 s
```

The 30 Apr 2025 holiday-moved weekly is no longer taken for the April monthly. Before the fix, the recorder returned
[30 Apr, 29 May] (judge 7).

## Does the "verified" path prove monthly-ness, or only assert it?

It proves it, with one stated assumption.

- **Expiries more than 50 days ahead.** These count as monthly from today's list alone. That rests on the assumption
  that weeklies are never listed more than 42 days ahead.
- **Expiries 50 days or fewer ahead.** For such an expiry *e*, the code reads NSE's actual file of the latest day on or
  before *e* − 51 (`monthly_contracts.py:31`, `expiry_listing.py:49-62`, with a 7-day lookback).
  - If *e* is listed there, its days-to-expiry in that file is at least 51. `monthly_as_of` then marks it monthly from
    real listing data, not from the date's position in the month.
  - If *e* is not listed there, it was never listed more than 50 days ahead, because a contract stays listed until it
    expires. So it is not monthly.
- **Record of proof.** Each file used is saved in `meta.json` → `monthly_check.files` with its date and SHA-256, so the
  proof can be re-checked later.
- **Missing files.** If no file exists in the lookback, the code raises and takes the flagged fallback below. It never
  guesses silently.

The one assumption is the 42-day weekly horizon, which judge 7's minor finding 2 covers. That finding stays open (see
below).

## Judge 7's findings: decisions

| # | Finding | Builder's answer | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | Should fix: the recorder used the last-of-month rule (it picked the 30 Apr 2025 weekly) | `PointInTimeMonthlies` calls A5's `monthly_as_of`. The app injects `history`, and meta records the proving files. | Real-data run above. Code read. 9 new tests pass. | ACCEPTED |
| 2 | Minor: no data check of the "weeklies ≤ 42 days ahead" assumption | Left open by the orchestrator's decision | Acceptable as minor: the rule has held 2024-26 (A5 note). Because the proving files are now recorded, any later check can be run over them. It remains the single assumption the verified path rests on. | Accepted as still open (minor) |
| 3 | Minor: two functions named `monthly_expiries` | Not renamed: the unchanged A4 test imports `fno.quotes.recorder.monthly_expiries`, and A7 criterion 4 forbids changing that test | The constraint is real. The docstring now says the function serves only the no-history (A4 test) mode. Under the owner's clean-code standard this name clash is a defect, but it is held in place by another criterion. Expected: rename when the A4 tests may change (see judge 12 finding 2). | Accepted as still open (minor) |

## The fallback decision (42d9a6b): judged

When the history cannot be read, the recorder:
- falls back to the last-listed rule;
- keeps the quotes;
- writes `monthly_check = {"status": "unverified", "rule", "reason"}`;
- sends an alert.

**This is right (reasoning only).** Quotes cannot be recorded after the day, while a flagged contract choice can be
checked later from the saved meta. The alternative, failing the day, loses data that can never be recovered.

**Two notes:**
- On a holiday-moved month, the fallback records the weekly as "monthly". The flag and the alert make that visible,
  and later research must exclude unverified days or re-check them.
- `except Exception` (`recorder.py`, `_nearest_monthlies`) also turns a programming bug into "unverified". It is still
  alerted, so this is acceptable, though narrower exceptions would be cleaner (new finding 1).

## Live-run risk for 13 Oct 2026 (09:18 UTC trigger, 14:55 IST window)

- **First-attempt reads.** The first attempt reads about 6 NSE files: 7.5-11 s from Drive in my run, and 15.8 s in the
  builder's dry run. That fits easily inside the 14:55-15:10 window. Files are cached across retries.
- **Nothing is written to the repository.** The library has no archive folder in this wiring (`build_nse_library`
  with no project folder), so no NSE files are added to commits.
- **Drive needs its key.** Drive works only with the Drive key in the routine's environment. Without it, NSE is asked
  directly. If both fail, the quotes are still recorded with the flagged fallback and an alert.
- **Separate from A5:** judge 12 noted that a missing Groww login already causes an alert and exit 1.
- **Contracts for 13 Oct.** The builder reports that the real-history dry run for 13 Oct gives [27 Oct, 23 Nov]. I did
  not rerun 2026 dates; my run covered the April 2025 case.

## Criteria (A5, re-judged)

| # | Criterion | Result |
|---|---|---|
| 1 | Re-runs byte-identical | MET (judge 7; research scripts unaffected by this fix) |
| 2 | Tests from the new location, incl. 30 Apr 2025 and Sep 2025 | MET |
| 3 | Point-in-time | MET |
| 4 | Semantic and byte comparison | MET |
| Story goal | Research and desk use one tested definition | Now met: the recorder calls `monthly_as_of` |

## Engineering standards

- `monthly_contracts.py` is 39 lines: one class, one job.
- The new `ExpiryHistory` interface is implemented by the existing reader through a shared `_latest`, so nothing is
  duplicated.
- `recorder.py` stays under 350 lines.
- The name clash is covered above.

## New findings (minor)

1. **Minor.** `_nearest_monthlies` catches `Exception`. Expected: catch the history's own failures
   (`ExpiryListUnavailable`, network and file errors) and let programming errors fail the attempt.
2. **Minor.** If the first expiry list (from the provider) gets "unverified" but the late-December fallback list then
   verifies, the meta stays "unverified". That errs on the safe side but is misleading. Expected: the status should
   describe the list that was actually used.
