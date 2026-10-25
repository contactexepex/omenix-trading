# Judge 271: R1c code, research questions, G4 freeze, G6 cumulative Holm verdict, RegisteredShadows (judge G)

- **Judged:** `story/r1c-shadows` at `0e4f10d7`: R1c commit `0f7aa48c` on top of R1b `9a20155a`, plus a merge of main.
  Builder: session 01XFXpbkyixX7SuXeQCp5EnX. Lane 1, because it touches evaluation records, S1's `frozen_files` and
  BG1's tracker. Judged under the orchestrator's standing go for R1. 271 was the next free number on main.
- **Verdict: FAIL.** Two rule gaps in G6, each on a path that normal running reaches, and one test gap in criterion 8.
  The rest is right and simple, and 7 of my 10 mutations are caught.

## What I ran

- **Gates:** ruff check, ruff format and `check_imports` are clean. `tests/factory tests/budget tests/evaluation`: 331
  passed. The builder reports the full suite as 7,451 passed and 3 failed; the 3 are main's own risk tests, which I
  confirmed in judge 266 addendum 1.
- **Real state:** `python -m fno factory shadows` prints "no registered shadow yet (Test B's R1 input is missing)".

## What is right (strong evidence, code read and tests)

- **Questions:** `questions.csv` is append-only through the shared `AppendOnlyCsv`, so there is one guard. The id is a
  slug, alpha must lie in (0, 0.5), and duplicates are refused (my mutation is caught).
- **G4 freeze:**
  - It runs only after G3, so a `screened_out` idea is never frozen.
  - The card's pass level must equal its question's alpha (mutation caught).
  - A measurement is refused by `is_measurement` on the playbook file, the one source R3 keeps (mutation caught).
  - It writes HEAD into the empty `protocol_commit` the way S1's `freeze.py` does, so B4's columns are untouched.
- **G6:**
  - It takes the first n positions only (my "all positions" mutation is caught).
  - The family is every G4 row on the question (my "only itself" mutation is caught).
  - A verdict is refused before the frozen sample (mutation caught).
  - Holm comes from `uncertainty.holm`.
  - The planted family is right: 0.004 among 19 members at p = 1 fails at 5%.
- **StrategyNets** reads E6's `strategy_records` for that version only (mutation caught). **RegisteredShadows** lists
  the G4 rows, and BG1's `present` callable makes R1's input present only once a shadow is registered, not merely
  because `gates.csv` exists.
- **Agreements with R3, BG1 and S1** are as the builder states. Dropping the DecisionStore read is right: the frozen
  sample is completed positions, so decisions do not enter p.

## Findings

### Should fix

1. **Positions opened before the freeze count towards the verdict** (FACTORY_RULES section 3, rule 1: "Records made
   before that commit never count").
   - `StrategyNets.nets` returns every completed position of the account, and the verdict uses the first n.
   - R3's step 3 lets the desk register the playbook version `research` (which opens the shadow account) as soon as
     G1 passes. G2, G3 and G4 then run later, by command.
   - So a shadow can trade for days or weeks before G4. Its early positions would be among the first n, and whoever
     runs `freeze` may have seen them first. That is the peeking the rule exists to stop.
   - **Fix:** count only positions opened after the G4 row's commit or date (for example `opened_on >` the G4 date),
     and say so in the verdict's numbers. Add a test with one pre-freeze winner that must not count.
2. **An `exploratory` idea can log G6 `passed`.** FACTORY_RULES section 4: a test on `spent` or `exposed` data "is
   labelled exploratory and cannot pass G6".
   - G3 accepts G2 `fresh` or `exploratory`, G4 accepts any G3 outcome, and `ShadowVerdicts.judge` never reads the G2
     row.
   - An idea whose measured quantity reads exposed data (for example India VIX 2017-2026, `exposed` in DATA_SPEND)
     would get `passed` written to the gate log. Section 3 rule 7 and the second-test rule both then read it as a pass.
   - **Fix:** when the trial's G2 outcome is `exploratory`, the verdict logs a non-pass, for example `failed` with
     `exploratory=yes`, or a distinct outcome. Its p is still recorded and it stays in the family. Add a test.
3. **Criterion 8's "a member short of its sample enters with p = 1" is not pinned.**
   - My mutation computing p from a short member's partial positions survives (237 passed), because the planted
     members have fewer than 2 positions, which gives p = 1 either way.
   - The rule matters in normal running. Other shadows on the same question will be part-way with early results, and
     Holm's step-down loosens the judged shadow's threshold when other p values are small.
   - My mutation of the t test's degrees of freedom (n instead of n − 1) also survives, so p has no known-answer test.
   - **Fix (tests):** a short member with at least 2 strongly positive partial nets must still enter at p = 1. Add one
     known-answer p from a hand-computed t, for example n = 5.

### Notes

1. **Refreezing is untested:** my mutation dropping the "already frozen" refusal survives. That path needs a second
   `freeze` on an already registered trial, which G3-then-G4 ordering already blocks. Pin it if convenient.
2. **The miss share is not reported until E6b's counter merges.** This is stated openly in Known limits, and accepted.
3. **No shadow positions exist until E8 part 1b and R3 part B merge,** so no verdict can fire yet. The should-fixes
   are about records that do not exist yet. They are cheapest to fix now, before the first G4 row is written.

## Addendum 1: `136b77c4` (judge G)

**Verdict: PASS.** The fix `1b572e51` reached me from the builder under the orchestrator's standing go for R1. It
includes `b6ab34c0`'s S1 constants pin test.

- **Should-fix 1 is accepted.**
  - `ShadowResults.nets(account, opened_after)` now counts only positions with `opened_on` after the G4 row's date, so
    the freeze day itself is excluded. That is conservative: the G4 row is written before its commit.
  - G6's numbers carry `opened_after`.
  - Both my mutations, `>=` and dropping the filter, fail a test.
- **Should-fix 2 is accepted.** `passed = holm_passed and not exploratory`. An exploratory trial is logged `failed`
  with `exploratory=yes`, and its p stays in the family. Ignoring the flag fails a test.
- **Should-fix 3 is accepted.**
  - A short member with 9 strongly positive nets enters at p = 1, and my partial-p mutation now fails.
  - The known answer is right: I recomputed nets 1..5 with `t_cdf` as t = 4.2426, df 4, p = 0.0066178. My df = n
    mutation now fails 2 tests.
- **Note 1 is done.** Refreezing is refused both ways, and dropping the "already frozen" refusal fails a test.
- **Gates:** ruff check, ruff format and `check_imports` are clean. Full suite in a worktree of `136b77c4`: **7,464
  passed, 0 failed** (main's risk fix is now merged in).
