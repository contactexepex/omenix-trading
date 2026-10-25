# Judge 495: R1 follow-up, cards anywhere

**Scope:** story/r1-cards-anywhere at 6fcbd6dc (one commit on main). The story's "R1 follow-up: cards anywhere" section
in `docs/stories/R-factory.md` and its Claims. Lane 1 (research records). Round 1 of 2. Judge H
(session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: PASS**, with 2 minor notes.

## Criteria
| Check | Result | Evidence |
|---|---|---|
| Ideas folder first, unchanged | MET | `card_paths.card_path`; plant (ideas lookup removed) caught |
| Else the ledger row's `protocol_path` if it holds a ```factory block | MET | Every protocol path on main's ledger holds no block (my scan of all 37 paths), so none is mistaken for a card. Plant (block check removed) caught |
| A named card that can't be read is an error | MET | `read_card` raises, including the id-versus-file-name check (`card.py:58`); test plus plant (stem match removed) caught |
| `factory report` lists CARD_P1 as a measurement | MET | On 6fcbd6dc merged with the registration branch 8106871b (scratch only): `CARD_P1 v2 (measurement): trial 99 of 99`, `measurement trials left out: 54, 55, 95, 96, 97, 98, 99`, false passes over 92 trials. `factory status CARD_P1` finds it. The real-report test then runs and passes |
| Gates | MET | On the merged tree: pytest -n auto 11,183 passed, 1 skipped, 16 xfailed. ruff check/format, check_imports and check_records are clean. `card_paths.py` is 43 lines |

## Findings
None blocking or should-fix.

**Minor:**
- (a) **A missing ledger-named card is ignored, not refused.** If the ledger names a card that is no longer there,
  for example `research/school/CARD_P1.md` moved, `ledger_card_paths` drops it silently (a test asserts it). The
  report then counts trial 99 as a test again, one more expected false pass, with no error. Every ledger path exists
  today. A ledger-named `.md` that is missing could fail `factory report` instead.
- (b) **One id found in two places is read twice.** `card_path` prefers the ideas folder, but `read_all_ideas`
  returns both cards: my run, with X1 in ideas and `research/school/X1.md` named by the ledger, gives `[X1, MEAS, X1]`.
  It needs a misconfiguration (two cards with one id). `all_card_paths` could refuse a duplicate id.

## Plants
6 planted, 5 caught. The survivor drops the ideas-folder exclusion in `ledger_card_paths`. It is equivalent, because
the set union in `all_card_paths` removes the duplicate path.

## Notes
- Merge order, as the orchestrator says: registration (judge 493) first. Until then the trial-99 report test skips.

## Addendum 1

**Re-check:** story/r1-cards-anywhere at 47fe7f97. The branch's own diff against main (the registration is already
on main) covers `card_paths.py`, `counting.py`, `registration/wiring.py`, ledger row 99 and the tests. **Verdict:
PASS.** Lane 1.

**Gates (my run):** pytest -n auto: 11,198 passed, 1 skipped, 16 xfailed. ruff check/format, check_imports and
check_records are clean. `factory report` lists 99 among the measurements left out.

**CountingRule, `comparison_card_mismatch` (judge 493 note b): ACCEPTED.**
- A decision counts only if its D6 row's `comparison_card_sha256` equals the SHA-256 of `CARD_P1.md` at the card
  version in force (`counting.py`).
- A row without the component, or a card nobody committed (empty hash), doesn't count.
- On the real tree, the card in force (0c0f1b24) hashes to `15ee4ab5...`, the value in all 12 rows. The real rule on
  CS1 at HEAD says `no_first_counted_session`, as designed.
- Plants caught: the check removed, the hash taken at the decision's commit instead of the card version's, the
  driver-card SHA read in place of the comparison SHA.
- **Consequence, correctly stated in the story's Claims:** any later card version (including the one the HEAD
  charges test forces on a fee change) counts only after new D6 rows naming it are registered. Until then decisions
  are `comparison_card_mismatch`, which fails closed. j's runbook should name that step.

**Ledger row 99 (note a): ACCEPTED.** `protocol_commit` is 0c0f1b24. That is the card's last change on this tip, and
a test pins it.

**Judge 495 minors: ACCEPTED.**
- (a) A ledger-named `.md` missing from the repository raises `CardError` by name.
- (b) An id found in the ideas folder and elsewhere is returned once, with the ideas folder winning.
- New: two cards elsewhere with one id raise.
- All three plants caught.

**Minor:** `card_sha256_at`'s empty string for a missing card is load-bearing only when a row also lacks the
component. Replacing it with `None` survived. A test with both missing would pin it.

**Plants:** 7, 6 caught, 1 survived (the minor).
