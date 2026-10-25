# Judge 493: MS-P1h registration (card v2, D6 rows, trial 99)

**Scope:** story/ms-p1-card-registration at 8106871b. The diff runs from its merge-base with main to 8106871b: card v2,
the 12 driver cards frozen, 12 D6 rows, ledger trial 99, LEDGER.md, DATA_SPEND, and the ledger guard. Lane 1
(evaluation records). Round 1 of 2. Judge H (session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: PASS**, with 2 minor notes.

## Criteria
| Check | Result | Evidence |
|---|---|---|
| `band_steps` in a driver card never changes a trade | MET | Nothing reads the field except the loader (`drivers/cards.py:29`; no other hit in `fno/`). I set all 12 cards to 3, then to 99: all 138 driver tests (exact-decision oracles) pass both ways. Strikes and wings come from each card's own parameters |
| 12 driver cards frozen | MET | `band_steps: 10` on every card (it was 0 to 40). The DRAFT line is replaced. Changing CS1's band to 11 fails 4 registration tests |
| 12 D6 rows | MET | Every `card_sha256` equals my SHA-256 of its card file. `comparison_card_sha256` `15ee4ab5...` equals CARD_P1 as of `registered_in_commit` b1f9ef70 and at HEAD. `python -m fno versions check` lists all 12 |
| Rows are registered after the cards and card v2 | MET | Cards 0deda30b, then card v2 0c0f1b24, then `registered_in_commit` b1f9ef70, then rows c0c2775d (a test checks each card's text at the registering commit) |
| Real counting run | MET | At HEAD, `D6VersionLookup` returns CS1's frozen SHA, and the rule says `no_first_counted_session` (as designed until the gate passes) |
| Card v2 §6 (expiry-day ELM priced) | MET | Part m is merged with judges 491.1 and 492.1 PASS (SEBI 2024/132 para 5.6). The text says v1's claim no longer holds |
| Trial 99 in ledger, gates.csv, LEDGER.md, DATA_SPEND; guard 1..99 | MET | Ledger row: prospective, hypothesis no, `protocol_path` the card; G0 `idea`; LEDGER total is 99. DATA_SPEND's `registered` is in that file's own vocabulary |
| Gates | MET | pytest -n auto: 11,171 passed, 1 skipped, 16 xfailed. ruff, check_imports and check_records are clean |

## Findings
None blocking or should-fix.

**Minor (notes):**
- (a) The ledger row has empty `protocol_commit`, `first_run_on` and `run_commit`. That is consistent with the
  orchestrator's known open item (`factory register` reads only `research/ideas/`). The R1 fix should fill
  `protocol_commit` with the card v2 commit.
- (b) `comparison_card_sha256` is recorded but no code checks it. Counting uses the card version in force by git, so
  the component is a record only. A v3 card would make it historic, not wrong. Say so in the card's §1, or leave it.
- DATA_SPEND names the NIFTY weekly under both the A4 row (99) and the new A4c/A4f row. That is harmless duplication.

## Plants
- 3 band values: 3, 99 and 11 (as an edit). The first two never change a decision; the edit is caught by the
  registration tests.
- The card files and the CARD_P1 hash were recomputed by hand.
