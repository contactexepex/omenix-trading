# Judge 234: F9a fixed Holm family: `story/f9a-fixed-holm-family` 891de864 (lane 1, evaluation)

Judge B. Claims: response 237. It fixes in F9a the flaw ChatGPT review 120 found in S3: `verdict.py` put only the
eligible units into `holm()`, so one unit becoming eligible moved every other unit's threshold.

## Checks
- **The code.** `holm([p for s in scores for p in _claims(s)])`. Every unit in `scores` gives two claims, and an
  untestable unit (unknown cost, or fewer than 30 changed) gives (1.0, 1.0). `passed[2i]` and `passed[2i+1]` now
  index over all units, consistently. A p of 1 can never pass Holm (`p >= alpha/(m-rank)`), so it only fixes m.
- **The family really is the registered set.** `report.py:83` builds `units` from
  `role_set_of(book, version).unit_ids` for the versions in the period's rows, so every unit of the registered role
  set is scored, including one with no changed opportunities.
- **The changed test is a correction, not a weakening.** `test_an_unknown_cost_...` used to assert b = `DROP` with
  x outside Holm: 2 claims, so b's 0.02 < 0.05/2 passed. That encoded the flaw. With x in the family at p = 1 there
  are 4 claims, and b's 0.02 is not below 0.05/4 = 0.0125, so b is `INCONCLUSIVE`. The assertion is now stricter and
  matches the owner's Holm rule over the fixed family. x still gets `COST_UNKNOWN`.
- **The new test, recomputed by hand.** Units a, b and c, with c at 29 changed opportunities and then 30. A fixed
  6-claim family gives a threshold of 0.05/6 = 0.00833, so a's 0.009 fails at both reviews. An eligible-only family
  would have given 0.0125 at the first review (a passes) and 0.00833 at the next (a fails).
- **My plant** (untestable units leave the family, `()`) fails 2 tests: the new one and the corrected one.
- **The story text** (F9a's Holm paragraph and criterion 7) now says "every unit of the registered role set ... p = 1
  ... 0.05/(2m − i + 1)". It matches the code.
- **Gates.** `-n auto`: **6,930 passed, 0 failed**. Ruff is clean. `tests/role_value`: 51 passed.

## Note (not blocking)
If a book's role set changes version inside one review period, `units` is the union of both versions' units, so the
family grows with the change. That is a registration event, not a unit becoming eligible, so it is consistent with
the rule. Say so in one line if S1 asks.

**Verdict: PASS for 891de864.** S1 items 8 and 11 (judge A) may follow once it is merged.
