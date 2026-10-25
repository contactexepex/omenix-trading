# Judge 500: MS-SIM-a, practice windows, history chain and dated terms

**Scope:** story/ms-sim-a at b481ab70 (builder session_01W2JE3W9xYftEDWTysHkdVC), diff origin/main...b481ab70. Story
MS-market-school.md section 7 (7.1, 7.4 SIM-a) and Claims 7.7. Lane 1 (practice records). Round 1 of 2. Judge H
(session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: FAIL.** 2 should-fix, 2 minor.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Windows: a spent day passes; 12/13 Oct boundary; FINNIFTY and MIDCPNIFTY refused; `first_counted` | MET | `windows.py`; 3 plants caught (a day past the end, first_counted ignored, NIFTY-W widened to 12 Oct) |
| 2 | Allow-list agrees with DATA_SPEND | MET | The rows match DATA_SPEND lines 23, 24, 25 and 41: NIFTY monthly 2019-23 and 2024-26 `spent`, NIFTY weekly Feb 2019 - 9 Oct 2026 `spent`, BANKNIFTY 2019 - 20 Oct 2026 `exposed`. FINNIFTY and MIDCPNIFTY have no row, so they are refused |
| 3 | Chain: rows, monthly vs weekly (index future listed), board lot never derived, empty and damaged files, index close | MET | `bhavcopy_chain.py`; parity with EDGE1's reader; 4 plants caught (no-rows day returned, far expiry's close, damaged file stops the chain, other underlyings read) |
| 5 | Dated lots and STT on both sides of each change | PARTLY | STT schedule is EDGE1's (2016, 1 Apr 2023, 1 Oct 2024, 1 Apr 2026). Lots: finding 1 |
| 6 | No NSE, Groww, order, Slack, store-wiring or counting import | MET | `test_isolation.py`, one case per file, plus a planted import |
| - | EDGE1 through one adapter, read-only | MET | Only `history/edge1.py` imports `edge1study` (`lots`, `stt_history`). Both import only the stdlib and their own package; nothing is written |
| - | Gates | MET | pytest -n auto: 11,736 passed, 16 xfailed. ruff check/format, check_imports and check_records are clean |

## Findings
1. **Should-fix: on a UDiFF day the lot falls back to a circular schedule that stops at 2023.**
   - `DatedTerms.lot` (`terms.py:20-24`) takes the file's board lot, else `circular_lot`, whatever the day's format.
   - EDGE1's own rule (`edge1study/lots.market_lots`) uses the circular schedule for **legacy** days only. Its
     schedule has no change after July 2023.
   - EDGE1's `LOT_CHECK.md` lists the UDiFF-era lots: NIFTY 50 to 25 (Apr 2024), 25 to 75 (Nov 2024), 75 to 65
     (Jan 2026); BANKNIFTY 15 to 30 to 35 to 30.
   - My run: a UDiFF `DayChain` of 2 Jun 2025 with no stated lot gives `DatedLot(50, 'NSE circular schedule')`.
     NSE's lot then was 75, so P&L and the cap width would be off by a factor of 1.5.
   - Expected: the circular lot only for legacy-format days (`chain.source`). A UDiFF day without its board lot gives
     None, so the road closes and never takes a guessed lot. Add a test on a 2025 UDiFF day.

2. **Should-fix (orchestrator's size rule, design A, 22 Oct 2026): the size sentinel is defined.**
   `constants.py:14` sets `SIZE_GATE_WAIVED = 10**9`. Nothing uses it yet in a or b, but the rule says sizes stay
   `None` with `SlotQuote.sizes_measured=False` and any such sentinel is a FAIL. Expected: remove the constant, and
   correct the story text in 7.2 that describes it.

**Minor:**
- (a) `history/edge1.py` puts `research/edge1` at `sys.path[0]` for the whole process. That folder also holds
  top-level `cards.py` and `study.py`, which would shadow any other top-level `cards` or `study` import. Nothing does
  that today (fno uses package imports). Appending instead of inserting would remove the risk.
- (b) The Claims say no real-data run of `BhavcopyChain` was possible ("no Drive settings"). This container has the
  Drive settings, so SIM-d's real run should not be skipped on that ground.

## Plants
9 planted, 9 caught.

## Notes
- The Claims' SIM-d requirement is right: `build_nse_fo_library` falls back to NSE. SIM-d must build `DailyFiles`
  from stores only.

## Addendum 1

**Round 2 of 2:** story/ms-sim-a at 662447ee, diff b481ab70..662447ee. **Verdict: PASS.** Lane 1.

**Gates (my run, on b's tip b62bc0b5, which holds a):** pytest -n auto: 11,802 passed, 16 xfailed. ruff check/format,
check_imports and check_records are clean.

**Findings:**
1. **UDiFF lot fallback: ACCEPTED.** `DatedTerms.lot` uses the circular schedule only when `chain.source` is
   `PANEL_FORMAT_LEGACY` (`"legacy"`, the label `DailyFiles` gives).
   - A UDiFF day of 2 Jun 2025 with no stated lot gives None.
   - A legacy day of 2 Jun 2020 gives 75.
   - Plant (legacy check removed) caught.
   - The Claims' real read of 2 Jun 2025 shows the file's own lot 75.
2. **Size sentinel: ACCEPTED.** `SIZE_GATE_WAIVED` is gone from `fno/` and from the story, and 7.2 describes design A.
- **Minor (a): ACCEPTED.** EDGE1 is loaded by file path as `ms_sim_edge1study`. After loading, `research/edge1` isn't
  on `sys.path` and `cards` isn't imported (my run). Plant (path inserted again) caught.
- **Minor (b): ACCEPTED.** The Drive claim is corrected, and there is a real-data run in Claims.
- The new SIM-d finding in the Claims is right and should become a SIM-d criterion: legacy files carry no underlying
  price, so the wiring must pass A10's index closes.

**Plants:** 2, both caught.
