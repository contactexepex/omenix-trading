# Judge 467: EDGE1 story text, has any simple rule-based NIFTY or BANKNIFTY option trade made money after costs (12c1f0c2)

Judge B, 22 Oct 2026. Lane 1: a new story with research records and the ledger.
- Builder: G13/G13b (session_01UkTaDeTRF9ksDgQB9cTU5C).
- Branch: `story/edge1-text`.
- The owner chose this study through the orchestrator.
- Number claimed with `tools/claim_number.py`.

## Verdict: FAIL (2 should-fix)

The text is honest and well built. Points in its favour:
- It starts from the four failed tests and does not re-run them as new.
- It reuses the engine, the costs, the margin calculator and the settlement chain, with no second simulator.
- It registers through R1's factory with a GR1-style freeze and two runs.
- It fixes the pass rule now, and positive at both pad levels is the right extra condition.
- It states in advance that 46 trades will most likely be too few. This checks out: G3's code uses z = 1.28 at a 0.10
  pass level, so (1.28 x 4,000 / 300)² is about 291.

Two things decide whether the result can be read at all, and both must be settled in the text first.

## Should-fix 1: the "held-back" BANKNIFTY 2023-26 has already been looked at for the very quantity that drives this P&L

The text calls BANKNIFTY options "exposed, not spent" and makes 2023-01 to 2026-10 the one confirmatory set. But
premium selling earns exactly when implied ranges are wider than what happens. GR1 already measured that on
BANKNIFTY, over the held-back years:
- In 2024, implied's own 50% band held **0.624** of BANKNIFTY N1 closes, so it was too wide (judge 442.2, from
  `selection.json`).
- In 2025-26, implied's 90% coverage was **0.927** on BANKNIFTY N1. A constant shrink scored 0.20% better and made the
  band 7% narrower (judge 459, `final.json`).
- G13b's own back-fill scores for every year were read before GR1.

**Why this is normal running, not imagined:** the desk has seen evidence, in the held-back years, that BANKNIFTY
implied ran wide. That is the variance risk premium a short condor or fly harvests. A held-back pass would then
partly confirm something already seen. That is the forking path FACTORY_RULES section 4 guards against.

**Fix (pick one, and write the facts above into the text either way).** Either:
- **(a)** label the BANKNIFTY held-back test `exploratory` too, so that only the forward shadow (R3) can confirm. This
  is cleaner, and given G3's sample size the label is likely in any case; or
- **(b)** keep it as the confirmatory set, but say plainly that the direction was partly foreseen from GR1. A pass
  then earns *some evidence* at most, never *strong*.

Put this to the owner in Q2.

## Should-fix 2: how untraded legs (settlement-price proxies) count is not stated, and that is what sank experiment 1

The engine prices a leg that did not trade that day at its settlement price, flagged
(`fno/research_engine/leg_prices.py`: "Settlement is a valuation proxy, not an executable price"). The text's own
table says experiment 1's "positive totals rest on stale exits".

**Why this is normal running:** BANKNIFTY's far monthly wings in 2019-22 often did not trade, so this is not rare.
SL2's and TP50's triggers can also fire on proxy prices.

**Fix: state the rule now.** Either:
- an entry or exit with any settlement-priced leg is "unfillable" and not taken (counted, as the report lists); or
- it is kept but flagged, the pass rule is computed on trades whose every leg traded, and the all-trades figure is
  shown beside it, never decided on.

Also say that a stop or target is checked only on traded closes. Finally, report the share of proxy-priced legs per
variant and period.

## Notes (one line each)

1. **Wing width with historical lots.** The rule (the largest width with worst loss within Rs 10,000) follows each
   expiry's lot size, so the structure changes with the lot. Say so, and show the width per year.
2. **BANKNIFTY's expiry day changed.** Thursday to Wednesday in Sep 2023, then the monthly moved again in 2025; the
   weeklies ended on 14 Nov 2024. The cycle window counts sessions, so this is fine, but list the dates in the report.
3. **`derived_lot()` before 2024 is a computed lot.** Cross-check it against NSE's circular lots on a few expiries in
   the build.
4. **The BANKNIFTY SPAN `symbol` path is unproven.** The text already plans to test it against NSE's published margin
   first. Keep that as a build gate: no return-on-margin figure without it.
5. **Q2's trade-off, plainly for the owner:** opening BANKNIFTY 2023-26 now spends the last untested history for a
   test G3 will likely call too small. Holding it back costs nothing except time.

## Addendum 1: revision 2 at 9d49ef16, with 2e6759c3 (number 467.1, claimed with `tools/claim_number.py`)

**FAIL. Should-fix 1 is met; should-fix 2 is still open.**

### Should-fix 1: met, more strongly than either option I gave
- All history is now exploratory. The R1 owner's point is accepted: G13b's back-fill read BANKNIFTY's 2019-26 option
  closes, and `fno/factory/data_spend.py` treats `exposed` and `spent` alike.
