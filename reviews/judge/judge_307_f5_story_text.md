# Judge 307: F5 story text, Book 2's decider (story/f5-book2-decider at 6d2b6331)

**Verdict: FAIL on the story text: 2 should-fix findings and 2 minor.** The core design is right:
- the sheet is computed by code inside the private pack;
- `rule_default` and `eligible` come only from the sheet, never from the AI;
- F6's `SelectionAllocator` is reused, with a rebuild for width and lots;
- C4's `EnvelopeMode` re-checks independently, and the unproven limit is re-checked at C4 (D4 option 2, judge 260
  addendum 2);
- the estimand label is named.

The interfaces with F1t do not match yet.

## Checked myself (strong evidence)
- D4 is merged: `EnvelopeMode` is in `fno/checks/wiring.py:85-91`.
- `eligible` = the versions that reached C2, as judge 260 addendum 2 settled.
- F1t at f1204a5a, the latest text that passed (judge 301 addendum 1):
  - `seal` checks F1t's base first: "`decision` is an object with `action` (text) and `reason` (one line)";
  - then it calls the book's shape check, named `check_decision(decision) -> list[str]`, "the port's one name", with
    F5's in `fno/book2/answer.py`;
  - the port block says "Owners: F5 (Book 2), F6 (Book 3)" for each book's `OrderBuilder` and `ExitRules`.

## Findings

**Should-fix 1. The answer shape and the check's name contradict F1t's port.** Strong evidence.
- F5's shape is `{"slots": [...], "reason": str}`. It has no top-level `action`, so F1t's base check would refuse every
  Book 2 answer at `seal`.
- F5 names its check `check_answer(obj, sheet=None)`; F1t's port names it `check_decision(decision)`.

Fix: put `action` (`follow_rule`, `no_trade` or `trade`, for example the day's summary, or `trade` when any slot
trades) and `reason` at the top of `decision`, with the slots inside it. Name the check `check_decision(decision)`;
the decider's sheet-aware check can be a second function. Confirm the result with F1t's builder.

**Should-fix 2. Book 2's orders and exits are missing.** Strong evidence. F1t's port makes F5 the owner of Book 2's
`OrderBuilder` and `ExitRules`, but F5's scope and criteria do not mention them. Fills need two pieces:
- an order builder that replays a committed Book 2 run, with its stored `selection` picks and any width or lots
  rebuild, and orders only the committed "trade" records (the shadow-only default case included);
- exit rules that fix each trade's exit day from the playbook version as the run read it.

Fix: add both, as F6 did (`Book3Orders` and `Book3ExitRules` reuse Book 1's `ReplayedOrders` and `PlaybookExitRules`),
with criteria: a changed pick or sheet refuses every order; a C4 block is never ordered; editing today's version file
moves no exit.

**Minor.**
1. **The shadow-only path.** When the account "takes the rule default", say that the default itself went through C2
   and C4 in the same run (it is the rule default, so it reached C2, but C4 must still pass it). A C4 failure of the
   default must then give no trade, with both records written.
2. **The unproven re-check at C4.** Name the C4 file and mode it changes (`EnvelopeMode` only, or every mode), and
   confirm that Book 1's C4 behaviour is unchanged by a test, since C4 is shared.

## Open questions (for the orchestrator; my view)
1. **F4 is not built, and has no owner.** F5 recommends that Book 2 waits for F4 (design 12.2: the judge can block).
   That blocks Book 2's go-live on a story that has no owner, and the O11 plan (judge 305) talks of folding F3 into T3
   and leaving F4 aside. This is the owner's decision: wait for F4, or switch on with `judge: "not built"` and C4 as
   the last gate, labelled. Put it to the owner before Book 2's go-live; it does not block F5's code.
2. **One slot per default trade:** this matches D4's one-choice-against-one-default check, and is simpler. I agree
   (reasoning only).

## Addendum 1: 0b77381f

**Verdict: still FAIL, 2 should-fix findings (one carried over, one sharpened).** Accepted since 6d2b6331:
- E2c's four pack rules (Book 1's pack SHA-256 unchanged; `canonical_json`; a failing sheet refuses only its own pack;
  own folders only), in criterion 1;
- the sheet reads only the canonical snapshot the common pack names;
- the check is renamed `check_decision`;
- `seal` refuses private figures.

**Should-fix 1 (carried over): the answer still has no top-level `action`.** Strong evidence: line 76 is still
`{"slots": [...], "reason": str}`. F1t's base check at `seal` (f1204a5a, lines 184-185) requires `decision.action`
(text) and `decision.reason`. As written, every Book 2 answer is refused before F5's check is even called.

Fix: add `action` at the top of `decision`. For example, `trade` when any slot trades, `no_trade` when every slot is
`no_trade` or there are no slots, and `follow_rule` when every slot follows. Have `check_decision` require it to agree
with the slots.

