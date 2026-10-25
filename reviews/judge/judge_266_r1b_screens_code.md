# Judge 266: R1b code, the screens (CostWall, DataSpend, SamplePlan, gate steps) (judge G)

- **Judged:** `story/r1b-screens` at `532c5e07`. Code `3305eabc`, plus R2's screen row and record `7d0edc76`, plus a
  merge of main. Builder: session 01XFXpbkyixX7SuXeQCp5EnX. Lane 1. Text: judge 259 PASS; R1a: judge 261 PASS. Judged
  under the orchestrator's standing go for R1. 266 was the next free number on main.
- **Verdict: FAIL.** The code is correct, and 16 of my 19 mutations are caught. One should-fix: the 3-year limit of
  criterion 7 is not pinned at its value. There are also 4 notes and 3 rulings.

## What I ran

- **Gates:** ruff check, ruff format and `check_imports` are clean. Full suite in a worktree of `532c5e07`: **7,327
  passed, 0 failed**.
- **Real output:** `fno factory report` still prints 55 trials and 0.53. B0 and FT1 now read "(measurement)", per
  judge 261 note 3.
- **R2's G1 row:** `53,G1,screened_out,2026-10-16,3305eabc...,reason=no_stated_edge;assumed_hurdle=yes`. It is
  appended after the G0 row, and the log is still append-only.

## Criteria (R1b's part)

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 4 | The worked example | `test_cost_wall.py` runs the real `MeasuredGross` → `StatedCost` → `screen` path: t 1.3086 and 1.2969, bounds +370.5 and −176.5, nets −453.5 and −990.5, ratios 1.19 and 0.50, both `screened_out` and thin margin. It matches my judge 259 recomputation. Caught: net on the mean, tail dropped, df = n, the 2x flag at 1 | MET |
| 5 | No source gives "no stated edge"; a cost-hurdle study never passes G1 | `NoStatedEdge.edge()` returns None, so `screened_out` happens before any cost, with the `assumed hurdle` label. R2's real row shows it | MET (note 2) |
| 6 | spent or exposed gives exploratory, with rows named | `data_spend` parses DATA_SPEND's register table and refuses unknown rows by name. Caught: the spent-only rule, `registered` always fresh, and unknown rows accepted | MET |
| 7 | SamplePlan's n and time; above 3 years, `exploratory_shadow` only | n = ⌈(z·SD/net)²⌉, z = Φ⁻¹(1 − level), net taken from the G1 row. n = 2,165 at SD 3,000, net 150, 1% (I checked it by hand: 2.3263 × 20 = 46.53, squared 2,164.7). My two-sided z mutation is caught. **The limit is not pinned** (should-fix 1) | partly |
| Judge 261 condition | G1-G3 inputs required at their gate, refused by name, no defaults | `inputs.py` reads each section only when its gate runs, and every field goes through `Fields`, which refuses a missing field by name. When an edge is stated, cost and tail are required | MET |
| Judge 259 note 1 | Stated cost against leg cost | `StatedCost` (measured plus source) or `LegsCost` (C1's `order_charges` / `settlement_charges_breakdown` plus pad × units per order). Caught: the exit pad dropped, and the closing side made equal to the opening side | MET |
| Gate order | Each gate once, in order, card committed, measurement never screened | `GateSteps._ready`. Caught: the measurement check, the uncommitted-card check, the staged-file check, and G2 allowed after a screened-out G1 | MET |

## Findings

### Should fix

1. **Criterion 7's 3-year limit is not pinned at its value** (quality rule 5, boundary cases).
   - `test_the_sample_plan` uses frequencies of 1,000 (2.2 years) and 12 (180 years). Any limit between 2.2 and 180
     years passes it: my mutation `years >= 30` survives, and so would changing `PLAN_YEARS_LIMIT` to 5 or 10.
   - The limit decides the common case. At about 12 trades a year (every monthly NIFTY idea), plans of 3-30 years
     are typical. A drifted limit would label a 5-year plan `planned` instead of `exploratory_shadow`. That changes
     what G4 may register and what G6 may later judge.
   - **Fix (tests only):** pin the limit's value and its boundary. A plan of exactly 3.0 years is `planned` (the rule
     says "above"), and one just over 3 years is `exploratory_shadow`.

