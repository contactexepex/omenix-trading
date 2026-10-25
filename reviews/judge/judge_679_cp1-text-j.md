# Judge 679: CP1 story text (measured cost pads), story/cp1-measured-pads at 5348d501 (judge J, 1 of 2, round 1)

**FAIL** (text), lane 1: 2 should-fix, 1 minor. One file, `docs/stories/CP1-measured-cost-pads.md` (122 lines), under
the 500-line limit. Each functional statement was checked against the code on main.

## The orchestrator's claims
| Claim | Verdict | My evidence |
|---|---|---|
| (1) The flat pad is B2's; `cycle_costs.py` never edited; `FlatPad` reproduces `PositionCosts` to the paisa | MET | `PAD = 1.0` is at `fno/research_engine/cycle_costs.py:24`. That file is frozen by `research/2026-10-12-experiment-1/FREEZE.md:47` and named in `research/evaluation/PROTOCOL.md:438`. A new `PaddedPositionCosts` beside it, with criterion 6's paisa test, is the right shape. The owner's decision row says "C1's flat Rs 1", and the text correctly places it in B2 |
| (2) MS-SIM-b's half-spread and bucket reused unchanged | PARTLY | Both functions exist (`spreads/learner.py:20`, `spreads/bucket.py:42`). But see S1: `relative_half_spread` is a share of the mid, not Rs |
| (3) Frozen, versioned, point in time, Drive and receipt, deterministic; under 30 sessions provisional at max(Rs 1, p75) | MET | Design 1-3 and criteria 3-5 and 8. `MIN_QUOTED_SESSIONS = 30` is at `fno/school/simulator/constants.py:13`. The dates check out on NSE's calendar: the 30th session from the first NIFTY capture (14 Oct) is 27 Nov, from 19 Oct it is 2 Dec, and from 22 Oct it is 4 Dec |
| (4) "Past results never re-read" enforced by named refusals | PARTLY | Design 6 and criterion 7 name the errors, but the interface cannot carry them (S2) |
| (5) Three owner questions | MET | Each comes with its recommendation |
| (6) Out of scope, and why | MET | Charges, G1, more than one lot, event days, the desk's and school's live fills, and stock options, each with its reason |
| One owning document; links, not restatements | MET, m1 | The ownership table links C1, B2, MS-SIM-b, A4, A16 and R1 without restating them |

## Findings
**S1 (should fix) The unit of the table contradicts the function it reuses.**
- Design 1 stores "the median of the session medians of the half-spread (Rs a unit)", and the pad is Rs a unit.
- But MS-SIM-b's `relative_half_spread` returns half the gap as a share of the mid, floored at half a tick
  (`learner.py:20-25`).
- A median of relative values times one price is not the median of rupee values. So the text must say which quantity
  the table holds:
  - **(a) Rupees:** each quote's rupee half-spread is `relative_half_spread(q) * q.mid`, which keeps the tick floor.
    The session medians are taken over rupees. This is what `research/edge2/SLIPPAGE_NOTE.md`'s rupee table shows.
  - **(b) Relative:** the pad is `relative * the leg's own price` at fill time. That scales with the premium, which
    is arguably truer for in-the-money legs, but `PadSource.pad` would then need the leg's price.
- Pick one, state the formula, and test it against the note's published medians on the same captures. For example,
  NIFTY monthly under 1%, 0-7 days: Rs 0.12.

**S2 (should fix) The refusal has no trial to refuse.**
- Design 6 says `MeasuredPad` refuses any trial registered before the table's cut-off, or naming no table or another
  SHA-256.
- But `PadSource.pad(underlying, strike, spot, expiry, kind, session, slot)` carries no trial, and nothing says where
  `MeasuredPad` learns which trial it prices. As written, the owner's rule has no point of enforcement.
- Fix: `MeasuredPad` is built for one trial, from its committed ledger row and its card (the composition root passes
  them), and it refuses at construction. A study cannot price without that object. Add a plant: a `MeasuredPad` built
  with no trial still prices.

**m1 (minor)** MS-SIM-b's `SpreadLearner` and `SpreadModel` already aggregate session medians per bucket. Say in one
line why CP1 builds its own table instead (the side and slot dimensions, rupees, a frozen record), so the two
aggregations are not read as two versions of one function.

## Plants
None (a text round). For the code round: the relative value used as rupees (S1); a trial-less `MeasuredPad` (S2); a
29-session bucket priced at its median; a capture on the cut-off read; `FlatPad` differing from `PositionCosts` by
one paisa.

## Notes
- The orchestrator reports the doc tests at 963 passed. The change is one Markdown file; I judged it by reading.
- I did not coordinate with judge B.

## Addendum 1: round 2 (the last), story/cp1-measured-pads at 1fd94daf (165 lines)
**PASS** (text), lane 1: S1, S2 and m1 closed. One Markdown commit on 5348d501 (+92 -49).
- **S1 closed.** The unit is now one quantity throughout.
  - The table holds MS-SIM-b's relative half-spread, and a leg pays max(relative × its own fill price, half a tick),
    with `TICK` imported (`fno/school/simulator/constants.py:12`).
  - The provisional rule is max(Rs 1, p75 × price). `PadSource.pad` now takes the leg's price.
  - Criterion 2 plants "the relative value used as rupees". The note's Rs 0.12 is a recorded check, outside CI,
    because it reads Drive.
  - The leave-one-session-out evidence (median absolute error Rs 0.113 against 0.137 out of the money, Rs 2.46 against
    2.92 in the money) is labelled [some evidence]. I did not re-run it, as it needs the Drive captures. The choice is
    sound by reasoning: in-the-money rupee half-spreads scale with the premium.
- **S2 closed.** Only `fno/costs_pads/wiring.py` builds a `MeasuredPad`, from the trial's committed ledger row, its
  card and the loaded table, and there is no trial-less constructor.
  - Three named refusals: `PadTableNotNamed`, `PadTableMismatch` (which includes the receipt not matching the file
    read) and `PadTableNotRegistered`.
  - Criterion 8 plants a trial-less build.
  - The text states correctly that `require_registered` checks only the protocol file, so the table check is CP1's own.
- **m1 closed.** Why `SpreadLearner` and `SpreadModel` are not reused as they are: no side key, frozen with the
  practice card, and 26 of 33 buckets differ by side. Every measuring function is reused: `relative_half_spread`,
  `bucket_of`, `percentile` (`spreads/model.py:21`), `TICK` and `MIN_QUOTED_SESSIONS`.
- B's points are in as well: per-band dates (labelled reasoning only, with 2027's missing holidays named), the bands
  linked rather than restated, and A16 out of scope with its reason.
  - New Q4: trades before the table's first session pay max(flat, measured). That is the right default, because
    measured pads can then only raise an older backtest's cost.
- Note: `research/edge2/slippage.py` still computes its own `max(gap/2, TICK/2)` (lines 41 and 109). Its removal is on
  `story/edge2-slippage-floor` (lane 2), as criterion 2 says.
- Document rules: 165 lines, and one owning table that links C1, B2, MS-SIM-b, A4 and R1. I did not coordinate with
  judge B.