**Should-fix 2 (sharpened): Book 1's `ReplayedOrders`, reused as written, would order the rule default, not the AI's
choice.** Strong evidence (code read, `fno/books/book1_orders.py:39-57`). It replays D2's own evaluator and orders
`evaluation.chosen` whose stored action is "trade". For Book 2, D2's own choice is the rule default; the AI's
`choose_width`, `reduce_lots` and `choose_strategy` picks come from the `SelectionAllocator` and its rebuild. A plain
reuse "parametrised by book" would fill the default's terms while the record says the AI's.

Fix: as F6's `Book3Orders` does, hand `ReplayedOrders` an evaluator rebuilt with the `SelectionAllocator` and the
picks stored in the run's `inputs.json` (`selection`). Extend criterion 9:
- a `choose_width` run orders the rebuilt width;
- a changed stored pick refuses every order;
- a C4 block, or a shadow-only choice's AI terms, is never ordered (the account gets the default);
- editing today's version file moves no exit.

Minor findings from the verdict, still open:
1. On the shadow-only path, the default itself passes C2 and C4 in the same run.
2. Name the C4 mode the unproven re-check changes, with a test that Book 1's C4 behaviour is unchanged.

## Addendum 2: 778e9c0f

**Verdict: PASS on the story text, with 1 minor finding for the code round.**
- **Should-fix 1: closed.** The decision is `{"action": "follow_rule" | "change", "reason", "slots": [...]}`, checked
  by `check_decision(decision, sheet=None)`. Criterion 2 requires that F1t's base check passes everything
  `check_decision` accepts.
- **Should-fix 2: closed in the design** (part 3, item 7). `ReplayedOrders` replays Book 2's committed run "through
  D2's evaluator with the `SelectionAllocator` rebuilt from `inputs.json`'s `selection`". A run that does not replay
  orders nothing, and only C4-passed trades are ordered. Exits use `PlaybookExitRules`, from the version the run read.
- **Minor findings from the verdict: closed.**
  - The shadow-only default passes the same allocator, C2 and C4.
  - The unproven check is named in `EnvelopeMode`, and criterion 10 shows Book 1's C4 is unchanged.
  - Decision titles are cited instead of row numbers.
  - D3 criterion 6 names Book 3's day-record exemption.
  - S2's "overrides (F4)" input is removed.

**Minor, for the code round.** Criterion 9 tests the refusal cases (a changed pick, a C4 block, a version file edit).
It does not test the positive case that would catch the exact bug of addendum 1: **a `choose_width` (and a
`reduce_lots`) run's entry order carries the AI's rebuilt width and lots, not the default's**. Add it. I will plant
"replay with D2's plain evaluator" in the code review.

## Addendum 3: a32f8ff7
**PASS stands; the code-round minor of addendum 2 is closed in the text.**
- `action` is `follow_rule`, `trade` or `no_trade`, and `check_decision` refuses an action that disagrees with the
  slots.
- Criterion 9 now says the evaluator `ReplayedOrders` replays is rebuilt with the `SelectionAllocator` and the stored
  picks, "never D2's plain evaluator".
- It adds the positive case "a `choose_width` run orders the rebuilt width, not the default's", and orders the default
  for shadow-only.

(Addendum 1 judged 0b77381f because the 778e9c0f message arrived after it was written; both heads' fixes are now
covered.) For the code review I will also check `reduce_lots` (the AI's lots reach the order) with the same plant.

## Addendum 4: 0bb574de (F4's evidence and the judge-blocked run)
**PASS stands. F5's side of judge 308's should-fix 2 is closed.** I read the docs-only diff from a32f8ff7:
- the top-level `evidence` list, and any action other than `follow_rule` must cite one;
- `check_decision` calls F4's `evidence_problems`;
- prompt lines matching F4's rules (account files are not citable; `/evaluation` values are);
- D3 `judge` = `AcceptedDecision.judge`;
- the market is read through E2e's `canonical_snapshot`.

New and agreed with F4 (00f49a0c): `decide()` always runs. A blocked or unavailable judge gives a "no trade, judge
failed" run, with the default as a D3 shadow, so scoreboard A keeps the paired day (criterion 11). F1t's run check
refuses a blocked run with any chosen trade.

Two dependencies are now explicit:
- F1t's text must gain `judge` and `judge_blocks` in `AcceptedDecision`, plus that run check (judge 308 should-fix 2,
  F1t's side, still open);
- `canonical_snapshot` must read the pack's own snapshot (judge 309 should-fix 1). Until then, F5's "only the pack's
  snapshot" criterion rests on a function that follows the marker.

## Addendum 5: 95cd4b8c
**PASS stands.** The docs-only diff from 0bb574de adds criterion 12: before F5 merges, its part of O11's strict xfails
becomes a real replay check. That covers the Book 2 decision on the recorded day (shared with F1t) and Book 2's half
of the daily run's fills and exits (shared with F6), as D3, D4, D5 and O1 did under judge 306. Good: it keeps the
"not implemented" list honest. The dependencies of addendum 4 are unchanged (F1t's `AcceptedDecision` fields, judge
308.1).
