# Judge 439: A17e global markets, code (story/a17e-global-markets @ e1d3e812)

Judge F (independent). Story `docs/stories/A17e-global-markets.md` with amendments 2 and 3. Claims are in the "Code
claims" section of `reviews/claude/response_297_a17e-global-markets.md`. The builder first sent 03b555f1, then
e1d3e812 (amendment 3.7, part B's own window and commit). I judged e1d3e812, which holds 03b555f1. Lane 1 (outside
services, schedules). Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 should fix, 5 minor). The fix is small; I re-judge it quickly.

What is right, checked:
- Official values come first, and Yahoo is labelled as an aggregator, with `unverified (Yahoo only)` on the four
  indexes that have no official file.
- Yahoo's block rule (owner rule 50a79a43, rule 2): one plain GET with redirects not followed. A 401, 403 or 429, a
  redirect, a non-JSON page or Yahoo's JSON error each stop the cue. A shared `YahooGate` then stops every other Yahoo
  cue of the run. There is no retry, cookie, crumb or other user agent.
- Every value is private and kept in Drive. Lines and alerts name only cues, statuses and error classes.
- The `behind` alert fires once per episode and only for names with a real session calendar (judge 351 addendum 2).
- Part B handles every failure path with one alert and one O10 row, including a Drive failure while building the
  reader and a morning where every market is stale.
- The STOXX certificate completes the server's chain: the SSL.com intermediate (valid to 18 Oct 2032) is added to
  the CA bundle, and verification stays on. It gets around nothing.
- Amendment 2.1 (made-up fixtures) is right: real values would break the privacy rule, and the claims cite a dry run
  on the real answers. Amendment 2.2 (KRX deferred until a key exists) is right too: a parser written now would be a
  guess.

## Gates (exact head e1d3e812)

| Gate | Result |
|---|---|
| pytest `-n auto` (no Slack token, no growwapi) | **9034 passed**, 17 xfailed, 353 s |
| `ruff check`, `ruff format --check` | clean, 1673 files formatted |
| `tools/check_imports.py`, `tools/check_records.py` | clean (1763 files); record scan clean (7354 files) |

## My plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | Yahoo redirects followed (consent page accepted) | yes, 6 failed |
| 2 | the shared `YahooGate` ignored | yes, 1 failed |
| 3 | `final_values` keeps unfinished values | yes, 1 failed |
| 4 | part B never closes its 09:05 window | yes, 1 failed |
| 5 | `behind` episodes not saved (an alert on every run) | yes, 3 failed |
| 6 | part B's `seen_at` set 30 s before the response | yes, 1 failed |
| 7 | Hong Kong's close at 16:00 (before the closing auction) | yes, 1 failed |

## Should fix

**SF1. A Yahoo daily close is taken as final the moment the exchange closes. A copy fetched just after that keeps a
possibly pre-final value forever [code read: strong; Yahoo's delays: some].**

1. `final_values` (`collection.py:29-34`) keeps a value once `available_at(value_date) < seen_at`. For
   `YahooChartSource`, `available_at` is the market's close with no margin (`markets.py`, `yahoo_source.py:105`).
2. Yahoo serves many exchanges with a delay. Its help page "Exchanges and data providers on Yahoo Finance" lists a
   delay per exchange, for example 15 minutes for Cboe indices. For Hong Kong and the ASX, 15-20 minutes is common
   (Google's table gives 15 and 20). So a fetch a few minutes after the close can hold the last pre-auction price as
   the day's close.
3. The table keeps the first value for a date (`table.py` `merge`). A later, different value is only a `CHANGED`
   revision, counted in a log line ("n revisions logged") and not alerted.
4. For the four Yahoo-only indexes, no pair check can catch it either.
5. The exposed case today is the 14:11 IST run. Singapore's value becomes "final" at 14:30 IST, so a start between
   about 14:30 and 14:50 writes a possibly wrong STI close for good. GitHub has started that cron 3 h 42 to 7 h 09 late
   on every day measured, so this is rare, not impossible. The case grows once FL1 asks for same-day Asian closes from
   an on-time caller (scope item 6).

Fix expected:
- a Yahoo finality margin, for example `YAHOO_FINAL_AFTER = 30 min`, so a Yahoo value is kept only once
  `available_at + margin < seen_at`;
- boundary tests at the margin, one minute under and one minute over;
- keep the as-of labels as they are, or apply the margin there too, and say which.

The fix costs a few lines and stops a permanent wrong row.

## Minor

1. **Part B's second O10 row is never committed.** When a read fails, `_report` writes the O10 row before the commit,
   which is right. When the push itself fails, the second `_report` appends its O10 row after the commit, so in the
   routine's short-lived checkout that row is lost (the alert is still sent). A read failure plus a push failure also
   gives two #fno-desk lines. Both are defensible; say so in the module docstring, or record the push failure only
   in the alert.
2. **No routine starts part B yet, and it has no trading-day check of its own.** A22's routine section (on A22's
   branch) has no `global-cues preopen` line. A22 must add that line after its own "not a trading day" check, or
   part B must check NSE's calendar itself. This is a condition after the merge: criteria 8 and 9 (the first part B
   read cited) are not met until then.
