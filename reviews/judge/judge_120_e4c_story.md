# Judge 120: E4c story text, refuse an entry whose protection cannot be traded both ways: `story/e4c-protective-leg-refusal` 7e33fc9c66cacfd588f976cb7732cc7406983047 (quality rule 1, text only)

**Number note.** E4c has no response file yet, so I used 120, the next free judge number. The orchestrator may
renumber it if 120 is reserved.

**What I checked:**
- the E4c section, the only change;
- the code on `main` at fd6c50a: `fno/desk/snapshot.py` `a4_problem`, `fno/desk/entries.py` `EntryDesk.enter` and
  `_unwind`, and the named tests in `tests/desk/test_entries.py`;
- C5 at b929743: `fno/risk/book_view.py` `session_trades`;
- design v2 6.1a and 3.2.

## The orchestrator's questions

**(a) No bid, bid 0 or no bid size are already refused on both sides: TRUE.**
- `ExecutionQuote.a4_problem` (`snapshot.py:48-59`) returns a problem when bid or ask is missing or not above zero,
  when the book is crossed, when either size is missing or not above zero, or when the contract had no trade today.
- The quote is then unusable for a buy as much as for a sell, and
  `test_a_protective_leg_without_a_valid_quote_opens_nothing` exists (`tests/desk/test_entries.py:123`).
- So exception 3 is reachable only with a valid two-sided quote whose bid size is above 0 but below the units, as the
  story says.

**(b) Checking every protective leg both ways before any fill: CONSISTENT with design, but it stops halfway.**
- **What the design requires.** Design v2 6.1a (approved): "On paper all legs fill at one snapshot or none
  (section 3.2)".
- **What the code does today.** `EntryDesk.enter` prices every leg first. If any leg does not fill, it fills legs in
  order and unwinds at the first failure (`entries.py:128-139`, `_unwind`). So partial fills exist only because the
  loop fills before checking quotes it already holds.
- **What E4c covers.** The protective legs, both ways. The story's own reason is "on paper every quote of the snapshot
  is known before the first fill ... so both are refusable in advance".
- **What it leaves.** Short legs: "Short leg's bid short: E4's partial fill and unwind — unchanged". A short leg whose
  bid size is below its units then still buys the protection and sells it back at once. That is the same paid-twice
  spread and both-sides record that decision 30 is meant to remove, at the same snapshot, and against 6.1a's "or none".
- See should-fix 1.

**(c) No spread-width threshold: SOUND.**
- A wide spread with enough bid size sells back, so it causes no same-snapshot close.
- The cost of crossing it at entry is bounded by E4's entry limit (the net at the touch must be no worse than C2's
  approved entry cash, `entry_shortfall`).
- A width rule would be a new, unsourced threshold, so it is rightly an owner question with A16's spreads as the
  evidence.

**(d) C5: a refusal does not count toward the Rs 50,000 new risk: CORRECT at b929743.**
- `session_trades` (`fno/risk/book_view.py:39`) is built from `PaperAccount(root, book).fills()`, the E1 ledger:
  only trades with a fill on the day.
- A refused entry writes no fill, so it never enters `session_trades`. D2's same-session count is the conservative
  side, as stated.

**(e) E8: SOUND as specified.**
- One pure function of (snapshot, legs, units), called by `EntryDesk`.
- A test shows it depends only on the snapshot given, so E8 can call it at each R's own snapshot. Each R is then its
  own single-snapshot entry.

**(f) Four existing lane-1 tests change: not loosened, as specified.**
- **Three exist on `main` today:** lines 112, 130 and 158 of `tests/desk/test_entries.py`. The fourth, E2b's
  `test_unverified_protection_at_the_opening_snapshot_closes_there_the_third_exception`, is on E2b's branch, not yet
  on `main`.
