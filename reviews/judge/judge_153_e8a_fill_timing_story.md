# Judge 153: E8a fill-timing study, story text check (quality rule 1)

**Story:** `docs/stories/E-paper-desk.md:713-799` (E8a), branch `story/e8a-fill-timing`, commit `13e1f090` (story text
only, 90 lines added, no code).
**Read against:** owner decision of 15 Oct 2026 (`docs/DESK_DECISIONS.md:179`, repeated as the last row), E8 design
(`docs/design_v2/03_layers_factory_desk.md:88-102`), response 144 plan item 3
(`reviews/claude/response_144_noise-fairness-scorecard.md:54-55`), `fno/research_engine/structures.py`, STR1
(`docs/stories/B-research-engine.md:366-376`), experiment 1 protocol, the R2 study folder, A16b, `research/FACTORY_RULES.md`,
`research/DATA_SPEND.md`, `research/ledger.csv`, `fno/research_engine/ledger.py`, `docs/JUDGE.md`.

## Verdict: FAIL (3 blocking, 9 should fix, 5 minor)

The study is worth doing and much of it is careful: the frozen-before-fetch rule, no substitute prices, the
read-only closure, the corrected "real last trades, not estimates" wording and the raw-to-Drive pattern are right.
But as written its headline number would mislead the owner on the exact question asked, the story drops one owner
requirement without saying so, and it has no gap list.

## What I checked myself

- Overnight-gap facts: recomputed from `research/data/intraday/rv-candle/2024-2026` (`sqrt(rv_overnight)`, status ok):
  680 sessions, median 0.223%, >= 0.5% on 17.2%, >= 1% on 4.9%. **Matches** the story (lines 727-728).
- Ledger: last row on `main` and on every remote branch is 53 (R2); no branch claims 54. **Trial 54 is free.**
- `fno/research_engine/ledger.py:26`: `KINDS = ("retrospective", "prospective", "control")`. "kind measurement"
  (line 747) is not a valid kind (finding S1).
- STR1 identities (`B-research-engine.md:376`): "SF is exactly CCS plus PCS, and BF is CDS plus PDS, at the same
  width"; and from `structures.py:142-152`, BF is SF with every leg reversed. So at one price set,
  C(BF) = -C(SF), C(CDS) = -C(CCS), C(PDS) = -C(PCS) exactly (finding B1).
- `fno/intraday/slots.py:1`: A16 snapshots fall on 15-minute marks (09:15 ... 15:30). Used in finding S4.
- Judge number: written as 151, renumbered 153 on 15 Oct (151 was taken on main by judge D's A4c verdict; orchestrator).

## Findings

### Blocking

**B1. The headline (mean of C) is price drift, mostly theta, labelled as "cost", and half the families mirror the
other half.** Lines 758-763 sign C so that "positive is worse for the trader" and report the mean as the delay cost.
From STR1's identities, a buyer's "gain" from waiting is exactly the matching seller's "loss": the mean of C across a
family and its mirror is zero, so the mean cannot be a cost of delay. Over 15:00 to 10:15 the expected C of a short
structure is about one night of theta (three nights after a Friday or before a holiday), which the late entrant
gives up but in return does not carry the overnight risk. The likely result: "selling costs X when filled at 10:15,
buying gains X", which would push the owner towards the wrong decision time. (Note: C *is* the exact P&L difference
to any common exit, so it is not meaningless; it just has to be read as such.)
*Fix:* (a) report only the six non-mirror families (SF, SC, CCS, PCS, LC, LP; state BF, CDS, PDS = minus their
mirror) or keep them all but say so; (b) lead with the **spread of C, not its mean**: the distribution of |C| and of
the adverse side (10th/90th, 5th/95th, 1st/99th percentiles, share beyond 5/10/20%), which is what "does the range still
hold" asks; (c) decompose the mean into a theta part (Black-Scholes theta at the early IV over the elapsed calendar
time) and a residual, and split by calendar gap (1 night vs 3+ nights); (d) state plainly that the cost a delay
can really do the desk, the decay of a decision signal, is not measured here, because no card has trade fields yet.

