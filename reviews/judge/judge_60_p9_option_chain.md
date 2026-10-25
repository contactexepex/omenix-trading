# Judge 60: story P9, NIFTY option chain read models (screen 32)

Date: 13 Oct 2026 (UTC). Claims: `reviews/claude/response_66_2026-10-13-p7-p8-p9-publishing.md`, addendum P9.

## Verdict: PASS (with three minor points and one owner cost decision)

## Per criterion

| # | Criterion | My check | Result |
|---|---|---|---|
| 1 | For 12 Oct every chain block equals W13's example field by field | The offline equality test (`tests/market_read_models/test_chain.py`, on the 307 KB fixture cut) passes. Plants: max pain by `max` instead of `min` caught; the chance N(d2) with call and put swapped caught. I did not re-run the real Drive `market compare` (3 min, Drive access): that part rests on the fixture test | MET |
| 2 | Every payload validates; a planted break fails the run | Validation tests pass; the earlier P6 break tests still refuse the whole publication | MET |
| 3 | Same transaction and run status as P6 | Chain blocks are in `build_market_blocks()`, published by the same `PostgresPublisher`; one run row | MET |
| 4 | Size, lint, imports, tests | Largest chain file 130 lines; full suite at ea4459f: 1,702 passed; ruff and imports clean (my run) | MET |

## Claims vs reality

| Claim | Reality |
|---|---|
| ATM strike: "a tie goes to the lower strike" | Code does this, but **no test has a tie**: my plant (tie to the higher strike) passed all 6 chain tests. Minor; a one-line fixture test |
| IV searched in 1%-200%, else no IV, Greeks or chance | Code matches (`bounded_iv` returns None outside the bracket). Time is calendar days / 365, no dividend yield: the mockup's convention, so equality holds, but it is not the B1 trading-day convention. State it on screen 32 if both appear |
| Page keys | W13's contract calls them proposed: `chain_contract:<code>` and `chain_rows:<expiry>`. P9 publishes `contract_history:<code>` and `chain_rows:<expiry>:<near/band/all>`. Not wrong (proposed names), but the dashboard route must use P9's keys, and W13's note should be updated by its owner |
| `chain_sources.books` | Fixed text, true today; must come from the books' state once a book can hold a position (builder says so) |
| Storage about 1.5 MB a session, about 1 GB a year in `pages_history` | Not measured by me; plausible from page counts. Owner decision (retention job, near-money contract histories only, or accept) |

## Project rules

No AI at runtime; contract copies pinned; chain math reuses `fno/analytics.py`; no secret in files. Clean.

## Addendum 1 (re-judge of 8cf2584): the ATM tie is now tested

My same plant (a tie goes to the higher strike) now fails 1 of 7 chain tests. Restored; `tests/market_read_models`:
116 passed. The W13 key differences are listed in the response for the contract owner. Verdict unchanged: **PASS**.