### Notes

1. **G1's zero boundary is untested.** My mutation `net >= 0` passes survives, but the rule says "at or below zero
   gives `screened_out`". Exactly 0.0 is rare with measured inputs, but possible with stated whole numbers (bound =
   cost, tail 0). One line can join should-fix 1's test.
2. **"An assumed hurdle needs no cost or tail" is untested.** My mutation requiring cost and tail for
   `assumed_hurdle` survives (only `none` was exempted). R2's committed row shows the right behaviour today. A card
   test with `kind: assumed_hurdle` and no cost or tail section would pin the claim.
3. **R2's card gained its `gross` block after its hand result was known.** That is allowed here: the outcome ("no
   stated edge") depends on no number, so no input can tune it towards a pass. Any future re-screen whose outcome
   depends on numbers must be a new idea (FACTORY_RULES section 2). `RESCREEN_R1b.md` reports the reason difference
   openly, which is right.
4. **Not built, stated openly:** the IV-point edge per vega (input 4), and physical-settlement costs. The second can
   bite: a stock-option card using `legs` with `settlement` would get cash-settlement charges, which understate
   physical delivery. Until C1 has a physical charge, refuse `settlement` legs for stock options, or require a stated
   cost for them. Do it with the first stock-option card at the latest.

## Rulings (asked by the builder)

- **`registered` is fresh only for the trial its Used-by cell names: accepted.** DATA_SPEND defines `registered` as
  "a frozen protocol will read it". A second test reading it first would expose it before the reserving test runs. So
  it is exploratory for anyone else, and the strict reading is the safe one.
- **Tail extra = (max(card, family) − card if in_gross else 0) × loss: accepted** (reasoning only). It applies
  "the worse of the two", and subtracts only what a measured gross already contains. When the gross is not measured,
  the whole expected tail loss is subtracted, which the rule requires.
- **The gate log's per-gate outcomes (GATE_OUTCOMES) and judge 261 notes 1-3 are done.** The back-fill test now
  catches my `head()` mutation from judge 261; the builder states this and I did not re-plant it.

## Addendum 1: `9a20155a` (judge G)

**Verdict: PASS.** The fix reached me from the builder under the orchestrator's standing go for R1. The fix commit
`9a20155a` changes `fno/factory/inputs.py`, three test files and `TEMPLATE.md`. `f94a4b92` before it adds one clause
to R3's step 3, plus merges of main.

- **Should-fix 1 is accepted.** `test_the_three_year_limit_is_exact` checks 3.0 years → `planned` and 3.0001 →
  `exploratory_shadow`, through both `SamplePlan` and `sample_plan`. Each of these now fails a test: my `years >= 30`
  mutation, a `>= PLAN_YEARS_LIMIT` mutation, and setting the constant to 5.0.
- **Notes 1, 2 and 4 are done, each caught by my re-planted mutation.** Net = 0 now gives `screened_out` (the `>= 0`
  mutation fails). `assumed_hurdle`, like `none`, needs no cost or tail (exempting `none` only fails). A leg now
  states `instrument`, and a `stock_option` leg with `settlement` is refused by name (dropping the refusal fails).
- **R3 step 3's clause** ("a research version only for a card whose G1 passed, or a measurement") matches
  FACTORY_RULES section 3, rule 2. It says openly that D1's `set-status` does not enforce it. R3's owner agreed.
- **Gates:** ruff check and ruff format are clean; factory tests: 90 passed. Full suite at `9a20155a`: **7,385 passed,
  3 failed**. The 3 failures fail identically on `origin/main` (`b576230a`) alone:
  - `tests/risk/test_manager.py`, twice (the 30-day factor tests);
  - `tests/risk/test_stress_factor.py::test_the_repository_seed_row_is_read_by_c2_and_c4`.
  They follow today's A14c data commit to `research/data/margins/stress_factor.csv`. They are not R1b's, and are
  reported to the orchestrator separately.