**B2. "Win at both" from the owner's decision is missing, and not excluded with a reason.** The owner row
(`DESK_DECISIONS.md:179`) lists three outputs: "range still holds, credit/debit change, win at both". The story covers
the first by stand-in thresholds and the second by C; the third is neither covered nor named: line 742 excludes "any
strategy P&L" in general. Response 144 item 3 also asks for "fill rate" (line 55); the story's threshold shares are a
fill rate at assumed range widths but are never called that.
*Fix:* either add "win at both" (for each structure, the net to a fixed exit, for example experiment 1's 21-day exit
or expiry, from both entries; the sign flip rate is the figure) with the DATA_SPEND consequence stated, or list it as
out of scope with the reason and put a question to the owner in a response file. Name the threshold shares as "fill
rate if the entry range were +-5/10/20%".

**B3. No gap list.** `docs/JUDGE.md` quality rule 2: "Every story lists each requirement of its design paragraph
(and of every design section it cites) as covered by a named criterion, or out of scope with the reason. A
requirement in neither list is a blocking finding." E8a cites the E8 design and response 144 item 3 and has no list.
Requirements found in neither: "win at both" (B2); R = 5 and R = 30 fills, which E8's design reports beside R = 60
(`03_layers_factory_desk.md:91-93`; R = 30 also lands next session at 09:45, R = 5 at the 15:15 mark); E4's 15:15
execution-snapshot baseline (line 102); bid/ask plus pad fills (line 93, covered only by the live follow-up).
*Fix:* add the table; cover R = 30 (cheap: one more candle per leg) or exclude R = 5/30 with the reason.

### Should fix

**S1. Ledger kind.** Line 747 says "kind measurement"; the guard allows only retrospective, prospective, control
(`ledger.py:26`). *Fix:* "kind prospective, hypothesis no", as R2's row 53.

**S2. Data spend understated.** Line 775 says Groww's historical option candles become "exposed". C is exactly the P&L
of "sell at 15:00, buy back at 10:15" (and of the 14:00-to-15:00 hold), a known candidate strategy family (overnight
premium). *Fix:* register the new rows as the update rule requires (`DATA_SPEND.md` update rule: `registered` at
registration, in the ledger commit), and after the run mark the 15:00-to-10:15 and 14:00-to-15:00 option price changes
of 2024-26 **spent**, the rest of those candles exposed; state that 2019-2023 intraday option candles stay fresh.

**S3. No paired comparison of the two paths.** The owner's choice is 14:00 versus 15:00, yet lines 758-763 give each
path separately. *Fix:* per family, the paired difference between the paths (same session, same blocks) with its
bootstrap interval, for the B1 headline figures (tail shares, not only means).