3. **The claims file is out of date.** "Part B's repository receipts ... are committed by A22's routine line" is
   superseded by amendment 3.7 (part B commits its own files). Correct it in the next claims update.
4. **TWSE connection resets.** If these happen from GitHub's runners as they did here (2 of 4 runs), `taiex: FAILED`
   alerts on every run, up to three a day. The first week decides this. If it happens, one paced retry after a
   connection reset is polite and gets around no block (rule 281, items 2 and 3) [reasoning only].
5. **Criterion 9 has moved from a hand run to the first scheduled run.** That is acceptable as quality rule 8. The
   claims after the merge must cite the counts, the first and last dates, and the overlap findings named in
   criterion 3 (VIX on 6 Feb 2026, the two missing SSE sessions).

## Addendum 1: re-judge at 85cb612a (amendment 3.8; new section of response 297)

**Verdict: PASS. A17e may merge** (pull, full suite on the merged tree, `check_numbers.py`, then push).

Gates on 85cb612a: **9037 passed**, 17 xfailed; ruff, ruff format (1673), `check_imports.py` and the record scan
(7354) are clean.

| Finding | Builder's answer | My check | Result |
|---|---|---|---|
| SF1: a Yahoo close final the minute its market closes | `available_at` = the close plus `FINALITY_MARGIN` (30 min) for every Yahoo cue; the as-of labels take it too, which is conservative; STI tested at +29, +30 (not final) and +31 (final); official sources keep their own times | Plants: margin 0: 1 failed. Margin 29 min: 1 failed. Applying it to the labels as well costs nothing at 09:15 (every Asian and European close is hours old) | **Accepted** |
| Minor 1: part B's O10 row after a failed push lost; two alerts | The row is written before the commit, so the commit carries it; one alert names every problem ("kospi failed; receipts not committed"); a failed push adds no row of its own, and the alert reports it | Plants: row after the commit: 1 failed. Push failure left out of the alert: 2 failed | **Accepted** |
| Minor 2: no trading-day check | Part B reads NSE's calendar itself (regular or special, never muhurat-only) and prints "not a trading day" on a closed day | Plant: check removed: 2 failed | **Accepted** |
| Minor 3: stale claims line | corrected | read | **Accepted** |
| Minors 4 and 5 | after the merge | stays open: the TWSE reset rate from GitHub's runners, and criterion 9's counts and overlap findings | **Open (after merge)** |

**Minor (new, not blocking).** `nse_session_day` runs outside part B's failure handling. On a day outside the
calendar's range (for example 1 Jan 2027 before NSE's 2027 holiday rows are added), `CalendarError` ends the command
with a traceback, with no alert and no O10 row. A4's 3 pm capture alerts "stopped, nothing recorded" the same day,
so the owner still hears of it [strong for the path, `calendar.py:98-100`]. Catching `CalendarError` into the one
alert would make part B's own record complete. Still open after the merge: A22's routine line that starts
`global-cues preopen`.

## Addendum 2: the calendar minor, story/a17e-preopen-calendar @ eb9e7fb2

**Verdict: PASS. It may merge.** A17e itself is merged (bc21f17f, builder's report).

When NSE's calendar cannot answer for the day, `cmd_preopen` now:
- catches the `CalendarError`;
- prints a `STOPPED` line;
- writes one O10 row and sends one alert ("NSE calendar cannot answer for today", class name only);
- exits 1 having read nothing.

The new test covers it. My plant (the O10 row dropped) fails 1 test.

Gates on eb9e7fb2: **9236 passed**, 16 xfailed; ruff, ruff format (1725), `check_imports.py` and the record scan
(7445) are clean.
