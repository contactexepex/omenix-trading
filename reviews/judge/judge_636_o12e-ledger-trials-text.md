# Judge 636: O12e, ledger trial numbers claimed in blocks, story text round 1

Branch `story/o12e-ledger-trials` at `cf62172e4` (section "O12e" of `docs/stories/O12-number-claims.md`, register
row). **FAIL, lane 1** (3 should-fix, 1 minor). Text only; judge session 01BvZZzF4XR48qNHNxLydQhf.

## Criteria

| Item | Verdict | Evidence |
|---|---|---|
| Seeded history equals main's `research/ledger.csv` | MET | my script on main: 108 rows, ids 1-108, no gaps, no duplicates, no non-numeric id; the runs of one experiment are exactly the 16 named (1, 2-17, ..., 100, 101-108) |
| Every path registers inside a claimed block | NOT MET | findings 1 and 3 |
| The Book 3 exemption is safe | NOT MET | finding 2 |
| A full block | MET | the freeze and `register` refuse it; a new block is claimed (criteria 3-5) |
| No write-once record edited | MET as designed, but finding 1 leaves one half-written | the design adds `numbers/` rows and a pin only; `ledger.csv` rows are not changed |
| Doc-reading tests and number check | MET | 932 passed, 13 xfailed; `check_numbers`: clean; only Markdown changed |

## Findings

