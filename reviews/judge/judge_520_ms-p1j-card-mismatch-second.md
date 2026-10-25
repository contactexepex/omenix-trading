# Judge 520: MS-P1j follow-up, a comparison card mismatch is loud (second judge)

**Scope:** story/ms-p1j-card-mismatch at 4aa043df (builder session_01CmKJ6taCLzfEGg7wt6RC4N), two commits on `main`.
Story MS-market-school.md, "MS-P1j follow-up: a comparison card mismatch is loud". Lane 1. Second judge; I wrote this
without reading Judge B's 507.7. Round 1 of 2. Judge K (session_019ZApRwkUiNMKDsf1k4W44z).

**Verdict: PASS.** 1 minor.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Each sealed decision is put to h's `CountingRule`; any `comparison_card_mismatch` gives one line, that cause only | MET | `card_check.py`. Plant "any not-counted reason" caught |
| 2 | "N of M" names the mismatched count | MET | plant N = M caught |
| 3 | `school run` exits 1 on a warning; the line is printed | MET | both CLI plants caught |
| 4 | First run and rerun both checked | MET | both runner plants caught |
| 5 | The record root wires the check; a replay has none | MET | wiring plant caught; `no_check` is the default in `fleet_on` and the replay root passes nothing |
| 6 | The card's version in the line | MET | version-parser plant caught |
| 7 | No record changes; counts only in the line | MET | the line holds two counts and a version number; `SessionRun` refuses warnings on a run that did not run |
| - | Gates | MET | pytest -n auto 13,807 passed, 16 xfailed. ruff check and format, check_imports and check_records are clean |

## Minor
- Judging at `"HEAD"` instead of `seal.commit` survives (`card_check.py`, the `CountCandidate`). A rerun after the D6
  rows land would then judge against the newer history. It would stay silent about decisions that, by D6's ancestor
  rule, still do not count. Add a test with a D6 row committed after the seal and a rerun. Counting itself is h's rule,
  applied elsewhere, so this affects only the alert.

## Plants
9 planted, 8 caught; the survivor is the minor.

## Addendum 1: ca847210

**PASS, minor closed.** 4aa043df..ca847210 is test-only:
`test_rows_registered_after_the_seal_never_clear_the_decisions_it_sealed`, on real git. With my `"HEAD"` plant it
fails (1 failed, 6 passed); without it, 7 passed. ruff check and format are clean.

## Addendum 2: the merge tip d0a9c2bf

**PASS** (second judge). 59401687 merges `main` again, after sim-seams (54ef5d40, 1f767528); d0a9c2bf is a one-line
test fix (`build_fleet` now reads `school.enabled` first).
- Against current `main`, the tip differs only by the card-check feature: `card_check.py`, the runner's
  `card_check` field and warnings, `fleet_on(card_check)`, `build_card_check` in the record root's `build_fleet` (after
  its `SwitchedOff` branch), and the CLI's warnings and exit 1. `git merge-tree` with current `main`: clean.
- My 9 round-1 plants were re-run on this tip: 9 of 9 caught.
- **Gates (my run):** pytest -n auto 13,999 passed, 16 xfailed. ruff check and format, check_imports and
  check_records are clean.
