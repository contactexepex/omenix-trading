# Judge 87: story S2, scoreboard B (whole systems), branch before merge

Date: 14 Oct 2026 (UTC). Branch `story/s2-scoreboard-b` at 258f369. That is 45c8376 plus one commit with the
orchestrator's answers; the branch includes S1's passed b1a6092. Claims: `reviews/claude/response_88_s2-scoreboard-b-design.md`
addenda 1 and 2. Story: `docs/stories/S-scoreboards.md` S2. I judged the S2 commits on top of S1.

I do not count as deviations the orchestrator's answers on F4, the pilot label, equity history and provisional
figures.

## Verdict: FAIL, one small must-fix (the AI cost is subtracted in every section), shown by probe

Everything else is right, and the story's own judge check (below) matches to the paisa.

## Gates (my runs, `python -B`, caches cleared, Slack token unset)

- Full suite: 2,981 passed.
- `ruff check`: clean. `ruff format --check`: 676 files. Imports: clean (683).
- `git merge-tree` with current `main` (471493e): **conflicts in `CLAUDE.md` and `reviews/claude/README.md` only**
  (text: keep every line).

## The story's judge check: one book's monthly net and net per unit of risk, recomputed from the records

I read the fixture's raw `desk_fills.csv` for Book 1 with my own script: sells minus buys at the fill price times units,
minus `charges_rs`. I used none of the project's code.

| Trade | My net (Rs) | The board (Rs) |
|---|---|---|
| p1 (pilot) | 1,193.86 | pilot raw 1,193.86 |
| h1 (head-to-head) | 2,492.90 | head-to-head 2,492.90 |
| o1 (overridden) | −430.33 | overridden −430.33 |
| u1 (no record) | 217.65 | unscored 217.65 |
| **October 2026 net** | **3,474.07** | C1 month table 3,474.07; overall 3,474.07; reconciliation ok |

**h1's net per unit of risk.**
- Its maximum loss at entry is Rs 6,000 (D3 record), and the sessions from 16 Oct to 21 Oct are 16, 19 and 21 Oct
  (20 Oct is Dussehra).
- Held at the close: 16 and 19 Oct. On 21 Oct it closed.
- Risk-days = 2 × 6,000 = 12,000, and 2,492.90 / 12,000 = **0.207742**. The board says 0.207742.
- The mean daily risk over the 5 head-to-head sessions is 12,000 / 5 = 2,400. The board says 2,400.

**MET.**

## Must-fix: the allocated AI cost is taken off in every section, so it is counted several times

