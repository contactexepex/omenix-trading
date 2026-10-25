# Judge 455: the evening's close through A4h (story/fl1-1d4-today-closes at cae76af8)

**Verdict: PASS (lane 1), with 1 minor finding. It merges after the go-live (e31e46ce, judge 454).**

`A4hTodayCloses` replaces `NoTodayCloses`. It reads A4h's day record, else its 16:00 recheck, verified through O9's
Drive cache. It uses NIFTY 50's and NIFTY BANK's `last` only when NSE's stamp is that day at 15:30 or later, and never
for an index A4h marks `official_close: false` (India VIX). The evening routine first runs A4h's own
`closes read --commit`, unchanged, committing only `receipts/data/closes/`, and posts an exit 1 to #fno-desk.

## Checked myself
- **Gates:** on cae76af8 merged with today's `main` (no conflicts), one run:
  - 9,486 passed, 16 xfailed;
  - `ruff check` clean; 1,791 files formatted;
  - imports clean; record scan clean (7,528 files).

  Strong evidence.
- **Mutations:**
  - caught: the stamp check dropped; the `official_close` flag ignored;
  - survived: the wiring put back to `NoTodayCloses()` (minor below).
- **A4h's own rule agrees.** `close_read/answer.py:32` refuses any list stamped before 15:30, so a record never holds
  an early stamp. The check here is a second guard, and harmless.
- **One builder per function.** A4h's command is called unchanged, and its receipts are committed only by its own
  path rule. The WORK_REGISTER's duplicated FL1 rows are now one current row (lane 3).
- **Labels.** The page still marks the evening's close provisional until the next morning confirms it against NSE's
  official file (FL1-1d-1's confirmation, judged in 444).

## Minor
**The wiring is unpinned.** With `today_closes=NoTodayCloses()` put back in `page_wiring.build_report_maker`, all 152
forecast-lab tests pass, and the evening would quietly check nothing again. Pin it in `test_wiring_editions.py`, as
the renderer and the cutoffs already are.
