# Judge 61: story P10, Home's F&O read models

Date: 13 Oct 2026 (UTC). Claims: `reviews/claude/response_66_2026-10-13-p7-p8-p9-publishing.md`, addendum P10
(65a4930). The India band, session and `fno_expiry` events were stopped by the builder because W10 names the stock
tool as their publisher: **blocked by owner / contract owner**, not a failure.

## Verdict: PASS on the built criteria; one cross-repository defect must be settled before Home can show them

## Per criterion

| # | Criterion | My check | Result |
|---|---|---|---|
| 1 | FnoBooks from each book's own account, Rs 5 lakh before opening, approved = frozen experiment's passing policies, limit from C2, never example values | Read `home_inputs.py`: each book's `PaperAccount`, equity rows on or before the session, opening balance otherwise. Planted "read every row, even after the session": caught. Approvals read from `results_challenge.json` `overall.passing_policies` | MET |
| 2 | FnoPicks empty state with the reason | Note read from the result file ("passed no policy") | MET |
| 3 | Validate against pinned W10 schemas; same transaction and run status as P6 | Tests pass; same publisher path as P9 | MET |
| 4 | A book with an open trade stops the run | Planted `if False:` for the open-trade check: caught | MET |
| 5 | Size, lint, imports, tests | Files small; full suite at ea4459f: 1,702 passed; ruff and imports clean (my run) | MET |

## The cross-repository defect (must be settled; the contract owner decides the names)

| Block | W10's `x-read-model` | P10 publishes | Dashboard W9-F&O reads |
|---|---|---|---|
| FnoPicks | `fno.pages_history page today (P1)` | `fno_picks` | `today` |
| FnoBooks | `pages risk and scoreboard_b (P1)` | `fno_books` | `risk` |

The two builders chose different keys and neither saw the other's choice. As built, the dashboard's reader finds
no `today` or `risk` page and shows "page missing" for both, although P10 published them. For picks the contract is
plain (`today`), so P10 departs from it, and its response did not say so (it raised only the books key). For books the
contract names two pages for one block, so it is ambiguous. One side changes; the contract owner should also replace
"proposed" or "P1" notes with the real keys.

## Claims vs reality

| Claim | Reality |
|---|---|
| "Today's truth: all three books at Rs 5,00,000, pnl 0, nothing approved, no risk used" | Consistent with the code and with experiment 1's result (judge 56: no policy passes) |
| "The only route by which a strategy becomes approved" is the frozen experiment's passing list | This is the story's rule. Note: the results file path is wired to experiment 1 in `fno/market_read_models/wiring.py`; a later experiment needs that line changed, or "approved" will stay on the old result |
| P6's pages byte-identical after P7-P10 | Not re-run by me (Drive, about 3 min). Not verified |

## Project rules

New behaviour in new classes; composition root wiring; no example values. Clean.

## Addendum 1 (re-judge of 8cf2584): page keys now `today` and `risk`

`home_blocks.py` now publishes FnoPicks as `today` (W10's `x-read-model`) and FnoBooks as `risk`, the keys the dashboard
reads; the served schemas stay `FnoPicksResponse` and `FnoBooksResponse`, validated against the pinned W10 copy
(`tests/market_read_models`: 116 passed, my run). The contract still says "risk and scoreboard_b" for books until its
owner reduces it to `risk`, as the orchestrator says is in hand. Verdict: **PASS**, the key defect closed on this side.
The end-to-end check (judge 63) waits for the next publish.
