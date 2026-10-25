# Judge 7: story A5, monthly-expiry identity in the package

**Verdict: FAIL.** Findings: 0 blocking, 1 should fix, 2 minor.

Judged `main` at 7846936 (story commit 20af389, 12 Oct 2026). Read in full: `fno/research_data/expiries.py`, the
pointer module `research/2026-10-12-capacity-screen/expiries.py`, `tests/research_data/test_expiries.py`,
`fno/quotes/recorder.py` (expiry part) and every caller of the three functions.

**No builder claims file for A5.** No `reviews/claude/response_*` names it. The claim is in
`conversations/2026-10-12.md:1510-1513`:

> rule moved ...; tests moved and a new test proves future listings never change an earlier day; **the quote recorder
> reuses the same rule (one definition)**. Re-running meeting 1, variants, max-loss, volatility-filter and
> capacity-screen scripts left every output byte-identical.

## Checks run by the judge

```
$ python -m pytest -q tests/research_data/test_expiries.py      4 passed (part of the full suite, which passes)
$ python research/2026-10-12-desk-meeting-1/desk.py        exit 0  (rewrote results.json at 23:14:02)
$ python research/2026-10-12-desk-meeting-1/variants.py    exit 0  (rewrote variants.json)
$ python research/2026-10-12-capacity-screen/screen.py     exit 0  (rewrote screen.csv, summary.md)
$ python research/2026-10-12-desk-meeting-1/max_loss.py    exit 0  (rewrote max_loss.json)
$ python research/2026-10-12-desk-meeting-1/vol_filter.py  exit 0  (rewrote vol_filter.json)
$ git status --short ; git diff --stat                     (no change to any output: byte-identical)
```

The re-run covered the three scripts the criterion names, plus `max_loss.py` and `vol_filter.py`. The output files'
timestamps show they really were rewritten, so the empty diff is not vacuous.

The quote recorder's expiry choice on a real holiday-moved month (Groww-style list seen on 2 Apr 2025):

```
fno.quotes.recorder.monthly_expiries([3 Apr, 9 Apr, 17 Apr, 24 Apr, 30 Apr, 29 May, 26 Jun 2025], 2 Apr 2025)
-> [2025-04-30, 2025-05-29]
```

That is the 30 Apr **weekly** in place of the 24 Apr monthly, which is exactly the case `monthly_as_of` exists to
avoid.

## Criteria

| # | Criterion | Builder's claim | Judge's own evidence | Result |
|---|---|---|---|---|
| 1 | Re-run meeting 1's `desk.py`, `variants.py` and the capacity screen; outputs byte-identical | "every output byte-identical" | My re-run above: all five scripts rewrote their outputs; `git diff` is empty | MET |
| 2 | Expiry tests pass from the new location, incl. 30 Apr 2025 and Sep 2025 | tests moved | `tests/research_data/test_expiries.py`: `test_a_holiday_moved_weekly_is_not_mistaken_for_the_monthly` (30 Apr 2025), `test_a_re_dated_monthly_keeps_only_its_new_date` (Sep 2025); pass | MET |
| 3 | Point-in-time: future listings added to the input change no earlier day | new test | `test_future_listings_never_change_an_earlier_day` adds two later days, including a re-listing; earlier days unchanged. The code (`expiries.py:29-39`) only accumulates days in order, so it holds by construction | MET |
| 4 | Outputs compared semantically and as bytes | (part of the byte-identical claim) | Equal bytes imply equal content; the scripts write a fixed column order (identical bytes after a fresh rewrite) | MET |

## Claims vs reality

- **"the quote recorder reuses the same rule (one definition)": false.**
  - The recorder imports `monthly_expiries`, the "last expiry of each month" rule (`recorder.py:20`, `:41-43`), not
    `monthly_as_of`.
  - The package's own docstring says "last expiry of the month" is "fooled by a weekly moved into the month for a
    holiday (30 Apr 2025)" (`expiries.py:30-31`), and my run above shows the recorder picking that weekly.
  - So research and the desk still use two definitions, against the story's goal ("research and the desk use one
    tested definition").
- **"byte-identical"**: true; reproduced.
- **"future listings never change an earlier day"**: true; test read and passing.

## Project rules and engineering standards

- Size: 39 lines.
- DRY: the rule has one copy, and the research module is now a pointer.
- Naming: there are two different "monthly_expiries" functions, `research_data.expiries.monthly_expiries` (last of
  month) and `quotes.recorder.monthly_expiries` (nearest two). The recorder imports the first under an alias. That
  is confusing, though not a rule breach (finding 3).
- No secrets.

## Findings

1. **Should fix: the desk's quote recorder chooses monthly contracts by a different rule, which fails on holiday-moved
   months.**
   - Evidence: on the 2 Apr 2025 list above, the recorder picks the 30 Apr weekly instead of the 24 Apr monthly. Its
     captured "monthly" quotes for that month would then be of the wrong contract.
   - This was not introduced by A5 (the recorder had the same rule before), but A5's claim says it was unified, and
     the story's goal is one definition.
   - Expected: the recorder uses the point-in-time rule (listed more than `MONTHLY_LISTING_DAYS` ahead on that day
     or before). It can keep the expiry lists it already records, or use the NSE daily files of earlier days. Add a
     test with the 30 Apr 2025 list.
   - If the story owner decides this belongs to A4 instead, the A5 claim must be corrected and a story named.
2. **Minor.** The rule rests on an observed constant: "weeklies are never listed more than 42 days ahead (2024-26)".
   If NSE ever lists weeklies further out, weeklies become "monthly". Expected: a data check (for example in A1 or
   the capacity fetch) that fails when any weekly is seen listed more than 50 days ahead.
3. **Minor.** Two public functions share the name `monthly_expiries` with different meanings. Expected: rename the
   recorder's, for example `nearest_monthly_contracts`.
