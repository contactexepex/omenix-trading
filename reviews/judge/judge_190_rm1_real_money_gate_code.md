# Judge 190: RM1 real-money gate, code round (judge A)

**Checked:** `story/rm1-real-money-gate` at `d1805788`, against the text I passed (judge 171 addenda 4-5). The claims
are in response 163 §9. The changed files are:
- new: `fno/evaluation/gate.py`, `tests/evaluation/test_real_money_gate.py`;
- changed: `completeness.py`, `freeze.py`, `cli.py`, `tests/evaluation/builders.py`, `test_freeze.py`;
- `research/evaluation/PROTOCOL.md` `frozen_files`, plus one sentence in the gate's `fill_honesty`.

**Verdict: PASS.** There are no blocking and no should-fix findings, and three notes below.

## Criteria

| # | Criterion (RM1) | Result | Evidence |
|---|---|---|---|
| 1 | Exact rule for every 8.3/8.4 element | MET | Text passed (171 add. 4-5). `GATE_ITEMS` has the same 12 keys, and the test asserts the parsed set equals it |
| 2 | `check` reports the gate and rejects bad items | MET | My run on the trial merge prints "PROTOCOL.md version 1: complete" and "REAL_MONEY_GATE.md: complete". `--decided` lists S1's 13 undecided items, then "REAL_MONEY_GATE.md: complete and decided". The tests name a bad label, a bad status, "to be decided", "TBD", a missing item and an empty Reason |
| 3 | The freeze refuses an undecided gate and writes nothing | MET | `test_an_undecided_gate_refuses_the_freeze_and_writes_nothing` checks that no record exists and the ledger is unchanged |
| 4 | Gate hash in `FREEZE_v<n>.md`; `verify` flags a later edit | MET | `test_a_decided_gate_is_hashed_…`: a Rs 5,000 to Rs 6,000 edit shows as changed |
| 5 | Owner numbers before the freeze | MET | Enforced by `_require_gate(decided=True)`; the committed gate is decided (rows on main) |
| 6 | Gate terms (Book 1 after the freeze, quote-based slippage, registered sample) | MET | Text unchanged from 04a80222 except the per-position sentence (note 2) |
| 7 | Never an order; no broker import | MET | `fno/evaluation/` imports none of providers, desk, books, broker, groww or orders (AST test). `gate.py` only parses and checks text. No code path reads the gate to act |
| 8 | 350 lines; `freeze.py` one class | MET | `freeze.py` is 189 lines, `cli.py` 111, `gate.py` 36, the test 137 |

## S1 unchanged (asked)

- **MET.** `completeness_problems` keeps S1's defaults (`REQUIRED_ITEMS`, `versioned=True`), so every S1 call is
  identical. The 44 earlier S1 tests in `tests/evaluation` pass.
- Two fixture changes are needed and correct:
  - `builders.py` puts the committed gate in the temporary repository and in its small `frozen_files`;
  - `test_freeze.py`'s exact hash set gains the gate.
- The real `PROTOCOL.md` `frozen_files` adds the two gate files, with the date in the Reason, so the decided Status
  stays parseable. This is the owner's Q10 "Yes, one freeze", and S1's text owner approved the wording.
- `_require_gate` runs before `_require_committed`. A working-tree gate that is decided but uncommitted still
  refuses, and a test covers it.

## Broken-code proofs (my plants on d1805788, `tests/evaluation`, 61 pass unplanted)

| Plant | Result |
|---|---|
| M1 the freeze never calls `_require_gate` | 2 fail |
| M2 `gate_problems` ignores "decided" | 3 fail |
| M4 the freeze checks the gate for completeness only (`decided=False`) | 1 fails |
| M3 `_check` ignores the gate in its exit code (still prints it) | **0 fail** (note 1) |

## Gates

Gates on the trial merge with origin/main a4459572 (tree 3787164; `WORK_REGISTER.md` merged automatically):
- pytest: 6138 passed and 3 failed;
- `ruff check`: clean;
- `ruff format --check`: 1129 files formatted;
- `check_imports`: clean.

The 3 failures are main's own, the same 3 as on a723840d (judge 186):
- `test_paper_account` and `test_home_blocks`: E2c step 3 removed the committed accounts;
- `test_committed_closes_reproduce_the_disclosed_v6_counts`: 2409 against 2410.

None is in RM1's files. The orchestrator's message said 2. It is 3 on main today.

## Notes (one line each, no fix asked)

1. `check`'s exit code on a failed gate is untested (plant M3 survives). Nothing runs `evaluation check` for its exit
   code (no workflow or tool calls it), and the freeze is the binding guard, which M1, M2 and M4 prove. A one-line
   test would close it.
2. `fill_honesty` (b) now takes one gap per position (my addendum 4 note), but the floor still says "fewer than 20
   legs with a next snapshot". Counting in positions as well would be consistent. The change came after the owner's
   2026-10-15 decision. It only makes the bound honest and changes no owner number. Tell the owner in one line when
   the gate is next shown.
3. After this merges, S1's real freeze also needs the gate decided, which it is, so C5 holds. S1's 13 undecided
   items still block it first, as intended.

## Addendum 1: follow-up at `story/rm1b-gate-followup` 6c167ce4: PASS

The delta d1805788..6c167ce4 touches 3 files: the gate's `fill_honesty` (b), one test, and response 163.

- **Note 1: MET.** The new `test_the_check_command_exits_failed_when_only_the_gate_fails` replaces `_check_gate` with
  a stand-in that always fails and asserts `_check` returns `EXIT_FAILED` on the complete real protocol. My plant M3
  (the exit code ignores the gate) now fails 1 test, where it failed none before. `tests/evaluation` has 62 tests,
  and all pass unplanted.
- **Note 2: MET.** The minimum now counts positions: "fewer than 20 positions with a gap is not met". A leg with no
  next snapshot is left out of its position's mean, and a position with no such leg is left out. Both are listed.
  This matches the per-position bound. It is stricter than 20 legs, since a two-leg position counts once, and that
  only makes the gate harder to pass. The owner should hear it in one line when the gate is next shown, with the
  per-position change of d1805788.

**Gates on the trial merge with origin/main 453de57c (tree 8a7e79b, clean auto-merge):**
- pytest: 6314 passed, 0 failed;
- `ruff check`: clean;
- `ruff format --check`: 1131 files formatted;
- `check_imports`: clean.

**Verdict: PASS.**