- **Each change asserts stricter behaviour:**
  - nothing bought instead of a buy and unwind;
  - the pending-unwind path kept, re-pointed at the only leg kind that can still be pending (a short leg's buy-back);
  - the same outcomes with new reason text;
  - `not_opened` instead of an exception.
- **In the code round I check** that no assertion is dropped and that the pending-unwind path stays tested.

**(g) The 16-row case table against rule 5: good, with one gap.**
- **Covered:** the positive case; both boundaries (64 / 65 / 66); the negative case (1); the A4-invalid cases; a
  one-leg trade; multi-leg STR1; a short leg's bid short; both empty cases (no protective leg; no quote at all); C3
  first; a rerun.
- **Missing:** a protective leg with a valid quote whose **ask size** is below the units. That is
  `protection_not_buyable` from size alone, the buy-side mirror of the 64-unit row. See minor 1.

## Should-fix (text)

1. **"All legs at one snapshot or none" is applied to protective legs only.** The gap list maps design 3.2 / 6.1a to
   criteria 1 and 4, but short legs can still produce a same-snapshot buy-and-sell of the protection. That leaves the
   requirement partly covered and not marked Out, which rule 2 forbids. Choose one:
   - **(A) recommended.** Check every leg's opening side (`price_leg(..., opening=True)`) together with the
     protective legs' closing side, before any fill. Any failure gives `not_opened` with nothing bought. At one
     snapshot no paper partial fill then exists. E4 criterion 2's unwind stays only as a guard, not a path.
     - This changes the behaviour of E4's passed criterion 2. It needs the orchestrator's decision recorded in the
       story, since lane 1 cannot reopen it silently.
     - E8's per-R fills inherit it.
   - **(B)** Keep short-leg partial fills, mark that part of 6.1a **Out** with its reason (for example, E4 criterion 2
     models legging deliberately), and add it to the open questions.

   Today's text claims the design point is covered while the short-leg path contradicts it.

## Minor (text)

1. Add the case "valid quote, protective leg's **ask** size 64 (below 65)": `protection_not_buyable`, nothing bought.
2. Criterion 5, "no quote figure": also say the alert line holds none. Its form already has only the contract and the
   units; make it testable in criterion 7.
3. The "Out" note on E4's existing "size N at the touch is below M units" reasons, which publish a quote size, is
   right to report to E2b. Name where it was reported (a decision or claims row), so it is not lost.

## Verdict: FAIL for 7e33fc9c66cacfd588f976cb7732cc7406983047 (story text)

One should-fix: the "all legs or none" scope must be completed (A, recommended) or the short-leg part declared Out
with a reason (B). Everything the orchestrator asked about checks out:
- (a) verified in the code;
- (c) sound;
- (d) correct against C5 at b929743;
- (e) sound;
- (f) as specified;
- (g) one case to add.

A re-check needs only the E4c section. Rule 9's ChatGPT review follows my PASS.

## Addendum 1 (15 Oct 2026): revision 1 at 8e53630c738645b8fab5ab1ee3630ff1b9ce3689 (7e33fc9..8e53630, text only)

| Judge 120 finding | Status | Check |
|---|---|---|
| Should-fix 1: "all legs or none" for protective legs only | **MET (option A, decision 43)** | Before any fill, the entry check covers every leg's opening side and each protective leg's closing side. Any failure gives `not_opened` with nothing bought, under one of three codes (`protection_not_buyable`, `protection_not_sellable`, `short_leg_not_sellable`). The change to E4's passed criterion 2 is recorded in the story with its reasons: the unwind becomes a guard, criterion 8. The gap list maps 3.2 to criteria 1, 3, 4 and 8, and the short-leg cases (64/65/66 and A4-invalid) are in the table |
| Minor 1: ask-size case | MET | "Protective ask size short", 64 units: `protection_not_buyable` by size |
| Minor 2: no quote figure in the alert | MET | Criterion 7: "a test checks the sent text against the snapshot's figures" |
| Minor 3: where the touch-size finding went | MET | Decision 42, E2b's fix round |

**The orchestrator's two questions:**

1. **E6's legging cost stays 0 unless the guard fires: TRUE.** `fno/scorecard/execution_costs.py:85` sums
   `legging_cost_rs` over E4's events. Only `_unwind` writes that field: the partial-fill event, or the exit that
   finishes a pending unwind. With the entry check first, no normal path reaches `_unwind`. Stated in the story, rightly
   as a known effect on E6's report, not a change to E6.
   - Design 6.1a still expects legging loss to be measured in the real-money test (8.4), so nothing is hidden: paper
     simply has none.
2. **Does the guard's test double exercise a real post-check fill failure? Not yet pinned in the text. This is a
   condition for the code round.**
   - On `main`, `EntryDesk.enter` prices every leg once (`quotes = [price_leg(...)]`, `entries.py:128`) and fills from
     that same list. If the entry check reads the same quotes, `quote.fills` is always true after the check passes, and
     the unwind branch cannot be reached from the snapshot at all.
   - So the guard test is meaningful only if the double is **injected at the fill step** while the **real** entry check
     runs on the **real** fixture snapshot. Two acceptable doubles:
     - a pricing function, given to `EntryDesk`, that returns a non-filling quote for the n-th leg on the fill pass
       only;
     - a journal whose `record_fill` raises on the n-th fill.
   - Not acceptable: a double that replaces the entry check (returning "no problem") or the whole `enter` path. That
     tests the unwind, not the guard behind a passing check.
   - **In the code round I will plant two mutations:**
     - removing the entry-check call must fail the normal-path tests;
     - removing the unwind call must fail the guard test.

   Both must be caught. If the guard is unreachable without a double, its code must say why it stays (a defect guard),
   so it is not dead code under the engineering rules.

**Tests changed on purpose (5):** all five named tests are stated, with "no assertion dropped (the unwind assertions
move to the guard tests)". Four are on `main`: `test_entries.py:112`, `:130`, `:140` and `:158`. The fifth is E2b's.
I check in the code round that each moved assertion still runs, now through the guard.

**Verdict: PASS for 8e53630c738645b8fab5ab1ee3630ff1b9ce3689** (story text), with the guard-double condition above
for the code round. Rule 9: ChatGPT's review comes next, before the merge.
