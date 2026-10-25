# Judge 259: R1, the factory's code (gates, gate log, cost wall, data spend, sample plan, trial count), story text (judge G)

- **Judged:** `story/r1-factory-text` at `86368061`. The orchestrator named `43404e8c`. The head adds `7769a81c` (the
  orchestrator's two answers and the dated `FACTORY_RULES.md` correction) and a merge of main, whose only docs change
  is O8's story, outside R1. Builder: session 01XFXpbkyixX7SuXeQCp5EnX. Lane 1. The orchestrator gave the go. 259 was
  the next free number on main.
- **Verdict: PASS (text).** No must-fix and no should-fix. There are 4 notes for R1a and R1b.

## The orchestrator's points

1. **The worked example's figures are correct** (strong evidence: I recomputed them with
   `fno/forecast_v4/student_t.py` `t_cdf`, inverted by bisection).

   | n | mean | SD | cost | t(0.90, n-1) | bound | net on the bound | net on the mean | ratio |
   |---|---|---|---|---|---|---|---|---|
   | 33 | +978 | 2,667 | 824 | 1.3086 | +370.48 | **-453.52** | +154 | 1.19 |
   | 57 | +408 | 3,403 | 814 | 1.2969 | -176.54 | **-990.54** | -406 | 0.50 |

   - The inputs match `response_92:38-39`.
   - The old paragraph in `FACTORY_RULES.md` used the means, against its own rule (the lower one-sided 90% bound for
     a measured distribution). So the condor is `screened_out` on both periods, not only the holdout.
   - The correction is dated and labelled, the old paragraph is kept, and criterion 4 pins the figures. Right.
2. **The boundary with R3 holds.** R1 never opens accounts: G4 stops at `registered`, and the owner's
   `playbook set-status` moves a version to `research`. R1 never reads closed trades for Test B: R3's criterion 12
   gives those, and `money_test` joins them with R1's `RegisteredShadows`.
   - The `ShadowResults` adapter filters R3's records by `mode`, never by file name. That matches R3 part A's
     `record_file` prefix and review 132's known limit.
   - It reads nets only after E2c's download, which matches R3's criterion 12.
   - R3's hand cost-wall step is replaced in the same change that merges `CostWall`, so the hand step and the code
     never both apply. The R3 register row records the agreement.
3. **B0 is excluded by `is_measurement`.** It counts in K but never in a Holm family, the expected false passes or
   `RegisteredShadows` (criterion 10 plants a measurement at p = 0.001). Moving `measurement.py` into the frozen files
   when R1's Holm first decides with it matches judge A's condition, as it stands on main.
4. **The orchestrator's two answers are sound** (reasoning only).
   - `gates.csv` stays in the repository: it holds trial status, not market values, like `ledger.csv`.
   - z is each idea's registered one-sided pass level, which ties G3's sample to G6's test.

## Other checks

- **No duplicate:** no `CostWall`, `TrialCount` or "trial k of K" exists in `fno/`. The only cost-wall mention is a
  budget item's text. No other story text defines them.
- **B4 is untouched:** `read_ledger` refuses any column beyond its ten (`ledger.py:23,72`), so a gate log beside it is
  the simplest design that keeps every writer (freeze.py and the study packages) working. R1 only calls
  `Ledger.register` and `require_registered`.
- **The rules followed:**
  - G1's formula (conservative bound − round-trip cost − tail beyond the gross);
  - the 2x warning only;
  - the assumed hurdle never passing G1;
  - G3's 3-year limit to `exploratory_shadow`;
  - cumulative Holm per question, with stopped or short shadows at p = 1 (conservative: Holm ranks them last, and the
    survivor still faces alpha/m);
  - all match `FACTORY_RULES.md` sections 2-4.
- **Reuse:**
  - C1's charges, A4's half-spreads, `uncertainty.holm` and `student_t.t_cdf`, with no third t table;
  - the context claim that `research/LEDGER.md` says 54 while the ledger has 55 rows is true.
- **Staging** in three judged M rounds is right for an L story.

## Notes

1. **Criterion 4 against `CostWall`'s cost:** the design computes cost from C1 charges and pads per leg, but the worked
   example gives only a round-trip cost (824 and 814), with no legs. R1b's test either feeds that cost as a stated
   input, or the card schema needs a "measured round-trip cost with source" case. Say which in R1b, so the test
   exercises the real `CostWall` path rather than a parallel formula.
2. **G0's hypothesis flag** is fixed to `yes`. A measurement or exploratory card registered through R1 later (B0 was
   registered `no` by hand) needs the flag from the card. One field in the block is enough.
3. **`research/LEDGER.md` says 54 trials**, but the ledger has 55 rows (B0's row is missing). It is a one-line
   research-record fix for its owner, independent of R1. R1a's `report` could print the ledger's count, so the hand
   count is no longer needed.
4. **The back-filled `idea` rows** for R2, FT1 and B0 must not record a gate those cards never passed by code. Only
   `idea`, labelled back-filled, as the text says. R1b's re-screen then reports differences and never rewrites the
   hand screens. I will check that in R1a and R1b.
