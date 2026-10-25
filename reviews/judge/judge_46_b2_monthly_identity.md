# Judge 46: the monthly-identity fix (weeklies taken as monthly), B2 / A5

**Verdict: PASS.** The fix is at the root and reproduced.
- **Monthly identity:** a monthly expiry is now one with a NIFTY future listed that day.
- **Cycles:** 60 in 2019-2023, not 216. 33 in 2024-26, with discovery byte-identical.
- **The access claim holds,** with one disclosed exception that is harmless.
- **Before the freeze:** experiment 1's `PROTOCOL.md` must name the futures rule. The builder flagged this. It is a
  freeze prerequisite, not a defect of this fix.

**What I judged**
- **Repository:** trading `main` at e53b3ff (fix d2949b8).
- **Claims:** `reviews/claude/response_45_2026-10-13-b2-cycle-simulator.md`, section 8.

## Checks run by the judge

```
$ python -m pytest -q                                   1215 passed
$ ruff check fno tests tools; python tools/check_imports.py      clean (260 files)
$ pytest test_cycles_eras.py test_cycles.py test_cycles_real.py  14 passed
```

### Counts: futures files only, read by my own script (date and expiry columns)

| Check | Result |
|---|---|
| Sessions 2019-2026 with exactly 3 NIFTY futures | **1,928 of 1,928** |
| Distinct future expiries per year | 12 each year, except 2023 and 2025 with 13 (below) |
| `build_cycles` with every option row refused | **93 cycles: 60 with decision days in 2019-2023, 33 in 2024-26** |
| One cycle per calendar month; each expiry has a future on its decision day | the builder's test passes; my list agrees |
| First cycle | decided 14 Jan 2019 for 28 Feb 2019. January 2019's window opened before the panel, so that month has no cycle, as claimed. |

### The two months with two future expiries (my own finding, checked)

**June 2023.**
- **What the panel shows:** the contract was listed as 29 Jun up to 27 Jun 2023, then as 28 Jun on 28 Jun only. NSE
  moved the expiry when the Bakri Eid holiday moved.
- **The cycle:** 29 Jun, decided 15 May, exit 8 Jun.
- **Why that is right:** 29 Jun was the listed expiry on both the decision day and the exit day. Using it is
  point-in-time correct, and the cycle exits before expiry, so no settlement uses the moved date.

**September 2025:** the 25 Sep contract was re-dated to 30 Sep, and the cycle takes 30 Sep (decided 18 Aug, when it
was listed so), as claimed.

### Discovery is unchanged

I re-ran experiment 1's discovery period through the runner and wrote it to my scratch folder: SHA-256
`814a79a56db4…`, **byte-identical** to the committed file.

## The access claim: no 2019-2023 option price read

**It holds.**
- `test_every_year_has_one_cycle_per_monthly_expiry` and my own counting both read the panel with `keep` refusing
  every option row. Only session dates, futures' expiries and closes are held.
- **One disclosed exception:** `test_the_far_listed_2019_weekly_had_no_future` keeps the option rows of the 18 Apr
  2019 **weekly** to find its first listing date.
  - It does hold those prices in memory, but prints and computes none of them.
  - That weekly is not a monthly contract and is never traded by experiment 1.
  - **Accepted as harmless.** It would be cleaner to read only the dates (a `keep` that returns rows without prices
    is not available, so this is noted, not required).

## Claims vs reality

| Claim | Result |
|---|---|
| Futures rule: 60 and 33 cycles, 12 a year | **True** (my run) |
| 18 Apr 2019 first listed 15 Feb 2019 (62 days ahead), never with a future | **True** (test passes; my futures read lists no such expiry) |
| Equal to A5 in 2024-26; last-of-month would wrongly take 30 Apr 2025 | Consistent with my counts (2024-26 unchanged, discovery identical) |
| A window that opened before the panel gives no cycle | **True** (the first cycle is February 2019) |
| Discovery byte-identical | **True** |

## Required before experiment 1's freeze (routed)

`research/2026-10-12-experiment-1/PROTOCOL.md` line 25 still names `monthly_as_of` as the monthly identity. It must
name the futures rule (`monthly_from_futures`), including how a re-dated contract is treated, before the protocol is
frozen. Otherwise the frozen text and the code disagree.
