# Judge 69: story D2, rule evaluation and allocation (branch `story/d2-rule-evaluation` 7d4b59e, before merge)

Date: 14 Oct 2026. Claims: `reviews/claude/response_72_d2-rule-evaluation.md` on the branch. (The E7 builder's
`response_72_e7` clashes with this number; one must be renumbered.)

## Verdict: FAIL, one must-fix: the desk's impossible-price rule differs from the research it trades on

## Gates (branch tip, separate worktree)

- `tests/playbook`: 234 passed.
- Full suite: 2,216 passed. Ruff and imports are clean.

## Per criterion

| # | Criterion | Check | Result |
|---|---|---|---|
| 1 | One condition unmet: no fire, recorded | Tests (number below threshold, unknown value, flag); the builder's mutation caught | MET |
| 2 | Two candidates, one slot: higher expected net per rupee of risk wins, the other "not chosen: slot" | Tests, including higher raw net but lower score losing. **Gap:** my plant swapping the tie order (expiry before maximum loss) passes all 234 tests. Only the name tie is tested | MET (tie order partly tested; should fix) |
| 3 | Negative expected net: no trade | Tests at -50 and exactly 0 | MET |
| 4 | Unproven strategy with one open trade: a second refused | Tests at 19 and 20 completed. The count is **per version**: a new version starts unproven again. That is stricter than per name, so there is no loophole (reasoning only) | MET |

## Must-fix: impossible prices (the orchestrator's question 3)

**Research (experiment 1, PROTOCOL.md "Impossible prices", `simulator._entry_trial`):** a width whose entry prices
put the position at or beyond its payoff bounds is `bad_prices` and is **skipped like an unlisted width**; the next
width is tried. That covers a trade that cannot lose (short credit at least the width, long debit at most 0) **and** a
trade that cannot win (long debit at least the width, short credit at most 0).

**Desk (D2 `candidates.py`):**
- only "maximum loss at most 0", the cannot-lose half, is caught;
- it then **stops the opportunity** instead of trying the next width;
- the cannot-win case is not checked at all, so the desk would trade a width the research refused.

**Why it matters:** `expected_net_per_opportunity`, the number D2 ranks by, comes from research run under the
research's convention. A desk that stops where research skipped (missed trades), or trades what research refused
(cannot-win entries), no longer trades what was tested.

**Which side changes: the desk.** Reuse the research's payoff-bounds test (`payoff_bounds` and `position_value` from
`fno/research_engine`) and skip the width, as research does. The story text ("a zero or negative value is a validity
failure") should then be amended to say "an impossible-price width is skipped, as in the research", with the owner's
or the orchestrator's sign-off. The research results are frozen evidence; the desk is the new code. Add a test for
each case: cannot lose, cannot win, and a narrower width that is tradable after a bad wider one.

## The orchestrator's other questions

1. **A misconfigured shadow never affects Book 1: MET for this code.** Book 1 is allocated first, against its own book,
   and returns outcomes only (no writes). Each shadow version is allocated alone against its own `ShadowBooks` book. A
   shadow book named like a real book, or like Book 1's, is refused. The builder's byte-identical test and the
   "shadow uses Book 1's book" mutation both hold. A shadow book with another name is trusted to be separate; the
   `ShadowBooks` implementation (E side) must prove that when it is built.
2. **Ranking, ties, unproven limit:** as in the table. The tie order should get a test with equal scores and different
   maximum losses.

## Limits stated by the builder, which I accept as limits (not met yet, and not D2's fault)

There is no real-day run. C2's `Market` from the A4 snapshot and the trade counts come with E2 and E5. The story's
"judge verifies" (re-run a day from its decision record) waits for D3.

## Project rules

New modules behind interfaces; constants in `fno/constants.py`; files under 110 lines. Clean.

## Addendum 1 (re-judge of branch 5acb188, fix 2852655): PASS. The builder may merge

**Must-fix closed.** `candidates.py` now uses the research's own `payoff_bounds` and `position_value`. A width whose
entry prices put the position at or beyond its payoff bounds (cannot lose or cannot win) is **skipped** and the next
width tried, as in experiment 1. The story line was amended. My plants, each caught:

| Plant | Result |
|---|---|
| Only the lower bound checked (cannot-win allowed) | 1 failed |
| A bad width stops the opportunity instead of being skipped | 2 failed |
| Tie order swapped (expiry before maximum loss), my earlier gap | now 1 failed |
| The "shadow folder above a real book's folder" check removed | 1 failed |

**Shadow storage guard:** `RealBooks.overlap` refuses a shadow account named like a real book, or stored in, inside or
above a real book's folder. Paths are resolved, so `..` and symlinks are handled. The folder is declared by the
`ShadowBooks` implementation, so that implementation (E side) must write only there. Note it in that story's
criteria.

**Gates at the branch tip, in a separate worktree:**
- `tests/playbook`: 244 passed.
- Full suite: 2,238 passed. Ruff and imports are clean.

**After the merge** I check that `main` equals this tip plus a clean merge and that CI is green.

## Addendum 2 (merge check, 662784f)

**MET.** 662784f has parents 0d44276 (main) and 5acb188 (the passed tip). I recomputed the merge of the two:
the only difference from 662784f is `reviews/claude/README.md`, the index conflict the builder resolved by hand. No
code differs. CI `checks` on 662784f (run 38497390532) and on the next commit e1ec07e (run 38497427804) are green.
My full suite on main at e1ec07e: 2,253 passed; ruff and imports are clean.
