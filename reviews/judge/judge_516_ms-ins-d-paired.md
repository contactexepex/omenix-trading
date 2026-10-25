# Judge 516: MS-INS part d, the paired comparison

**Scope:** story/ms-ins-paired at c40ed950 (builder session_01LH7m9r5TCAKgZbeHVYkiTD), diff 8b58177c..c40ed950.
Story MS-market-school.md INS-d and "INS-d Claims"; `research/school/INSTRUCTOR_V1.md`. Lane 1, one judge.
Round 1 of 2. Judge K (session_019ZApRwkUiNMKDsf1k4W44z).

**Verdict: FAIL.** 2 should-fix, 1 minor. The pairing, cut, clustering, batch bound and v1 ladder are right. The
false-positive rate printed on every seller row, and frozen in the card, is far too low.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1-4 | Hand pairs, one point a session, abstention 0 and counted, the cut | MET | plants caught: refused not 0, unfilled ignored, cut reset, per-road points, after-cut count, unavailable count, executed tickets |
| 5 | v1 ladder 29/30; never Watching | MET | `<=` plant caught; the `PairedRow` Watching guard plant caught |
| 6 | Three statuses | MET | a's type, unchanged |
| 7 | Null calibration | PARTLY | the Gaussian gate is checked at the cards' holds, read at test time. The skewed-seller rate printed on seller rows is wrong (finding 1) |
| 8 | Planted edge | MET | +1.0 test |
| 9 | Empty | MET | survivor noted in the minor |
| - | Batch bound and holds | MET | plants caught: first batches kept, t at k, one batch allowed, min hold to max, RC1 twin min, floor days, batch = hold, driver hold only, last exit day ignored. `t_quantile` is S6's one-sided 95% table (6.314 at 1 df) |
| - | Gates | MET | see Notes |

## Findings
1. **Should-fix: "this method can falsely look positive up to 21%" is false for the seller shapes and holds in force.**
   - The test pins one cell only: loss chance 0.1, hold 10, batch 15, 120 sessions.
   - My runs: `nulls.seller_slots` and `share_positive` (the branch's own code), 1,000 seeds, batch = 1.5 x hold.
     Each cell is the share with a positive bound, upper end in brackets:
     - hold 3 (WS1), batch 10: p 0.1 at 20 sessions, 15.8% (18.2%); p 0.05 at 20, 29.6% (32.5%);
     - hold 10 (CS1), batch 15: p 0.1 at 30, 22.0% (24.7%); p 0.05 at 60, 36.1% (39.1%);
     - hold 15 (PS2-4), batch 23: p 0.1 at 46, 25.6% (28.4%); p 0.05 at 60, 40.5% (43.6%);
     - hold 26 (REF), batch 39: p 0.1 at 120, 22.5% (25.2%); p 0.05 at 120, 44.0% (47.1%).
   - The Claims' own cell does not reproduce. Hold 10, p 0.1, 30 sessions is 14.9% in the Claims; my run at their
     2,000 seeds gives 22.6% (upper end 24.5%). At 120 sessions I get 16.7% (18.4%), against their 18.9%.
   - A loss chance of 5% is a plausible far-out credit spread [reasoning only].
   - The owner reads this line as the worst case, and the card freezes it.
   - Expected:
     - measure the seller null over the real holds, loss chances 0.05-0.2, and the session counts where a bound
       first exists;
     - print the measured worst upper end (or a plain "often; measured up to X%");
     - pin the test at that worst cell;
     - correct the Claims table.
2. **Should-fix: the frozen texts disagree with the code.**
   - `INSTRUCTOR_V1.md` lists the real holds as "3, 10, 15, 18, 25 and 33"; the cards give REF 26.
   - The story's frozen method says "35 days monthly" and "REF and RC1 25"; the code says 36, REF 26 and RC1 15
     (my run of `hold_sessions` on the cards).
   - The card is hashed into every instructor record and changes only as v2. Correct both before it freezes.

**Minor:** `compare` skips a pair only when its common set is empty or absent. Replacing that with "absent" survives:
nothing tests a pair present with no road-days. Add one test.

## Plants
25 planted, 24 caught; the survivor is the minor.

## Notes
- **Gates (my run, python3 after routine setup):** pytest -n auto 13,665 passed, 16 xfailed. ruff check and format,
  check_imports and check_records are clean.
- Ruling D (no Watching in v1) makes finding 1 a reporting error, not a status error. My numbers support ruling D
  more strongly than the Claims do.

## Addendum 1: round 2 at 5bdc8fb0

**Verdict: PASS.** Lane 1, one judge. Scope: the single commit c40ed950..5bdc8fb0.

| Round-1 finding | Result | My evidence |
|---|---|---|
| SF1 the printed seller rate | ACCEPTED | The rate is now 46% in code, card and test, plus "(rarer full losses can be worse)". The builder's worst cell (p 0.05, hold 26, 120 sessions: 43.4%, upper end 45.6%) agrees with mine (44.0%, upper end 47.1% at 1,000 seeds; the same within noise). My spot checks of the holds I had not run are all under it: hold 18 at 54, 120 and 250 sessions; hold 33 at 100, 120 and 250; hold 26 at 78 and 156; p 0.05, upper ends at most 41.5%. A test pins the worst cell (above 40%, at or under 46%) and my round-1 cell (22.6%) |
| SF2 frozen texts | ACCEPTED | The card's hold list reads REF 26. The story says a 36-day cycle, RC1 15 from its twins, REF 26, matching `hold_sessions` on the cards |
| Minor: empty common set | ACCEPTED | `test_a_pair_present_with_an_empty_common_set_gives_no_row`; my `in common` plant is now caught |

- **Gates (my run):** pytest -n auto 13,667 passed, 16 xfailed. ruff check and format, check_imports and
  check_records are clean.

## Addendum 2: the follow-up 5bdc8fb0..960a03a2

**Verdict: PASS.** Scope: the seeded grid tool `tools/ins_seller_null.py`, its output
`research/school/instructor_seller_null.csv` (96 cells), `nulls.seller_cells` and `nulls.seller_cell`, and two
tests that derive the printed 46 from the file.

- **Reproducible:** I recomputed two cells with `seller_cell` and they match the CSV to 4 decimals: hold 3, p 0.1,
  20 sessions gives 0.1595 / 0.1762; hold 18, p 0.05, 54 sessions gives 0.3715 / 0.3929. The worst cell (hold 26,
  p 0.05, 120 sessions: 0.4340 / 0.4558) agrees with my round-1 run within noise.
- **Plants, both caught:** `SELLER_FALSE_POSITIVE_PCT` lowered to 40, and the worst CSV row edited down.
- The grid's cells must equal `seller_cells` for the holds the cards hold today, so a card change forces a re-run.
- **Gates (my run):** pytest -n auto 13,669 passed, 16 xfailed. ruff check and format, check_imports and
  check_records are clean.