`BookBoard._section` calls `self.ai.allocated(book, first, last)` for **every** section and subtracts it in each
`net_rs`:
- overall;
- pilot (over the account's whole period);
- head-to-head;
- each segment;
- unscored;
- overridden.

The docstring's own rule for operating costs ("the book's, not a version's: they enter the book-level sections only")
is not applied to the AI cost.

**My probe** (the branch's fixture, the AI port faked at Rs 1,000 for any period). Book 1's (raw, net):

| Section | (raw, net) |
|---|---|
| overall | (3,474.07, 2,474.07) |
| pilot | (1,193.86, 193.86) |
| head-to-head | (2,492.90, 1,492.90) |
| segment v1 | (2,492.90, 1,492.90) |
| unscored | (217.65, −782.35) |
| overridden | (−430.33, −1,430.33) |

Pilot, head-to-head, unscored and overridden partition Book 1's trades. Their nets carry Rs 4,000 of a Rs 1,000 cost.
- The pilot section's period (first session to the report day) overlaps head-to-head's, so the AI cost after the
  common start is in both.
- A book with two segments would show each segment's net reduced by the whole book's AI cost.

**Today no wrong number is printed**, because `AiCostBeforeF8` gives Book 1 Rs 0 and the AI books "not available".
But the defect sits in S2's own code and turns on the day F8 fills the port. The AI books' `net_rs` is the primary
verdict (S1's `primary_metric`).

**Fix (small):**
- Take the AI cost as the operating costs are taken: only in the book-level sections, each over its own
  non-overlapping period. Pilot runs from the first session to the day before the common start; head-to-head from the
  common start to the report day. Overall covers both.
- Segments, unscored and overridden show no AI cost (or say "book-level").
- Test: with a fake allocation, pilot net plus head-to-head net equals overall net (no double count), and the
  segments, unscored and overridden carry none.

## Per criterion

| # | Criterion | Check | Result |
|---|---|---|---|
| 1 | Every number of design 12.5 per book and segment | Tests check every key. Read: gross, pads, charges, execution costs, operating costs, AI (labelled), raw and net, max loss, risk-days, net per risk, margin-days (at entry, labelled), stress usage, trades | MET |
| 2 | Account net reconciles with C1 to the rupee | My recomputation matches. My plant (tolerance Rs 1,000) is caught | MET |
| 3 | Pilot, unscored and overridden apart | My plants: pilot split `<=` (4 failed), overridden in head-to-head (3), late runs starting the comparison (1). The AI cost leaks across these sections (must-fix) | PARTLY |
| 4 | Byte-identical rebuild | Test (canonical JSON, input hashes) | MET (read) |

## My plants (7, `tests/scoreboard`): all caught

| Plant | Result |
|---|---|
| Held at the close includes the close day | 2 failed |
| Pilot split `<=` | 4 failed |
| A stale mark becomes unvalued | 1 failed |
| Late runs start the comparison | 1 failed |
| Reconciliation tolerance Rs 1,000 | 1 failed |
| Operating costs ignored | 2 failed |
| Overridden counted head-to-head | 3 failed |

## Follow-ups (not blocking, reasoning only)

1. **A whole month's operating costs are booked on the last session in the period.**
   - On a mid-month report day, the full month's cost lands on that day.
   - In the common-start month, all of it counts head-to-head, including the days before the start. The builder
     chose this, and it is conservative for head-to-head.
   - Pro-rating by sessions would be fairer. It is the owner's call, best written into S1.
2. **The builder's own follow-ups stand:**
   - equity history;
   - C1 pricing at the charges table in force when a trade filled;
   - daily stressed margin;
   - Holm's correction in S4;
   - snapshot files in the input hashes.
3. **The uncertainty block** applies S1's proposals, labelled provisional. That is correct until the freeze.

## Claims vs reality

| Claim | Reality |
|---|---|
| Known answers by hand | Confirmed by my own recomputation from raw fills |
| "23 of 23 mutations caught" | Not re-run; my 7 are caught |
| Net minus AI cost tested | Tested per section, not across sections, so the multiple count passes (must-fix) |
| No real figures yet | True: there are no trades on `main` |

## Project rules

- New package `fno/scoreboard/` with its own wiring. The largest module is 82 lines.
- Ports exist for the operating costs, F4 and F8.
- The output is canonical JSON. No orders, no AI, no secrets.

## Addendum 1 (771d508 = the fix on cb7b3b4, which is 258f369 plus a merge of main): PASS

**The must-fix is met.** The AI cost is charged only at book level, over periods that do not overlap:
- overall: first session to the run date;
- pilot: first session to the day before the common start;
- head-to-head: common start to the run date.

Segments, unscored and overridden carry none, labelled "charged at book level only".

**My probe** (my own fake: Rs 7 per calendar day, any book). For each of Book 1 and Book 2:
- overall 77, pilot 21, head-to-head 56. **21 + 56 = 77**, so nothing is counted twice.
- Every segment, unscored and overridden section carries the label, not a rupee.

**My plants (3, `tests/scoreboard`): all caught.**

| Plant | Result |
|---|---|
| Pilot AI over the whole period | 1 failed |
| Segments carry AI again | 10 failed |
| Head-to-head AI from the first session | 1 failed |

**Gates (my runs, `python -B`, caches cleared, token unset):**
- full suite: 2,990 passed;
- ruff, format (678 files) and imports (685): clean;
- `git merge-tree` with current `main` (7c3afb4): clean. The doc conflicts were resolved in cb7b3b4.

**Follow-ups (not blocking):**
1. Segments, unscored and overridden show `net_rs` equal to the raw net, under the book-level label. For an AI book
   whose allocation is not available, the book-level `net_rs` is null while a segment shows a number. Better: segment
   `net_rs` null (or absent) with the label, so no reader takes it for an after-AI net.
2. When the common start is the account's first session, the pilot AI period is (first, first − 1 day), an empty
   reversed range. F8's allocation must return 0 for it; add that test when F8 is built.
3. The judge-87 follow-ups stand: pro-rate operating costs, plus the builder's list.

**Verdict: PASS** for 771d508. After the merge I check `main` and CI.

## Addendum 2 (merge check, a9a3cd1)

**MET (merge).**
- a9a3cd1 has parents 78411bb (`main`) and 771d508 (the passed tip), and it equals my recomputed merge.
- The only code since my last check is S2's own.
- b34b74e adds only the builder's response (the two follow-ups recorded, not built).
- CI on a9a3cd1 (run 38551046960) was in progress when I wrote this; I confirm it at my next check.
