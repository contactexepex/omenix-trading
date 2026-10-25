# Judge 261: R1a code, idea cards, G0 registration, gate log, trial k of K (judge G)

- **Judged:** `story/r1a-records` at `29a0707a`. Code `e74df3aa`, plus `6b8cc7b1` (a test that B0's card agrees with
  its playbook `edge_family`), plus merges of main. The orchestrator gave the go at `4c5370c6`, and the builder
  replaced it with `29a0707a`, whose only non-merge change is that test. Builder: session 01XFXpbkyixX7SuXeQCp5EnX.
  Lane 1. Text: judge 259 PASS. 261 was the next free number on main.
- **Verdict: PASS.** I caught 13 of my 14 mutations; the survivor is a path that has already run once, and I checked its
  output by hand. I rule on the two open choices below, and there are 3 notes.

## What I ran

- **Gates:** ruff check, ruff format and `check_imports` are clean. Full suite in a worktree of `4c5370c6`: **7,232
  passed**. At `29a0707a`, `tests/factory tests/research tests/playbook` give 482 passed (the builder reports 7,233 for
  the full suite).
- **Real output:** `python -m fno factory report` prints "55 trials in the ledger; expected false passes at 0.01
  one-sided: 0.53 (53 trials; measurement trials left out: 54, 55)", then B0, FT1 and R2, each with "trial k of 55"
  and "last gate G0 idea ... (back-filled)".
- **The back-filled rows, checked against git:** 53 at `1d76c75f`, 54 at `245934ab` and 55 at `496e74fd`. Each commit
  adds that trial's ledger row, each is on main, and the dates match the ledger's `registered_on`.

## Criteria (R1a's part)

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 1 | One command registers. The ledger row goes through B4 and the `idea` row is logged. A missing or malformed field is refused with its name, and nothing is written | `IdeaRegistration.register` checks everything before writing: no other staged files, append-only log, no gate row yet, trial id not in the ledger, card path not registered, trial = next number. It then calls `Ledger.register`, with the hypothesis taken **from the card** (judge 259 note 2). Mutations caught: the hypothesis forced yes, the next-number check, the staged check, the duplicate-path check, the existing-row check, unknown fields, and the id against the file name | MET |
| 2 | The guard refuses an edit or deletion | It reuses D1's `rewritten_history` over git versions plus the working file. Caught: guard off, working file left out, and the `numbers` pattern off | MET |
| 3 | trial k of K follows the ledger's order and count; expected false passes = K × α | `TrialCount` uses ledger order. My `int(trial_id)` mutation fails 2 tests. For false passes, see choice (b) | MET |
| 9 | B4, D1, R3 and S1 unchanged | No file of theirs changes. `LEDGER.md` gains B0's missing row and a count of 55, and a test ties that count to the ledger | MET |
| 10 (R1a's part) | A measurement counts in K but not in the false passes | B0 and FT1 are left out of the 0.53 and listed by name. Removing that subtraction fails a test | MET |

## The two open choices (the orchestrator left them to me)

- **(a) The block holds G0 fields only: accepted** (reasoning only).
  - R2's frequency is "measured by the study", and FT1 has no trades, so requiring G1-G3 inputs at G0 would force
    invented numbers.
  - Unknown fields are refused, so R1b must add those fields deliberately.
  - **Condition for R1b:** the G1-G3 inputs are required when `screen`, `spend` or `plan` runs. A card lacking them
    is refused by name there, never given a default.
- **(b) FT1 counts as a measurement in the expected false passes: accepted** (reasoning only, with the record as
  evidence).
  - FT1's ledger row has hypothesis `no`, and both its card and its row call it an exploratory measurement with no
    pass mark. It cannot produce a false pass.
  - Leaving R2 and the controls in, which follows FACTORY_RULES' "53 trials" example, overstates the expected false
    passes. That errs on the strict side, and is right.
  - The card's `measurement` flag is needed for trials that have no playbook version. For B0, the new test ties it to
    `edge_family`, so the playbook stays the one source where a version exists.

## Notes

1. **The back-fill's commit choice is untested** (`first_commit_containing("\n<id>,", ledger)`). My mutation using
   `head()` instead survives. The back-fill has run once, and no hand-registered card remains, so the three committed
   rows, which I verified, are the only output. No fix is needed. If back-fill is ever reused, pin the commit in a
   test.
2. **`register --on <date>` can back-date a trial's `registered_on`.** The ledger is the record that an idea was
   registered before its results, so a past date weakens it. It is not a normal path, since the default is today, and
   B4's `Ledger.register` allows the same. A one-line refusal of any date other than today would close it. It can go
   with R1b.
3. FT1's line reads "(measurement: never promoted)". "Never promoted" fits shadows, but FT1 is a study. The wording is
   harmless and can change when R1c labels shadows.
