# Judge 541: A4h-2, the day's high, low and previous close in A4h's record, story text (story/a4h2-day-range @ 4a03734a)

Judge F. Round 1 of 2. Lane 1 (a record feeding the forecast lab). Text only: the doc-reading tests are the gate
(owner, 23 Oct). Checked against DR1's approved staging model (`docs/stories/DR1-design-staging.md` on
story/dr1-design), where A4h's closes are the first dataset. Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (2 should fix, both small). The shape is right.

What fits the DR1 model:
- One parser of NSE's answer (A4h's `read_answer`), so FL1 gets no second one.
- The new fields are checked by A4h's confirm, which is DR1's certifier for this dataset, against the official file
  within `TOLERANCE`.
- No old record is rewritten: older records read "day range not recorded" and stay `provisional` until confirmed.
- No level in any line (criterion 5 extends A4h's criterion 8).
- DR1's builder is told of the new fields.

## Should fix

**SF1. DR1's sanity check 5 is missing for the new fields [strong: the DR1 text].** DR1's provisional level runs checks
1-5, and check 5 names this exact case: "a close outside the day's high-low". With `high` and `low` in the record, the
read can make that check for the first time.
- Add to "The read" and to the criteria: for NIFTY 50 and NIFTY BANK, a read with `low > high`, or `last` or `open`
  outside `[low, high]`, is refused with a named reason (no level). For INDIA VIX it is recorded as a problem, not
  refused.
- Criterion: a planted answer with `last` 0.01 above `high` is refused, `last == high` is accepted, and `low > high` is
  refused.

**SF2. No gap list (quality rule 2).** A4h's own text has one; this section needs its rows:
- FL1-1f's request and the owner's 30-second rule;
- DR1's checks 1-5 at the provisional level and check 6 at confirm;
- O9 write-once (no rewrite of old records);
- the no-level rule (judge 440 SF1);
- the 14:00-16:15 window and the merge date;
- quality rules 5, 6 and 8.

## Minor

`previous_close` is confirmed against "the previous session's official close, read from that session's file". Say
what happens when that file is not in Drive yet: the field stays unconfirmed under the same overdue rule as `last`, so
it is never silent.

Plants: none (text round).

## Addendum 1: round 2 at 7fb7d3de

**Verdict: PASS for the A4h-2 story text.** Code may start; merge no earlier than Mon 26 Oct, never 14:00-16:15 IST.

| Finding | Answer | Check | Result |
|---|---|---|---|
| SF1: DR1 sanity check 5 | The range check at the read: `low > high`, or `last`/`open` outside `[low, high]` (edges included), refused for NIFTY 50 and NIFTY BANK with a named reason and no level; VIX's finding goes into `problems`. Criterion 2b: 0.01 over, at the edge, and `low > high`, for both checked indices | read | **Accepted** |
| SF2: gap list | 12 rows: FL1-1f (the 30-second rule Out, as FL1's display), DR1 checks 1-6, O9 write-once, no level, the merge window, quality rules 5, 6 and 8, DR1's certifier Out | read; each row maps to a criterion or to Out | **Accepted** |
| Minor: `previous_close` without its file | Unconfirmed under `last`'s overdue rule (one alert at the second session after); criterion 3 tests it | read | **Accepted** |

For the code round, show criterion 2b's boundary cases and the planted values from criterion 5 absent from every line.
