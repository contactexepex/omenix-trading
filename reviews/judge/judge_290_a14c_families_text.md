# Judge 290: A14c families, story text (story/a14c-families at cdf31c7f)

**Verdict: PASS (text). The code is lane 1 and has its own judge, with the hand check below.**

## Story text against the owner's decisions
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | One k per family, debit and credit (DESK_DECISIONS 16 Oct, "(b) k per family") | MET | families table in `fno/constants.py`, read by A14c, C2 and C4 (C4 keeps its no-research-engine rule) |
| 2 | Families tied to payoff, not hand-listed only | MET | test: debit means least value ≥ 0, credit means most value ≤ 0 (`payoff_bounds`). SF and SC (short iron fly, short condor) are ≤ 0; BF (long iron fly) is ≥ 0. A code with no family is refused by name |
| 3 | Skip impossible entry prices (DESK_DECISIONS 16 Oct, "skip impossible prices", the B2 BAD_PRICES rule) | MET | entries whose NOV per unit lies outside the payoff bounds are skipped and named. The owner's row names *entries*, so entries only matches it |
| 4 | My own hand check agrees with the PDS example | MET | judge 237 add. 2: PDS 300 entry NOV Rs 34,424 for 65 units is 529.6 a unit on a 300 width, which is impossible. That is the entry that set 2.1 |
| 5 | STR1 codes left out of the measure, with the reason stated | MET | the orchestrator's ruling (DESK_DECISIONS 16 Oct): C2 and C4 cap their stressed SPAN, so k acts only on their exposure |
| 6 | 2.1 stays until a family's own judged row | MET | C2 and C4 take the latest row before the day with family = the proposal's or `all`; with neither, the trade is refused by name. Age and the hold-every-fall rule apply per family. A fall needs `--approve-fall` citing the decision, confirmed by the orchestrator (the decision says "a lower value applies only from its judged row") |
| 7 | WORK_REGISTER | MET | the A14c row (same builder); no second version |

## Notes for the code (not should-fix at text level)
1. **The header change and append-only.** The new `family` column changes the header line. Three things follow:
   - judge 269's repository test asserts that the file `startswith(HEADER + seed row)`, so it must change with the
     header, in the same commit;
   - the two old rows keep 8 fields under a 9-field header, so `DictReader` gives them `family=None`. The "read as
     `all`" test should use the real file's bytes;
   - O9 lists `stress_factor.csv` among the files that move to Drive write-once. Make the header change before that
     move, or it becomes a new version under O9's rule 2. Tell O9's builder.
2. **Thin measures.** The debit k rests on BF alone, and the credit k on SF and SC. After impossible entries are
   skipped, the line should print how many held positions each family measured. A family measured on a handful of
   positions is weak evidence for a lower k.
3. **Peak days are not bound-checked** (known limit, stated). An impossible price on a peak day can still set a family's
   k. The evidence must name the peak position and day for each family, so the hand check can test that price.
4. When the code comes, I will recompute one family's needed k by hand from two real NSE files (read-only Drive), as
   for 2.1.
