# Judge 681: CP1 story text, measured cost pads (story/cp1-measured-pads @ 5348d5011), judge B, round 1 of 2

**FAIL (0 blocking, 4 should-fix, 3 minor). Lane 1** (the cost every future study is judged at). Text only: the
doc-reading tests on a trial merge with main pass (963 passed, 13 xfailed); the number check is clean. I did not read
judge J. Each claim below was checked against main's code.

| Check | Result | My evidence |
|---|---|---|
| (1) The flat pad is B2's; CP1 never edits it | MET | `PAD = 1.0` and `PositionCosts` are in `fno/research_engine/cycle_costs.py:24,39`; the file is frozen by `research/evaluation/PROTOCOL.md:438`. C1's story only *uses* pads (`C-code-roles.md:13,37`). The owner's "C1's flat Rs 1" is corrected openly. `FlatPad` equal to the paisa is criterion 6 |
| (2) MS-SIM-b reused unchanged | MET, with S1 | `relative_half_spread` and `bucket_of` (`fno/school/simulator/spreads/`); session-median weighting (`learner.py:4`); `MIN_QUOTED_SESSIONS = 30` (`simulator/constants.py:13`); the bands match `bucket.py` |
| (3) Frozen, versioned, point in time, receipt, deterministic, provisional below 30 | MET as text, with S2 and S3 | design 1-3, criteria 3-5 and 8 |
| (4) Never re-read, by named refusals | MET in intent, with S4 | design 6, criterion 7: three named refusals |
| (5) Three owner questions | MET | 30 vs 20 sessions; median vs 75th percentile; closes vs quotes. Q1's dates recomputed from the canonical markers and NSE's calendar: NIFTY 7 sessions, 30th on 27 Nov; the other three monthlies 4, on 2 Dec; the weekly 2, on 4 Dec. Correct per road, but see S2 |
| (6) Out of scope, with reasons | MET | C1/G1, more than one lot (touch about 1 lot: `SLIPPAGE_NOTE.md`), event days, live fills, stocks |
| Document rules | MET, minors m1-m2 | 122 lines; owner table at the top; links to its owners |

**S1, should-fix: the unit is not stated.** `relative_half_spread` returns a *share of the mid*
(`learner.py:25`). CP1's table, its `max(Rs 1, p75)` and `PadSource.pad` are in Rs a unit. EDGE2's note converts by
recomputing `max((ask - bid)/2, TICK/2)` itself (`research/edge2/slippage.py:39`), which is a second copy of MS-SIM-b's
floor. The text must say:
- how Rs is obtained (relative × that quote's mid, one reuse, no copy of the floor);
- whether a leg pays the bucket's Rs median, or its relative median × the leg's own price.

The two differ widely inside one bucket. The note shows in-the-money medians from Rs 1 to Rs 80 a unit.

**S2, should-fix: Q1's dates are per road, not per bucket.** The 30-session rule is per bucket, and on each session
a road's nearest monthly sits in one days-to-expiry band only. So 0-7 days gains about 5 sessions a month and reaches
30 around six months out [reasoning only, from `bucket_of` and the monthly calendar]. Only the moneyness bands of the
band in use fill at the road's pace. The owner reads "measured from 27 Nov" when most buckets will stay provisional
(max(Rs 1, p75)) well into 2027. Restate Q1 per bucket and give each band's expected date.

**S3, should-fix: the backtest's era.** "Point in time" (criterion 3) covers the table's captures only. A study
backtesting earlier years (EDGE1, EDGE2 and the bhavcopy studies) would be priced with spreads from Oct-Dec 2026, a
calm sample in today's market structure. For older trades, a measured Rs 0.03-0.65 can flatter a study, the very
thing "Why" wants to avoid. State it as a limit with a rule, or as an owner question. For example: a trade dated
before the table's first session pays max(FlatPad, MeasuredPad), or the study reports both.

**S4, should-fix: the refusal has no input.** `PadSource.pad(underlying, strike, spot, expiry, kind, session, slot)`
receives no trial, so `MeasuredPad` cannot refuse a trial as design 6 says. Name where the check sits: for example,
`MeasuredPad` built per trial from its ledger row and card, in the composition root, refusing at construction. Name
which ledger field gives the registration date (`registered_on`, `fno/research_engine/ledger.py:26`).

**Minors:**
- **m1:** design 1 restates MS-SIM-b's band values. Link to `bucket.py`/MS-SIM-b instead (new rule: link, not restate).
- **m2:** design 5 says the ledger guard "covers the table". The guard checks only that the protocol file is
  unchanged (`ledger.py:7-8`). The Drive-receipt match is CP1's own code (criterion 7); say so.
- **m3:** A16's 15-minute chains are not read by `CaptureReader`, which reads the 3 pm captures (`roads/capture.py:1`).
  Name A16's reader, or put the A16 slots out of scope until one exists.

## Addendum 1

**Round 2 of 2 at story/cp1-measured-pads `1fd94daf6` (165 lines): PASS (0 blocking, 0 should-fix, 3 minor).**
Text only: doc-reading tests on a trial merge with main: 963 passed, 13 xfailed. I did not read judge J. My own data
checks read the verified 15:00 captures through MS-P1b's `CaptureReader` (read-only, scratch script, deleted).

| Finding | Result | My evidence |
|---|---|---|
| S1 unit | MET | The leg pays relative × its own price with a half-tick floor; `percentile` exists (`spreads/model.py:21`). Leave-one-session-out, recomputed: **3,768 quotes** (same). Relative vs rupee median, median absolute error: OTM Rs 0.116 vs 0.138 (text 0.113 vs 0.137), ITM Rs 2.39 vs 2.82 (text 2.46 vs 2.92). Same direction and size; the small gap is method detail |
| Side key | MET | Beyond 1%, ITM over OTM in **26 of 33** buckets, median ratio 1.54, range 0.25-4.08 (text: 26/33, 1.5, 0.25-4) |
| S2 Q1 per band | MET | I simulated each band from the canonical markers and sidecars (sessions already seen per underlying × band), NSE's calendar, last-Tuesday monthlies moved for holidays (Nov: 23 Nov) and NIFTY's two non-monthly weeklies: **all 12 dates match** the table |
| S3 era | MET | Q4: before the table's first session a trade pays max(flat Rs 1, measured), so older backtests can only cost more |
| S4 refusal input | MET | `MeasuredPad` is built only in `fno/costs_pads/wiring.py`, per trial, with no trial-less constructor. Three named errors, keyed on `registered_on` (`ledger.py:26`); criterion 8 plants a trial-less build |
| m1, m2, m3 | MET | Bands linked to `bucket.py`; the receipt match is CP1's own check (`require_registered` checks only the protocol); A16 is out of scope with its reason |
| Document rules | MET | 165 lines; the owner table links out; one owning document for the pad table |

**Minors (no block):**
- **m4:** "cuts the mean out-of-sample error by 8% (the median by 6%)" holds for the error *as a share of the price*.
  I got mean 8.1% and median 5.1% better. In rupees, the unit design 1 judges by, the side split gives mean 7.0%
  better and **median 2.0% worse** (3,450 quotes with both predictions). Say which unit. The side key still stands on
  the 26-of-33 evidence.
- **m5:** criterion 2 says EDGE2's second tick floor "is removed (branch `story/edge2-slippage-floor`)". No such branch
  is on the remote (`git ls-remote`). Push it, or word it as planned.
- **m6:** "each leg's own fill price": say the *unpadded* price (the close), so the pad is never computed on a price
  that already contains it.
