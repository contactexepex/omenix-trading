# Judge 403: FL1 story text, the forecast lab and daily reports (story/fl1-forecast-lab at a6c6db0d)

**Verdict: FAIL on the story text: 3 should-fix findings and 3 minor. Lane 1.** Number claimed with O12's tool.

The text is honest and well grounded:
- it tells the owner first that no live forecaster has beaten its base rate yet, that next-day direction is close to
  a coin flip, and that trust is counted in trading days (about 60 for calibration, 6-12 months for an edge);
- it reuses E8's fill parts, G13's scores, A16's observer and LR1's publish-once;
- it splits the build into five parts gated on their inputs;
- it matches the owner's 21 Oct rows 262-264: two channels, NIFTY and BANKNIFTY, ranges first, top 10, the 08:45 slot
  waiting for A22, BANKNIFTY lab positions waiting for A16's marks.

The three findings are in the lab's decision logic, where a wrong design would mislead the owner about trust.

## Findings

**Should-fix 1. The 09:30 positions can use a forecast sealed after the price they trade on (look-ahead).** Strong
evidence: text read.
- The "open" slot's seal cutoff is "before 09:45" (Design, Forecasts row).
- The lab's positions are priced and filled at "the 09:30 mark", with the ranker scoring candidates "under the sealed
  5-95% quantiles".
- So a forecast sealed at 09:44, after seeing 09:30-09:44 prices, could pick positions priced at 09:30.

Fix: the forecast a position is ranked on must be sealed before the mark it is priced and filled at. For example, the
open slot's cutoff is at or before the 09:30 mark's capture start, or the positions use a later mark than the seal.
Add a criterion: a forecast sealed after the fill mark is never used to rank, the day's positions are "not taken:
forecast sealed late", and that is alerted.

**Should-fix 2. The ranker does not say whose ranges it trades, and on the implied range it has no edge by
construction.** Some evidence (reasoning, plus the text's own baselines).
- The forecasts are G13's (`implied`, `rv20`, `hist750`) and later G13b's, but the `RangeRanker` row says only "the
  sealed 5-95% quantiles".
- If it ranks on the option-implied range, then expected payoff against the same options' prices is about zero before
  costs, so the top 10 are chosen by noise and costs.
- Ranking on `rv20` or `hist750` is a real test of "realised versus implied" (the volatility risk premium).

Fix: name the forecaster or forecasters the lab ranks on, state why, and state that the implied range is a baseline,
never a ranking source. Print in each report which forecaster picked the positions, so a lab result is never read as
"the engine works" when it only measures one baseline against another.

**Should-fix 3. Flat tails at the 5% and 95% levels bias the ranking towards selling premium.** Some evidence
(mathematics).
- With "flat tails at the 5% and 95% levels", the outer 5% of probability on each side sits at q05 and q95.
- A short vertical or condor whose short strike is inside the band, but whose wing is beyond q95, then loses only up
  to the payoff at q95 in that model, instead of losing more towards the wing's maximum loss.
- So expected payoff is overstated for exactly the credit structures whose losses live in the tails, and the top-10
  ranking leans to them. That is the pattern experiment 1 already paid for.

Fix: use a tail that keeps the measured mass beyond q05 and q95 at least as far as each candidate's wing. For defined
risk, the payoff beyond the wing is flat at maximum loss, so put the tail mass at the wing (or at maximum loss) and
not at q95, or use G13's anchored lognormal tail. Test it with a condor whose wing lies beyond q95.

**Minor.**
1. **Size.** State each lab position's size (one lot each, as scoreboard A standardises), so P&L across the 10 is
   comparable and the costs (Rs 800-940 a four-leg trade) are per lot.
2. **Winner's curse.** Picking the top 10 of many candidates by expected net overstates each pick's edge. The match
   report should show expected against realised net by rank, so the bias is visible to the owner.
3. **Horizon against exit time.** The forecasts are about the N+1 (or N+3) close, but positions exit at the 15:15 mark.
   Say so in the report, or exit at the mark nearest the forecast's target.

## Addendum 1
Number 403.1. Head: db10d88f (a6c6db0d plus G13b's reader port, a seal check on `sealed_at` (the receipt's commit
time, never the self-reported `issued_at`), and the match report reading G13b's own scores).

Those changes are good: the seal time now comes from `main`, not from the producer.

**The three should-fix findings stand.**
1. The 09:30 issue's cutoff is still "before 09:45", while positions are priced and filled at the 09:30 copy.
2. The `RangeRanker` still does not name the forecaster it ranks on.
3. "Flat tails at the 5% and 95% levels" is unchanged.

## Addendum 2
Number 403.2. Head: 67c98204, with the new section "The lab's rules (judge 403)".

**Verdict: PASS on the story text.**
1. **Look-ahead: fixed.** The ranker reads the 09:30 issue only once it is sealed, and it prices and fills on the
   first A16 mark strictly after `sealed_at`, normally 09:45. A forecast not sealed by 09:45 gives "not taken:
   forecast sealed late", alerted.
2. **Picking forecaster: fixed.** `lab_v1` trades `rv20` (realised against implied), fixed in config. A change is a
   new version, never chosen by recent scores. The implied range is never a picking source. Every report names the
   forecaster and version. The text also reminds the owner that this is the variance-risk-premium test, which costs
   have eaten so far.
3. **Tails: fixed.** It uses G13's anchored lognormal tail beyond q05 and q95, each tail carrying its 5% mass, with
   σ = (ln q95 - ln q05)/(2 × 1.645) over the horizon, running to every wing. Expectations are exact (closed-form
   partial expectations). Criterion 6b tests a condor whose wing lies beyond q95.
   - Check of the formula: for a lognormal, ln q95 - ln q05 = 2 × 1.645 σ√τ, so this σ is the horizon's total σ. That
     is consistent with applying it "over the horizon" (reasoning only: correct when the forecast is lognormal, as
     `rv20` is; an approximation otherwise).
- **Minor findings: all closed.** One lot each; expected against realised net by rank; the 15:15 exit against the
  15:30 close target is stated.
- Positive expected net is required to qualify, and it is re-checked at the fill touch (`RankedPrice`). Good.

## Addendum 3
Number 403.3. Head: 3feff85e, restructured by the owner's "Lab universe, report times and phasing" (DESK_DECISIONS
line 265, 21 Oct): FL1-1 is the 15:45 report plus end-of-day contract tracking; FL1-2 is the 09:15 report plus 09:30
paper fills.

