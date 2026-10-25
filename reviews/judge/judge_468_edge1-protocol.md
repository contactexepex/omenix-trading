# Judge 468: EDGE1 protocol draft (story/edge1-build at ea268f3a), round 1 of 2

Judge B, 22 Oct 2026. Short-report rule (DESK_DECISIONS row 294).

## Verdict: FAIL (1 should-fix)

## Checked and right

- **§2, status.** Every result is exploratory, both reasons are given (the data is spent, and GR1 foresaw the
  direction), and the known-before variants are named (experiment 1's P1 and P2).
- **§3, the seal.** Run 1 reads at most January 2023's closes, for its December 2022 exits, and says so. Run 2 is
  opened once, on the same cycles for all 12 variants.
- **§3, weeklies left out.** The narrowing is justified: the engine's cycles are monthly, every NIFTY weekly is
  spent, and BANKNIFTY's weeklies ended.
- **§5, the widths.** BANKNIFTY's are NIFTY's list times 3, fixed now.
- **§6, the arithmetic.** SL2's mark of at least 3 x the credit is a 2x loss, and TP50's mark of at most 0.5 x the
  credit is half earned. Both are checked on fully traded days only.
- **§7.** The untraded-leg rules from judges 467 and 467.2, word for word.
- **§8, lots.** The circular wins any disagreement.
- **§9, costs and margin.** Today's STT is the decided figure. The historical rates are marked reasoning only and
  checked in the build. The margin build gate is in.
- **§10, G1.** R1's CostWall on run 1, with at least 20 trades.
- **§11, the test.** The re-centred one-sided p, Holm, and the four-part nomination rule, including all trades
  positive at both pads.

## Should-fix 1: the bootstrap block of 20 is 20 months here

§11 uses G4's `resampled_means` with **block 20** over trades in date order. G4's 20 is 20 sessions of daily data.
EDGE1's unit is one monthly trade, and the trades do not overlap: each decision falls 30-45 days before an expiry and
the T21 exit 21 days before it, so one trade's exit comes before the next decision.

The story's own pass rule (judge 467) says "block bootstrap **by month**".

**The normal path:** run 2 has about 45 cycles, and fewer after the not-taken trades. With L = 20:
- there are 26 possible block starts;
- each resample joins 3 blocks;
- so the "bootstrap" is close to resampling 3 overlapping 20-month windows. The null distribution is lumpy, its
  variance is badly estimated, and the p-value is unreliable in either direction.

**Fix.** Set the block to the unit:
- block length 1 trade (a month), or 2-3 if you want some allowance for serial dependence, stated with the reason;
- through G4's same function, with its `block` argument (or the same moving-block code with L passed in), and the
  seed rule unchanged.

## Notes (one line each)

1. **Expected count.** At about 45 run-2 cycles with every-leg-traded entries, several BANKNIFTY variants may fall
   below the 40-trade minimum (p = 1). Print the expected count per variant from run 1's fill rates before run 2.
2. **Holm spans both indices.** "Every variant run 2 tests" covers both indices; say so explicitly in §11.

## Plants

None: this round is text only. The code and freeze come next.

## Addendum 1: revision 1 at 7910539d, round 2 of 2 (number 468.1, claimed with `tools/claim_number.py`)

**FAIL: one claim in the fix is wrong for EXP. The fix is mechanical.** Under row 294, the orchestrator now takes
both sides to the owner.

**Met:**
- the block length is passed in as 1 trade through G4's code, with G4's default of 20 kept for other callers;
- the 30-trade floor is fine, marked reasoning only;
- Holm is one family across both indices;
- run 1 prints the expected run-2 counts with no price read.

**The wrong claim:** "the trades are monthly and never overlap (each exits at T21, EXP or earlier, before the next
cycle's decision)". This is true for T21, SL2 and TP50. It is **false for EXP.**
- The next cycle's decision is the first day its expiry is 30-45 days away. For a 27 Feb 2025 expiry that is about
  13 Jan 2025.
- The January EXP trade is held until its expiry on 30 Jan 2025.
- T21's January exit is about 9 Jan, before 13 Jan, so T21 trades do not overlap.

Consecutive EXP trades therefore overlap by about two weeks of a roughly 45-day hold, and they share index moves. A
block of 1 understates their variance, so EXP's p-values come out too small and more of them would be nominated.

**Fix (one line):** use a block of 2 trades for EXP variants, which covers adjacent overlap only; or 2 for every
variant, for simplicity. Correct the text's reason.

## Addendum 2: revision 1b at 835d8677 (number 468.2, claimed with `tools/claim_number.py`)

**PASS.** This is the exact fix 468.1 recommended, so nothing is left in dispute and no owner decision is needed.

| Item | Result |
|---|---|
| The block | 2 trades for every variant, through G4's code with the default unchanged |
| The reason in the text | corrected: T21, SL2 and TP50 exit before the next decision; EXP trades overlap by about two weeks |
| The floor | 30 trades, or 15 blocks |
| Commit f84dcca7 | only wraps lines |

Next: the code and the freeze, before registration and run 1.

## Addendum 3: revision 2 at 4277fba5, the owner's Q1 and Q2 answers (number 468.3, claimed with `tools/claim_number.py`)

**PASS. The protocol is ready to freeze**, together with the analysis code, as GR1 was.

**Matches DESK_DECISIONS row 295 (22 Oct):**
- **Q1, "also measure".** 4 measurements: NS, the naked strangle, and NT, the naked straddle, T21 exit only, per
  index.
  - They are labelled "not tradeable under the house rules", and they sit outside both the pass family and the Holm
    family.
  - They are never nominated without an owner rule change.
  - The report shows their worst loss per trade and per lot, uncapped, and the margin each would need.
  - Their ledger rows carry `hypothesis` no.
- **Q2.** Screen and nominate.

**The engine is untouched.** `require_covered` stays as it is. The naked legs are built by a research-only structure
in `research/edge1/`, never added to the engine's tradable list. Section 7's fill, untraded-leg and pad rules apply
to them unchanged.

**One note.** In each measurement's report row, show the largest realised loss next to Rs 10,000, so the owner sees
by how much the house cap would have been breached.

**Next:** the code and the freeze. I check them before registration and run 1.

## Addendum 4

**Scope:** EDGE1 protocol revision 3 (story/edge1-build at 1896d9b3, sections 3, 9 and 14), a set of changes made
before the freeze. Under the orchestrator's instruction I opened no new round on points already settled.

**Verdict: PASS.** Nothing blocking, nothing to fix.

**Checked:**
- **Seal (section 3).** 31 Dec 2022 + 45 days = 14 Feb 2023, correct. A decision day falls 30-45 days before expiry,
  so run 1's last cycle is the January 2023 expiry (25 Jan, decided 11-26 Dec 2022). The February expiry (23 Feb) is
  decided in January 2023, inside run 2. `cycles_of(..., expiry_by=RUN1_SEAL)` therefore drops no run-1 cycle.
  `inputs.markets(through=)` cuts the rows before any panel is built, and `run1` seals the panel again
  (`runner.sealed`).
- **Historical STT (section 9).** Premium 0.05% to 31 Mar 2023, 0.0625% to 30 Sep 2024, 0.1% to 31 Mar 2026, then
  0.15%. Exercise 0.125%, then 0.15% from 1 Apr 2026. These match the Finance Acts' dates as I know them, and the
  0.15% matches `config.yaml`. Every order is charged at its own trade date's rate. The results are reported as
  `pad1_stt_history` and never decided on.
- **Exchange charge, stated but not modelled.** I re-did the arithmetic for the worst case, a spread whose bought
  legs cost as much as its sold legs:
  - under-charge: at most 0.018% × 2 sides × (sold + bought premium) = 0.072% of sold premium;
  - over-charge on STT: 0.10% of sold premium before Apr 2023, 0.0875% from Apr 2023 to Sep 2024.
  
  The over-charge is larger in every window, so "the decided run stays conservative overall" holds per trade, not
  only on average.
- **Margin label.** "calculator only, unchecked" is honest: `margins.csv` comes from the same calculator, so it
  cannot check it. Margin is not a pass condition, so the old build gate's removal changes no decision.

**Gates (partial, for the protocol only):** `tests/research_edge1` passed, 38 of 38, at 1896d9b3. The full gates run
on the code verdict.

**Plants:**
- **STT date moved one day** (1 Apr 2023 → 2 Apr 2023): caught by
  `test_the_schedule_changes_on_each_acts_first_day`.
- **The seal's session filter loosened by 30 days** (`runner.sealed`): **not caught.** Both run tests still passed.
  It is not a protocol defect. For the code verdict, a test must show that a session after RUN1_SEAL never reaches
  run 1: the panel's sessions, not only its option prices.

**Note:** the runner docstring says run 1's cycles expire "by early February 2023". That is the 45-day upper bound;
the real last expiry is 25 Jan 2023. It is wording only.

**Next:** the code, the mutation proof and FREEZE.md, judged before registration and run 1.
