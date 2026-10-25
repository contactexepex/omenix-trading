# Judge 544: A4h-2, the day's high, low and previous close, code (story/a4h2-day-range @ 72d769b8; code 93ea7e9c)

Judge F. Code round 1 of 2. The text passed in judge 541 add. 1. Lane 1 (a record feeding the forecast lab).

## Verdict: PASS. It may merge from Mon 26 Oct, outside 14:00-16:15 IST.

Gates on 72d769b8: **14622 passed, 0 failed**, 1 skipped, 16 xfailed; ruff, ruff format (2335), `check_imports.py`
and the record scan (8817) are clean.

Checked in the code:
- `read_answer` requires `high`, `low` and `previousClose` for NIFTY 50 and NIFTY BANK and keeps them optional for
  VIX.
- DR1 check 5 (`range_problems`): `low > high`, or `last`/`open` outside `[low, high]` with the edges included,
  refuses a checked index with a named reason and no level. VIX's findings go into `problems`.
- The confirm compares `high` and `low` with the same official file, and `previous_close` with the previous session's
  file (`calendar.previous_session`). The builder checked that after a muhurat session NSE's previous close is the
  muhurat close, on 4 Nov 2024 and 23 Oct 2025.
- A missing previous file stays unconfirmed under the overdue rule, with its own reason. A record from before A4h-2
  is confirmed on `last` alone.
- The interface change (`OfficialCloses.closes` becomes `values`) is announced to DR1's builder.

## Plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | a checked index not refused for its range | yes, 7 failed |
| 2 | the range edges excluded (`low < x < high`) | yes, 4 failed |
| 3 | `low > high` allowed | yes, 2 failed |
| 4 | `previous_close` confirmed against the same day's file | yes, 11 failed |

The builder's own 10 plants and the extended no-level test (7 forms of every planted, moved and official high, low and
previous close) are in the claims.

After the merge (quality rule 8): the first session's read, recheck and confirm lines with the new fields, no level.