- EDGE1 is now a screen:
  - run 1 (2019-22) selects and applies G1;
  - run 2 (2023-26) is opened once and tests only run 1's passers, with Holm.
- A fixed nomination rule sends at most two variants on as a proposal for an R3 forward shadow, the only confirmatory
  test.
- The labels say exploratory, with *some evidence* at most.

### Should-fix 2: not addressed
The new text adds the A14c owner's bad-price skip: an entry whose NOV is outside `payoff_bounds` is skipped. That
catches impossible prices, not stale ones. The text still does not say:
- how a leg the engine prices at **settlement**, because it did not trade that day (`leg_prices.py`, flagged), counts
  in run 1, in run 2 and in the nomination rule;
- that SL2's and TP50's triggers read **traded closes only**;
- the share of proxy-priced legs per variant and period.

With a nomination rule now in place, this matters more: a nomination built on settlement proxies would send a false
positive to the owner, exactly as experiment 1's "positive totals rest on stale exits".

**Fix: choose one rule and write it in.** Either:
- **(a)** any settlement-priced leg makes that entry or exit unfillable: not taken, counted by reason; or
- **(b)** proxy legs are kept but flagged, and every pass and nomination condition is computed on trades whose every
  leg traded, with the all-trades figures shown beside them and never decided on.

Plus the traded-close rule for SL2 and TP50, and the proxy share in the report.

### Margin points (2e6759c3): sound, all of them
- point-in-time SPAN with the manifest SHA-256 and a created-before-09:00 check;
- each day's own lot;
- missing series named and never filled;
- BANKNIFTY's monthly pick checked, and NSE's figures checked before any result.

## Addendum 2: revision 3 at 28c35558 (number 467.2, claimed with `tools/claim_number.py`)

**FAIL. One narrow should-fix is left, from should-fix 2.**

### What is now met
- **Should-fix 1.** Option (a), with my facts written in as a second reason for "exploratory": 0.624 in 2024, 0.927 in
  2025-26, and G13b's yearly scores read. Q2 now asks the owner to accept screen-and-nominate.
- **Should-fix 2, mostly.**
  - Entry only when every leg traded (volume > 0).
  - SL2 and TP50 checked only on days when every leg traded.
  - Trades not taken are counted by reason.
  - The proxy share and all trades are shown beside the traded-only figures.
- **All five notes**, plus the R1 owner's and A14c owner's precisions: the bad-price test is strictly inside, so a
  credit of 0 or of the full width is skipped.

### Remaining should-fix: the exit rule is ambiguous, and dropping trades with no fully traded exit can flatter the screen

The text says a trade is "closed only at a close where every leg traded. If no leg-complete close exists by the exit
day, the trade is recorded at the exit day with its proxies flagged, and it is left out of the pass and nomination
figures."

1. **"By the exit day" does not say which close is used.** Is it the last fully traded close on or before the planned
   exit day? Picking an earlier day after seeing the exit day is a hindsight choice. Is it the planned exit day only?
   Write the exact rule.
2. **Leaving those trades out biases a short-premium screen upward.** It is the normal case, not a rare one: in a big
   move the far wing often stops trading, so a losing condor or fly is the trade most likely to have no fully traded
   exit, and so the one most likely to be dropped.

**Fix.** Define the exit close exactly; the planned exit day's close is the simplest. Then:
- the nomination rule also requires run 2's mean net to be positive on **all** trades, with proxies included, as well
  as on the traded-only set, at both pad levels;
- report how many trades each variant drops for an incomplete exit, and their mean proxy P&L.

## Addendum 3: revision 4 at a219747f (number 467.3, claimed with `tools/claim_number.py`)

**PASS. The text may go to the build** (parts behind the existing interfaces, each agreed with its owner, with nothing
merging into `fno/` before Monday 26 Oct, as the text says). The owner's answers to Q1 and Q2 are still open; the text
has defaults for both.

| Point from 467.2 | Result | Where |
|---|---|---|
| (1) The exit day is exact | MET | see "The exit rule" below |
| (2) No survivorship | MET | see "Incomplete exits" below |

### The exit rule
- A stop or target exits at the close of the day it triggers. Such days have every leg traded, because SL2 and TP50
  are only checked on those days.
- Otherwise the exit is the planned exit day's close: T21's day, or the expiry for EXP, cash-settled at the final
  settlement price, which is a real price.
- No earlier or later day is ever searched for.
- An untraded leg at that close takes its settlement proxy, and the trade is marked "incomplete exit".

### Incomplete exits
- They are kept and flagged, never dropped, and the text gives the reason.
- The pass and nomination figures use trades with a complete exit, and the nomination also needs run 2's mean net to
  be positive on all trades, proxies included, at both pad levels.
- The report shows each variant's incomplete-exit count and their mean proxy P&L.

### Next from me
- The study's protocol and freeze, before run 1, as for GR1.
- The code with its synthetic tests.
- Then I reproduce both runs.
