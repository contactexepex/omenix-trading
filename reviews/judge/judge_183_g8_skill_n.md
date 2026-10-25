# Judge 183: G8 skill_n display fix: `story/g8-skill-n` 84dbb4d2 (lane 1, forecast scoring report)

Judge B. A16/G8 builder. It answers LR1's devil's-advocate objection L13: "v6_ewma_t4 n 2158 vs base rate n 1908" read
as an unpaired comparison. Two files change: `fno/forecast_scoring/v4/scores.py` and its test.

## Checks
- **The skill was already paired** (checked). `scoring._scores` builds `base` only from the forecaster's scored days
  where the base rate exists, and `probability_scores` computes the skill on those pairs. The change adds no new
  computation: `ProbabilityScores.skill_n = len(base_pairs)`, the days the skill uses.
- **Printed in both outputs.** `render.py` prints scores through `asdict` in the text report (line 83) and the JSON
  (line 61), so the new field appears in both with no other change. `ProbabilityScores` is built in one place only
  (checked by grep).
- **The test, recomputed by hand.** Three scored days and a base rate on two of them give n 3 and skill_n 2. The
  forecaster's Brier on the paired days is (0.64 + 0.01) / 2 = 0.325, and the base rate's is 0.5625. Skill =
  1 - 0.325 / 0.5625 = 0.4222, which matches the test's expression.
- **My plant:** `skill_n = len(pairs)` (the unpaired count) fails the new test.
- **Gates.** `tests/forecast_scoring_v4` + `tests/forecast_scoring`: 85 passed. Ruff and format are clean. The
  builder's full suite shows 6,119 passed and 3 failed; those 3 are the known red tests on `main` (judge 177 addendum
  4), not this branch's.

## Notes (not blocking)
- `fno/forecast_scoring/v4/` will be byte-checked at the v4 freeze. This change lands before it, so the freeze hashes
  include it. Merge it before the freeze commit.
- LR1 L13 is answered: the report now shows that the skill is computed on 1,909 shared days, not compared across 2,159
  and 1,909.

**Verdict: PASS for 84dbb4d2.** Merge once `main` is green again; the full suite on the merged tree must pass.
