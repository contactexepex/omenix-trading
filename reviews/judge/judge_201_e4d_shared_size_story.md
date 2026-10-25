# Judge 201: E4d story text, shared displayed size within a book: `story/e4d-shared-size` 06136baf (lane 1)

Judge B. The E4c builder. Claims: `reviews/claude/response_195_e4d-shared-size.md` (renamed from 193). Quality rule 1:
story text only, no code. The branch starts from E4c's b1de45e9, so its diff against `main` includes E4c until E4c
merges.

## Checks
- **The source.** ChatGPT review 123 Q2, E4c's first Known limit, and the orchestrator's "fix it, not just list it"
  (after response 192).
- **The path is real (code read).** `DeskSteps.fill` loops over a book's orders at one snapshot, and `entry_problems`
  checks each entry alone. `book1_orders` returns every traded opportunity, so two approved strategies sharing a strike
  (for example SF and BF on the monthly ATM) both fill against size only one could take. On paper this inflates
  results with fills that could not have happened.
- **The design is simple and fits.**
  - The units taken come from the book's own fill rows at this `snapshot_id`, so there is no new state and a rerun
    counts the same units.
  - An optional argument to `entry_problems` (empty by default) keeps E4c and E8 unchanged.
  - The check uses the same `price_leg` with summed units.
  - E4c's codes keep priority, and it is never pooled across books or shadow accounts (E1's firewall).
- **Criteria.** They are testable and cover positive, negative, boundary (129 refused, 130 opens), the two-book
  negative, the rerun, priority, privacy and the E4c-unchanged case. "Judge verifies" names three plants.
- **Coordination.** WORK_REGISTER row E4d is this builder's. It depends on E4c (judge 197, PASS), and E4c merges first.

## The orchestrator's question: count an opened protective leg's sell-back need on the bid side?
**Accepted (reasoning only).**
- E4c's rule is that every bought protection must be sellable back **at that snapshot**. If a later entry in the same
  book sells the same contract at the bid, or buys more protection on it, the first entry's sell-back would compete for
  the same bid size. Not counting it would let the second entry quietly make the first's protection unsellable: the
  exact gap E4c closed.
- The cost is a stricter refusal in one case: SF and BF in one book, opposite trades on the same ATM strikes. With a bid
  size between 65 and 129, the later one is refused even though the two would partly net.
  - That refusal is safe: paper, one entry fewer, never a fill that could not happen.
  - It is consistent with E4c, which also does not count a short leg's buy-back depth (Out, open question 2). The
    story keeps that asymmetry as stated.

## Notes (not blocking; fold into the code round)
1. **Wording after E2c.** "The records are committed after each entry" should read: kept in Drive after each entry
   (E2c's `DriveAccountSync`), which is what makes the rerun count the same units.
2. **Which fill rows count.** Say that every fill row at this snapshot counts by its touch side, including an unwind's
   closing fills, which are reached only through E4c's guard. Otherwise a guard unwind's sales would not reduce the bid
   size left.

**Verdict: PASS for 06136baf (story text).** Code may start. Rule 9 (ChatGPT) applies to the code.
