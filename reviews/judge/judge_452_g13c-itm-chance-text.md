# Judge 452: G13c story text, each contract's market-implied ITM chance and its calibration (9cdec546)

Judge B, 22 Oct 2026. Lane 1: a new story that writes evaluation records and a Drive file.
- Builder: G13/G13b (session_01UkTaDeTRF9ksDgQB9cTU5C).
- Branch: `story/g13c-itm-chance`.
- Register row on main 3246ad0a.
- Number claimed with `tools/claim_number.py`.

## Verdict: PASS (notes only)

## Criteria

| Check | Result | Evidence |
|---|---|---|
| Purpose and labelling | MET | Every number carries "risk-neutral (market-implied), not a forecast". No trade or stop decision reads it, and it is in no protocol. A corrected "real-world" chance would need a protocol (Q1) |
| No duplicate | MET | It reads G13's stored CDF through one shared function, the same as `Distribution.cdf`, not a copy, and G13b's close tables through their readers. It edits nothing in `fno/price_distribution/` or `fno/price_ranges/`. Weeklies stay with A4's builder |
| Arithmetic | MET | A put is ITM with chance F(K) and a call with 1 - F(K). The region (body or tail) is shown, never hidden. A missing distribution gives G13's reason, never a guessed number |
| Calibration design | MET | see "Calibration design" below |
| Interfaces and composition | MET | a new package with `wiring.py` (to be added to CLAUDE.md's list); `ItmChances.for_day` / `.for_contract` and `ItmCalibration.latest` are named for FL1 and the designer |
| Acceptance criteria | MET | testable: hand cases, put plus call summing to 1, the tail region, an unsettled expiry counted, a close equal to K is "not above", the cluster test (one expiry duplicated gives the same interval), write-once, and a real-data run the judge can rerun |

### Calibration design
- One row per strike in the CDF body, with p = P(S_T > K), so the call and put are one test.
- Horizon buckets: 1-7, 8-21, 22-45 and over 45 days.
- The cluster bootstrap resamples whole expiries. This is right: every row of an expiry shares one settlement, and
  consecutive days overlap.
- n expiries is printed beside every figure.
- The report splits by source (back-fill against 3 pm) and at NIFTY's Tuesday change.
- No forecaster contest is claimed.

## Notes (one line each)

1. **Settlement source.** The outcome is the index close on the expiry date from G13b's tables, while E7's
   `NseFinalSettlement` (`fno/desk/settlement.py`) already reads NSE's `SttlmPric`. Say which is the authority, and in
   the build cross-check that they are equal on every expiry where both exist, so the project keeps one settlement
   fact.
2. **Data spend.** DATA_SPEND already marks NIFTY's monthly option closes for 2019-2026 as `spent`, so this report is
   exploratory by construction. If Q1's corrected forecaster is ever built, its protocol must say these expiries were
   read here; add the row then.
3. **The counts are not yet confirmed.** "About 93 settled NIFTY expiries" and BANKNIFTY's first settled expiry on 27
   Oct are marked unconfirmed. The build's first run must state them, as criterion 6 says.
4. **The far tail is left out of the calibration.** Rows use body strikes only, so the far tail (often the crash-premium
   strikes) is shown but not calibrated. Say so in the report's header.

## Addendum 1: notes written in at fad73292 (number 452.1, claimed with `tools/claim_number.py`)

**PASS stands.** All four notes are in the text:
- E7's `SttlmPric` reader (`fno/desk/settlement.py`, reused) is the authority, and G13b's closes are the to-the-paisa
  cross-check. A mismatch is listed with both values and the expiry left out.
- The header says the report is exploratory and points to DATA_SPEND.
- Criterion 6 confirms the counts and the mismatches.
- The tail strikes are shown but not calibrated.

**One build-time check, new from reading E7's code.**
- E7's reader goes through `read_fo_file`, which maps the old format's `SETTLE_PR` to `SttlmPric` (`fno/fo_bhavcopy.py`;
  NSE used that format up to 5 Jul 2024).
- E7 then requires every expiring row to agree. In the old format, an option row's `SETTLE_PR` is that option's own
  settle price, so E7 may refuse every pre-July-2024 expiry. That would quietly cut the about 93 expiries to about 27.
- The build must run E7's reader on one old-format expiry first and report what it gives. If it refuses, take the
  `FUTIDX` row's `SETTLE_PR`, or the close, labelled as such and cross-checked, rather than dropping more than half the
  sample.
- Criterion 6's counts will show this either way.