1. **Should fix: a refused freeze leaves its write-once record behind.** `Freeze.freeze` writes `FREEZE_v<n>.md`
   (`fno/evaluation/freeze.py:160`) before `_register` (line 161). With the new rule ("refused when there is no block"),
   a refused freeze leaves the file on disk, and every retry is refused at line 152 ("exists: a change is a new
   protocol version"). Fix: the text says the trial id is chosen (or refused) before anything is written; add that
   to criterion 5, plus a plant that moves the choice back after the write.
2. **Should fix: the exemption covers every non-numeric id, not only Book 3's.** The text exempts "ids that are not
   whole numbers". `ledger.py` checks no id format (`read_ledger` 141-150, `register` 170-181), so `x109` or
   `edge2:1` would bypass both the guard and the check. Fix: exempt exactly `book3:<strategy_id>` with Book 3's own
   experiment (`book3/registry.py:95`, `TRIAL_FAMILY`). Any other non-numeric id is refused by `register` and flagged
   by the check. Add this to criteria 1 and 4.
3. **Should fix: a trial typed by hand into the ledger still runs outside a block until the merge.** The known limits
   say the check catches a hand-typed id "on the next push". But `checks.yml:10-14` runs only on pushes to `main` and on
   pull requests, and `require_committed` (`ledger.py:183-197`), the gate every run passes, needs only a local commit.
   The latest collision was itself hand-written: the v4 freeze's rows 101-108 came in commit 4c7187c8c with no code
   writing them. So a branch can still run on ids that clash with another branch, which is the failure O12e exists to
   stop. Fix: put the block check in `require_committed` too, for numeric ids not in the seed (or state why not, with
   the owner's acceptance). Add a criterion and a plant. Also reword "every writer goes through it": hand edits do not.
4. Minor: "the experiment starts with the block's name" lets block `edge2-f1` cover `edge2-f10-...`. Require the
   name itself or the name followed by `-`. Test both.

## Plants

None (text round). The text's own plant list should add: the choice made after the freeze file is written (1); a
non-`book3:` non-numeric id accepted (2); the run gate without the block check (3).

## Notes

- Who claimed a block cannot be proven: this is stated plainly in the text, and the claim tool's race handling is
  unchanged from O12.
- 115-120 `edge2-f6` is reserved by the orchestrator, not by a builder. That is fine, since F6's experiment must
  start `edge2-f6`.

## Addendum 1: round 2 (the last), text and code, head `cb6ceb79b` (judge 1 of 2)

**PASS, lane 1.** No blocking or should-fix finding left.

| Item | Verdict | Evidence |
|---|---|---|
| Round-1 finding 1, freeze writes before choosing | FIXED | `freeze.py` `_claimed_trial` runs before `path.write_text`. My plant (the choice moved after the write) fails `test_the_evaluation_freeze_without_a_free_id_in_its_block_is_refused_before_writing` (2 cases) |
| Round-1 finding 2, too wide an exemption | FIXED | `blocks.py` `is_book3`: `book3:\S+` only under `book3_ai strategies` (= `TRIAL_FAMILY`, `book3/registry.py:30`); ids must match `[1-9]\d*`. Plants R1 (any experiment) and R2 (leading zero) caught |
| Round-1 finding 3, hand-typed rows | FIXED | `require_committed` applies `TrialClaims.problem`. Plant R5 caught (`test_a_row_typed_by_hand_outside_its_block_never_runs`) |
| Round-1 finding 4, prefix boundary | FIXED | `Block.is_for`: the name itself or the name + `-`. Plant R4 caught |
| Seeds equal main's ledger | MET | trial merge with main: the 16 `existing` rows equal my recomputed runs of `research/ledger.csv` exactly (108 rows); `check_numbers`: clean |
| No write-once record edited | MET | `research/ledger.csv` has no diff against main; `seed_pins.json` adds `ledger-trial` and keeps the four pins as they were; the registry only gains rows |
| Every existing trial still runs | MET | `require_committed` on all 108 rows of the merged tree: 0 refusals |
| Criterion 7, the factory | MET | `registration.py` `_next_claimed`; plant R6 (`next_free` crossing blocks) caught by 8 tests |
| Claim tool | MET | plant R8 (block start ignoring ledger ids) caught; plant R7 (overlap check off) caught |
| Test changes | MET | `P1`/`P2`/`P9` renamed to claimed whole numbers, experiments renamed; no assertion removed or loosened |

**Gates (trial merge with main, clean):** ruff, format, imports, check_records and check_numbers clean; full suite
16786 passed, 13 xfailed, 0 failed. **Plants:** 8, all caught.

**Notes (not findings):**
- The guard reads the checkout's own `numbers/ledger-trial.csv`. A block row added by hand on a branch, never
  claimed on `main`, passes there until the merge, where an overlap is flagged or git conflicts on the registry. This
  is the same residual as O12's review numbers.
- The 121-126 `edge2-f8` reservation sits after 115-120 with no overlap.

## Addendum 2: round 3 (granted by the owner, 25 Oct), head `1f680b2c1` (judge 1 of 2)

**PASS, lane 1.** This round answers judge 644's S1 and m1. I judged the code and text myself and did not read 644.

| Item | Verdict | Evidence |
|---|---|---|
| Claims read as git holds them | MET | `TrialClaims` takes `Git.committed_text` (HEAD) and `Git.is_clean`. Every `problem` and `next_free` refuses while `numbers/ledger-trial.csv` has a local change, untracked included (`git status --porcelain`). Plants: never dirty (2 tests), `git diff` in place of status, which misses untracked (1 test), the dirty check dropped from `problem` (2) and from `next_free` (1): all caught. The registry read from the working tree breaks 66 tests (caught, if crudely) |
| m1, a block committed only on a branch | MET (text) | Known limits now say plainly that such a block passes that branch's guard until `main`'s check at the merge, so the claim tool is the only safe way to get a block |
| Seeds and claims against main's ledger | MET | main's `ledger.csv` now runs 1-127. Blocks: 16 seeds (1-108) plus 109-114 `edge2-f1-weekly-vrp-gate`, 115-120 `edge2-f6`, 121-123 `edge2-f8`, 124-127 `edge2-f9`; every trial on main sits in its own block. `check_numbers` on the trial merge: clean |
| No write-once record edited | MET | the narrowed f8 row and the moved f9 row exist only on this branch (no `numbers/ledger-trial.csv` on main yet); `research/ledger.csv` has no diff against main |
| One owning document (owner, 25 Oct) | MET | `numbers/README.md` gives the command and links the O12e section; `research/LEDGER.md` points to the story. `O12-number-claims.md` is 281 lines (under 500) |

**Gates (trial merge with main, clean):** ruff, format, imports, check_records and check_numbers clean; full suite
17625 passed, 13 xfailed, 0 failed. **Plants:** 5, all caught.
