# Judge 490: MS-P1f, tickets and the three counts (second judge)

**Scope:** story/ms-p1-tickets at f591ba21 (builder session_01CmKJ6taCLzfEGg7wt6RC4N), diff f591ba21^2 (4451a75b,
part a with the story) to f591ba21. The story's part f and its Claims. Lane 1, money piece: JUDGE.md "Two judges",
second judge, independent of Judge K (I didn't read K's verdict). Round 1 of 2. Judge H
(session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: FAIL.** 3 should-fix, 1 minor. The branch has since moved to a50caf62. After writing the findings below I
checked that tip only for whether each still holds (see the end).

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Tickets: same quotes and laws, account limits relaxed; never in an account; never in rupees | PARTLY | `rules.py`, `book.py` (own `TicketLedger`), `rupees.py`; plants caught. Findings 1 and 2 |
| 2 | eligible >= fillable >= executed over a fixture day | MET | `counts.py:22-27`: fillable needs trade or ticket (both carry a proposal), executed needs fillable; 3 plants caught |
| 3 | Shared displayed size counted; no unservable fill summed | PARTLY | `shared_size.allocate`; 4 plants caught. Finding 3 |
| 4 | A refused ticket stays in the denominator | MET | `totals.scheduled` counts every row; duplicates refused (plant caught) |
| 5 | Conformance | MET (n/a) | f implements no port of a |
| - | Gates | MET | pytest -n auto: 10,358 passed, 16 xfailed. ruff check/format, check_imports and check_records are clean. Largest file is 64 lines |

## Findings
1. **Should-fix: a refusal is named by an account limit even when a binding law also refused.**
   - `_after_laws` uses `refusals[0]` (`rules.py:47`).
   - My run: `[bucket_cap, daily_stop]` gives `refused: bucket_cap`, and `[open_risk, max_loss]` gives
     `refused: open_risk`.
   - The record and both reports then say a cap stopped a trade that the daily stop, or the Rs 10,000 loss law,
     actually stopped. An account limit is exactly the reason that would have made it a ticket, so the record misleads
     on why there was no ticket.
   - Expected: the reason is the first binding refusal (a stop, then trade validity), never an account limit when a
     binding law refused, with a test for each mixed pair.
2. **Should-fix: no law results means every law passed (fails open).**
   - `classify` with a `check` that returns `()` gives `trade` (my run).
   - `ticket_laws_pass(())` and `first_binding_refusal(())` both let a ticket through, so `TicketBook.enter(...,
     results=())` fills it: the self-review's blocking case comes back through an empty tuple.
   - a's laws fail closed on bad input. The empty case should too: missing results are a wiring fault in j, not a
     pass.
   - Expected: an empty result set refuses or raises in `classify`, `TicketBook.enter` and `counts_for`, with tests.
     [reasoning only: a's contract has no list of law names; a non-empty check is the floor]
3. **Should-fix: who gets shared size is decided by the owner's name.**
   - `allocate` sorts by owner string (`shared_size.py:43`), so `CS1@1`, `DB1@1` and `DR1@1` always come before
     `N0@1`, `RC1@1`, `REF@1` and `WS1@1` on a contended contract.
   - The fills marked unservable fall systematically on the controls (RC1, REF), and on drivers late in the
     alphabet. That biases the driver-against-control comparison the card exists for.
   - Expected: an order no driver can win by its name (for example seeded per session, slot and road, recorded with
     the allocation), with a test that it doesn't follow names.

**Minor:**
- (a) `TicketBook.enter` takes `results` from its caller, beside the `SealedDecision`, and doesn't read them from the
  sealed `DecisionRecord.law_results`. j must pass the sealed ones. State it in j's story, or take the record.

## Plants
16 planted, 16 caught (one plant first failed to apply and was re-planted by line).

## Notes
- `counts_for` doesn't use `allocate`: a fill the shared size couldn't serve still counts as fillable unless j feeds
  the allocation back. a50caf62's `fill_status` (`unavailable: size_shared`) looks aimed at this; j should wire it.
- **At a50caf62, read after writing the above:**
  - Finding 3 is addressed: a seeded order, accounts before tickets.
  - Finding 1 is partly addressed: stops are named first, but `[open_risk, max_loss]` still gives `open_risk`.
  - Finding 2 is unchanged.

## Addendum 1

**Round 2 of 2:** story/ms-p1-tickets at a50caf62 (the round 2 after Judge K's judge 481; I still haven't read K's
verdict), tickets diff f591ba21..a50caf62. **Verdict: FAIL.** 2 should-fix still open, 1 minor. This was my last
round: the owner decides (JUDGE.md, two judges for money pieces).

**Gates (my run):** pytest -n auto: 10,369 passed, 16 xfailed. ruff check/format, check_imports and check_records
are clean.

**Round-1 findings:**
1. **Refusal reason: PARTLY fixed, still a should-fix.**
   - Stops are named first: `[bucket_cap, daily_stop]` now gives `refused: daily_stop` (my run; plant caught).
   - But `[open_risk, max_loss]` still gives `refused: open_risk` (my run). A trade the Rs 10,000 loss law refused is
     recorded as a cap refusal, the one reason that would have made it a ticket.
   - Expected, unchanged: never name an account limit when a binding law refused, e.g.
     `(stops or binding or refusals)[0]`, with a test for the pair.
2. **Empty law results pass: NOT fixed, still a should-fix.**
   - `classify` with `check -> ()` gives `trade`. `ticket_laws_pass(())` is True and `first_binding_refusal(())` is
     None (my run, at a50caf62).
   - Expected, unchanged: an empty result set refuses or raises in `classify`, `TicketBook.enter` and `counts_for`.
3. **Size by owner name: ACCEPTED.**
   - The order is seeded from SHA-256(session, slot, road), with accounts before tickets. The seed and the order are
     recorded.
   - An unservable account entry becomes `unavailable: size_shared`: fillable, not executed, left out of
     `account_net`.
   - Plants caught: order by name, no account-first group, a constant seed, `fill_status` ignoring the allocation,
     `size_shared` ignored in the counts.
- **Minor (a): not changed.** Results are still passed beside the `SealedDecision`; j must pass the sealed ones.

**New minor:** an outcome whose exit was unservable isn't tested: removing the `o.exit` term in `rupees.py:22`
survived. The code is right; add the test.

**Plants:** 7 on the new code, 6 caught, 1 survived (the new minor).

## Addendum 2

**Round 2 of 2, at the right tip:** story/ms-p1-tickets at b40cf1cf (code cad9a608 / ec9128b6), tickets diff
a50caf62..b40cf1cf. The orchestrator ruled that Addendum 1 judged a superseded tip and doesn't use up the round. This
addendum replaces it as my round 2. **Verdict: PASS** as second judge, with 1 minor. I still haven't read Judge K's
verdict.

**Gates (my run):** pytest -n auto: 10,626 passed, 16 xfailed. ruff check/format, check_imports and check_records
are clean.

**Findings:**
1. **Refusal reason: ACCEPTED.** `named_refusal` names a stop, then a trade-validity law, then an account limit.
   My runs:
   - `[bucket_cap, daily_stop]` gives `daily_stop`;
   - `[open_risk, max_loss]` gives `max_loss`;
   - `[open_risk, bucket_cap]` gives `ticket: account_limit`.
   Plant (`binding` dropped) caught.
2. **Empty law results: ACCEPTED.** `classify` raises on `()`, `ticket_laws_pass(())` is False,
   `first_binding_refusal(())` raises, and `counts_for` raises for a trade or ticket with no results. All 4 plants
   caught.
3. **Size order: accepted in Addendum 1, unchanged.**
- **Minor (a), results from the caller: ACCEPTED.** `TicketBook.enter` now takes the sealed `DecisionRecord` and reads
  its `law_results` (plant setting `binding = None` caught).

**Still open, minor:** no test covers an outcome whose exit was unservable (removing `o.exit` in `rupees.py` survives
again). The code is right. Add the test before j relies on it.

**Plants:** 7, 6 caught, 1 survived (the minor).
