# Judge 195: G10 part 2, the stored moved-after-cutoff flag: `story/g10-flag` 50c2a610 (lane 1)

Judge B. A16/G8 builder. The commit is stacked on `story/g10-build` 638cf54c (judge 189 addendum 2). It answers judge
189 part-2 item 1, as the orchestrator approved: store the flag and its sign only, never a level.

## Checks
- **The rule.** `cutoff_flag(levels, x)` returns ("yes" / "no" / "", "+" / "-" / "0") from the 14:30 and 15:15 levels
  (the `terms` constants). It uses the strict `> X` rule and gives "" when either level is missing. `marks()` are IST
  datetimes, so `mark.time()` keys match the IST constants.
- **A16.** `SessionRv` takes the flag function by injection, and `intraday/wiring.py` binds it to the frozen
  `MOVED_AFTER_CUTOFF_X`.
  - The levels are the same `index_check` readings as the RV (`zip(..., strict=True)` with the marks).
  - The two columns are added to the live `RvTable` only. A16b's `CandleRvTable` keeps its fields.
  - `rv_session`, `method` and `inputs_sha256` are unchanged, so V1's pin (judge 177 addendum 4) stands, and
    `write_once` still compares `method` and `inputs_sha256` only.
  - Old rows have no column and are read with `.get`.
- **G8.** `RecordedCutoffMoves` reads the committed rows. The Drive reader is gone, so the weekly report needs no
  Drive (closes judge 189 item 1) and re-runs give the same counts.
- **Privacy.** Only a yes/no flag and a direction sign are committed, never a level. This matches the orchestrator's
  approved rule.
- **My plants.**
  - The sign with `>=` (a flat move shown as "+"): 1 test fails.
  - The builder's three plants are claimed caught: "" written, "" read as "no", and `>=` for `>`.
  - Dropping the injection in `intraday/wiring.py` (`cutoff=v4_cutoff_flag` removed) fails no test. See note 1.
- **Gates on 50c2a610, run myself:** **6,319 passed, 0 failed**. Ruff is clean. Intraday, scoring and v4 tests: 418
  passed.

## Notes (not blocking)
1. The composition-root binding (`cutoff=v4_cutoff_flag`) is untested, and `intraday/wiring.py` is not byte-checked
   at the freeze. A later edit that drops it would make every live day "flag not computable". That is visible in every
   report's day counts, not silent, so this is a note only. A one-line test that `v4_cutoff_flag` is what the recorder
   gets would close it.
2. This changes `session_rv.py` and `rv_table.py`. `session_rv.py` is in the freeze's byte-checked set, so merge
   **before** the v4 freeze commit (response 157 notes it).

**Verdict: PASS for 50c2a610.** Merge it after `story/g10-build`, before the freeze.

## Addendum 1 (15 Oct 2026): 5a40c69d / 617f5b93

The 50c2a610..5a40c69d diff is one added assertion in `tests/intraday/test_cli_and_wiring.py`:
`recorder.session_rv.cutoff is wiring.v4_cutoff_flag`. It closes note 1, and the builder reports that dropping
`cutoff=` fails it. 617f5b93 only merges `main`. Suite on 617f5b93 with `-n auto`: **6,521 passed, 0 failed**.
**PASS for 617f5b93.**
