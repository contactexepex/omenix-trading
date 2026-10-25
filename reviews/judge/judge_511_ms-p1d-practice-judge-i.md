# Judge 511: MS-P1d part 4, practice quote rules (design A) (second judge)

**Scope:** story/ms-p1d-practice at fb7e67ba (on the law order 2de9c037, with a3 round 2 696f2db7 merged), diff
2de9c037..fb7e67ba. Judge I (session_01MvZneCLZqBuiGyNxawdVee), the second judge (money piece); Judge B passed it
(488.6), and I did not read that verdict. Lane 1. Round 1 of 2.

**Verdict: PASS.** No finding.

## Checked against design A (orchestrator: sizes stay None; only a practice-flagged rule maps them at E4; without it the fill is refused; a sentinel is a FAIL)
| Point | Result | Evidence |
|---|---|---|
| No sentinel in the data | MET | an unmeasured `SlotQuote` keeps `None` sizes (a3's `__post_init__`). The mapping happens only in `QuoteRules.sizes` at the E4 boundary (`execution_snapshot`): practice gives no limit, live gives none. No 10**9 or waiver constant exists |
| Live refuses by name | MET | `LIVE` names the refusal `size_not_measured` in the gate and in `SchoolFills.enter`; a3's `check_fill_port_unmeasured` runs on the real port (`test_the_live_port_passes_a3s_unmeasured_check`). Plants caught: `LIVE` built as practice, the live check returning False, live sizes set to no limit, the gate's naming dropped |
| Only the practice roots build practice rules | MET | `QuoteRules` is keyword-only; the isolation scan over `fno/` refuses `QuoteRules(...)` outside `quote_rules.py` and the two practice roots. Plants caught: a practice rule built in, and imported into, the live `build_fill_port` |
| Practice says it did not test the size | MET | `PRACTICE_SIZE_NOTE` on the size and sell-back laws when they passed an unmeasured size; plant (note dropped) caught |
| Nothing records an unlimited size | MET | `FilledLeg` and E4's `FillMaker` keep no size, so the practice mapping never reaches a record |
| Gates | MET | full `pytest -n auto` 12,875 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean |

## Plants
7 planted, 7 caught.

## Notes (no action required)
- a3's merge-order condition is met here: the real `SchoolFills` with `LIVE` passes `check_fill_port_unmeasured`.
- b's quality gate and the drivers still treat an unmeasured quote as two-sided. The fake fleet closes such a road live, but j's real fleet must do the same (judge 506's note).