**S4. The 14:00 path does not follow E8's rule, and its information cost is unmeasured.** A decision at 14:00 makes a
card at about 14:08 (E8's own example is a 15:08 card for a 15:00 decision), so T + 60 = 15:08 fills at the first mark
at or after it, 15:15 (candle 15:00-15:15), not at 15:00 (line 755). Also a 14:00 decision cannot use A4's 15:00
snapshot or the last hour's moves the current inputs rely on. *Fix:* define one card latency for both paths and derive
each fill mark from it (or say "decide at 13:52"); state in the report that the 14:00 path measures price drift only,
never the loss of the last hour of information.

**S5. Stale-leg and missing-symbol selection has no limit.** Lines 756-757 and criterion 5 drop and count, which is
right, but dropped days may not be random (second-month wings, quiet or very fast days), and the probe already failed
on a Sep 2025 symbol (line 733): if the Tuesday-expiry months fail, 13 of 33 months vanish silently into a count.
*Fix:* report stale and missing counts by month, gap band and family; a rule frozen in advance, for example "a family
with more than 10% of its eligible days stale or missing is reported as insufficient, with no figures"; and, before the
freeze, a coverage-only probe (candle counts, no prices read) of one symbol per expiry month.

**S6. Spread caveat is too thin and assumes what it should measure.** Line 765: A4's 15:00 bid/ask since 13 Oct 2026
is 3-5 sessions at build time and has no 10:15 quote, yet the text says the spread is "a separate cost that both times
pay". Morning spreads are commonly wider than at 15:00. *Fix:* print the session count; say that the 10:15 spread is
unknown until A16 has data and that the live rule will measure it; drop "both times pay".

**S7. Live rule cannot fail in practice.** Line 769-771: "agree within the bootstrap interval" on 20 sessions; the
interval will be very wide, and bid/ask C differs from candle C by construction (half-spreads). *Fix:* compare
candle-close C with **mid-quote** C on the same sessions, paired, report the spread separately, and state the
smallest difference 20 sessions can detect.

**S8. Expiry and lot unit.** Line 750: "nearest monthly with at least 7 sessions left" mixes 7-22-session contracts and
differs from experiment 1's 30-45-day entry, the only structures the desk has studied. Line 758 "per lot": NIFTY's lot
changed over 2024-26. *Fix:* split by days to expiry (7-14, 15-29, 30-45 calendar days, adding the next monthly), and
report rupees per unit and at the current 65 lot (as experiment 1); the share of the early price also blows up on
small credits, so add C as a share of the width (maximum risk).

**S9. Criteria do not cover several rules the judge is told to break.** "Judge verifies" (line 792) plants an
expiry-week entry, but no criterion states the 7-session rule; sessions (special and muhurat excluded), bootstrap
seed and block, the gap and VIX bands and the 14:00 path's hand check have no criterion. *Fix:* one criterion each,
including a hand-checked 14:00-path day.

### Minor

**M1. Block length 5 is a guess.** Delay windows of consecutive days do not overlap (15:00 t to 10:15 t+1, then 15:00
t+1 to 10:15 t+2), so the correlation is volatility clustering, not overlap; clustering lasts longer than a week. Add
blocks 10 and 20 as sensitivity.

**M2. Bands from the wrong window.** The gap band should be NIFTY's own 15:00-to-10:15 move (same index candles), not
close to open; the VIX band should use a value known at the decision (previous close or the 15:00 candle).

**M3. Candle close is a last trade.** For a far wing it may be minutes before 15:00 and at either side of the spread;
this adds noise to C and widens the tails (inflating the share beyond 5%). Say so beside the tail figures; optionally
report a candle-VWAP sensitivity.

**M4. Feasibility unstated.** No estimate of calls. My own rough estimate (reasoning only): about 40 strikes x 2 types
per monthly expiry x 33 expiries, one 90-day call each (A16b pattern), about 2,000-3,000 calls, 20-40 minutes at 2 a
second. State the estimate and run outside market hours, so A4 (14:33-15:30) and A16 share no Groww key load.

**M5. Housekeeping outside the story:** `docs/stories/E-paper-desk.md:709` repeats the end of line 708, and the owner
decision appears twice in `DESK_DECISIONS.md` (line 179 and the last row). One line each to tidy.

## Pushback on the brief

- "Overlapping trades": the delay windows are disjoint (M1). Daily entries into one expiry share moneyness and
  regime, which block bootstrap handles; this is not blocking.
- "Is anything added that nobody asked for": the 14:00 path is asked for by E8's own remedy text (line 101); widths
  100 and 300 as sensitivity are cheap. No addition is unrequested.
- Exposure and privacy: results are history and per family, no live strikes, raw only in Drive. Fine.

## Re-judge needs

B1-B3 fixed in the text; S1-S9 fixed or answered with evidence; a new SHA.