**Verdict: FAIL, 1 should-fix and 1 minor.** The three judge-403 fixes are kept and correctly re-timed:
- ranking on the sealed 09:15 issue; a seal after 09:15 opens nothing, and is alerted (criterion 9);
- filling at the 09:30 mark, after the seal, with `RankedPrice` recomputing expected net at the touch;
- `rv20` as the named picker (criterion 10);
- anchored lognormal tails (criterion 11).
The phasing matches the owner's row.

**Should-fix 1. Contract scoring uses the bhavcopy close for every contract, including untraded ones.** Strong
evidence for the data's nature; reasoning for the effect.
- "The outcome is the contract's N+1 bhavcopy close", for every NIFTY and BANKNIFTY contract, all expiries.
- In NSE's F&O file, a contract that did not trade on N+1 has no fresh close: its close and settlement are stale or
  NSE's own theoretical value. G13b's part B says so for settlement ("settlement prices of illiquid options are NSE's
  own ...").
- Far strikes and far expiries are often untraded, so band coverage there would be scored against a model price or
  yesterday's price. That flatters or punishes the band for reasons unrelated to the forecast. The same applies to the
  "own implied volatility from today's close" that the band is repriced with.

Fix:
- Name the outcome field (close or settlement).
- Score only contracts traded on both days (volume > 0 on day d for the IV, and on N+1 for the outcome). Count the rest
  as "not scored: untraded", reported by bucket, never in the coverage.
- Add a test with an untraded contract.

**Minor 1.** "A future is the quantile itself" ignores the future's carry over the index (basis). Either use the
future's own forward (index quantile × the future's basis ratio at d's close), or say so beside the futures' scores.

## Addendum 4
Number 403.4. Head: baf36c0e.

**Verdict: PASS on the story text.**
- **Should-fix 1: fixed.**
  - Prices are `ClsPric`, never `SttlmPric`.
  - "Traded" means `TtlNbOfTxsExctd > 0`. Both fields exist in the UDiFF reader (`fno/fo_bhavcopy.py:23-24`).
  - Only contracts traded on d get a band (and an IV), and only contracts traded on N+1 are scored. The rest are
    counted "not scored: untraded on d / on N+1" by moneyness bucket and expiry, never dropped.
  - Criterion 6 tests one untraded option each way.
- **Minor 1: fixed.** A future's band keeps its basis (each quantile × the future's d close / the index's d close).
- **Scope:** under the phase-1 freeze, contract tracking moves to part FL1-1b, after FL1-1 merges, with this rule in
  place. FL1-1's code carries no contract scoring.
- **Minor for FL1-1b:** NSE's legacy F&O format (before July 2024) has no `TtlNbOfTxsExctd`. If FL1-1b ever back-fills
  across that date, define "traded" there from the legacy `CONTRACTS` column (contracts traded > 0), mapped in one
  place.
