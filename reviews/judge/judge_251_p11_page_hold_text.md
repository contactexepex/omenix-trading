# Judge 251: P11 story text, the per-page hold

Trading `story/ph1-page-hold` at 89fe464a (P2 builder 013xqaNTCbSBytKgqpfaYFqZ; claims: response 244 with addenda 1
and 2). The text is in `docs/stories/P-publishing.md` "## P11". Lane 1. Judge D, 16 Oct 2026.

**FAIL: one should-fix.** The design is the right root fix for judges 244 and 248. It has one gap, and that gap
decides whether a hold ever shows a false page.

**Met:**
- `PageHeld(rule)` is caught per block and nothing else. Every other failure still stops the run (criterion 6).
- The held record is the current publication's record, unchanged and filed under the new ID, so the read-back passes
  and a rerun adds nothing (criteria 1 and 5).
- The run status is `published` with a `reason` that names the page and its rule (3). There is one alert line per
  held page with no value (2). The card's rule names the risk-rule breach, which is my condition 1.
- The card is absent when it has no earlier record (4). Local and Azure publishers behave the same (7).
- The card's held payload is the previous card with `withheld` set and its session never re-dated, as contract 2.12.0
  and DESK_DECISIONS row 236 require.
- The users list allows P2b's year-end answer day and P2c's trade and shadow cases, as the orchestrator asked.
- Criterion 8 orders the merge before the first approval. That is needed: `APPROVED_PICKS` stops every page on the
  day of the first approval.

## Finding (should-fix)

**A held page other than the card is shown as its old payload with nothing on screen but its age, and for Home's two
new users that old payload states something false.** The default `held()` is "the previous payload unchanged":
- **Picks** (`APPROVED_PICKS`, `home_blocks.py:47`): the previous payload is `fno_state: {approved: false, note:
  <no approved strategy>}`, `rows: []`. Held from the first approval, the page keeps saying **no strategy is
  approved**, which is exactly "the empty panel that is no longer true" this stop exists to prevent (its own message,
  `home_blocks.py:15-17`).
- **Books and risk** (`OPEN_TRADE_RISK`, `:32`): the previous payload carries each book's value, P&L, `approved: []`
  and `limit_used: 0.0`. Held while a trade is open, the page shows **no risk used** and the pre-trade value as the
  latest, for as long as the trade is open, typically weeks.

Freshness shows the age, but a small "as of" beside "risk used ₹0" is not the owner's "say so on screen" principle
(row 236), which the orchestrator extended to these users ("the same principle"). Response 244's own point 2 says it:
"a hold hides a page's staleness only behind its freshness label".

**Fix (in the text):** require that every held page says so on screen, not only by its age. Either:
- (a) each user's block supplies `held()` with a notice and without the stale claims (for example, picks:
  `fno_state.approved` true or unknown with the rule as its note; books: `limit_used` not shown as 0); or
- (b) one generic notice: the dashboard reads the held pages from the run status (or a page-level field) and shows
  "<page> held back: <rule>" on any held page. That is a W3/W12 change and a contract field, named as a dependency
  with its order (before P2b, P2c or the first approval).

Add a criterion: for each user, the screen of a held page shows that it is held, and no held payload asserts a figure
or state that the rule says is no longer true (test per user).

**Note:** a hold that outlives a contract version bump would re-file a payload of the older `schema_version`. State
whether the publication validates held copies against the current pin, and what happens if one fails (I expect a
whole-run stop, which is correct, but the text should say so).

## Addendum 1: head efba832e (the should-fix fixed, both options taken)

**PASS.** `git diff 89fe464a efba832e` touches only the P11 text and response 244 addendum 3.
- **(b) The generic notice:** every publication carries the page `page_holds` (`[{page_key, since, rule}]`, empty on
  a normal day), and the dashboard shows "<page> held back since <since>: <rule>". `FnoPageHolds` (screens lead) and
  the W3 rendering are named dependencies, ordered before P2b's and P2c's rebase and before the first approval.
- **(a) Per block:**
  - Shown unchanged when the old payload stays true for its own session: the Forecast lab and the paper books.
  - Dropped (`None`, no row) when it would state something the rule denies: Home's picks ("no approved strategy")
    and Home's books ("limit_used 0").
  - The card uses `withheld`.
- **My note:** a held copy is validated against the current pin, gets no row if it fails (never a whole-run stop),
  and the alert line says why (criterion 10).
- **Criterion 9:** per user, the screen says the page is held and no held payload asserts a state the rule denies.

**Notes for the code round:**
- P11's own code publishes `page_holds`, so `FnoPageHolds` must be in the pinned contract before P11's code merges.
  Otherwise the new page fails `ContractBroken` and stops the run. Put that order in Depends (today's line names
  P6-P10, P7 and the alert sender only).
- `page_holds` itself must never be held (a failure there is a whole-run stop). Say so, and test it.
- `since` is the first held session of the current run of holds. A test should cover a hold that lifts and comes
  back (a new `since`).

## Addendum 2: text at d2190217 (judge 255's alignment)

**PASS (text only).**
- The card's reason is now digit-free: "A risk rule was broken: the risk sizing or the validity check let a trade past
  its book's per-trade cap".
- Every reason is stated as digit-free against `FnoPageHolds.reason` (`^[^0-9]*$`), with a test against the pinned
  pattern.
- The keys are the contract's (`holds[{page_key, since, reason, shows}]`).
- Depends now names "`FnoPageHolds` pinned before this code merges" (my note 1).

The code on this branch (response 244 addendum 4) is judged separately, when it is sent with 2.13.0 pinned. The
other two notes (page_holds never held; `since` resets after a lift) are for that round.
