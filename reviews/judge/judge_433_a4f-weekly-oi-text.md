# Judge 433: A4f NIFTY weekly expiries and open interest in the 3 pm capture, story text (story/a4f-nifty-weekly-oi @ 00173470), for response 302

Judge F (independent), quality rule 1. The "A4f" section of `docs/stories/A-data-foundation.md`. Lane 1 (the 3 pm
recorder, Groww, a v2-recorded file). Labels: **strong**, **some**, **reasoning only**.

## Verdict: PASS (3 minor, to carry into the code)

The owner's decision is on main (DESK_DECISIONS row 283, "Contract-level forecasts: all three pieces", piece 3: "the 3
pm capture extended to NIFTY weekly expiries (BANKNIFTY has none since Nov 2024) ... history from its start"). The
text follows it. The design is careful where it matters:
- `recorder.py` (348 lines) is split first, with no behaviour change, proven by A4's byte baseline and the v2 golden
  cases;
- `open_interest` is the last column, and every reader uses `DictReader`;
- the weeklies get their own dataset and stem (`niftyweekly`), so NIFTY's `nifty_*` glob and the monthly readers can
  never take them;
- they run in A4c's window and pace, so the monthly capture is untouched;
- the slot always leaves a canonical marker (id or `none`), so F1's restart rule and the e2e kill-rerun set cover it;
- the gap list is present, and the known limits are stated.

## Minor

1. **The expiring weekly on its own expiry day.** "The two nearest listed expiries from `day` on" includes a weekly
   that expires that afternoon. At 15:05 it has minutes to live, and piece 2 ("next-session premium range", scored
   against the next 3 pm) has nothing to score it against. Say whether the expiring weekly is recorded on its expiry
   day, and test that day. Recording it is fine (its last-day prices are data); then name it, so a reader can drop it.
2. **Boundaries (quality rule 5).** Criterion 3's 5% strike band at, just inside and just outside 5% of spot, and
   criterion 4's last request at 15:12:59 versus 15:13:00, as A4c's tests do.
3. **Open interest 0 against "not given".** Groww's parser turns a missing `oi` into 0 (`or 0`). For the put-call
   ratio and max-OI strikes that matters. Since the chain answer is already in hand, write an empty cell when the
   leg's raw answer has no OI field, rather than relying on the parser's 0. Or keep the stated limit and have the
   readers (G13's pieces) treat a 0 as unknown. Either is acceptable: say which.

## For the code round

The claims must cite:
- the first live day's weekly result line and timing (does the window still end about 15:07?);
- the A4 baseline diff showing only the new column;
- the golden check output "unchanged".
