# Judge 492: MS-P1m, the school's margins per trade (first judge)

**Scope:** story/ms-p1m-margin-rows at 0499f885 (builder session_01Vm1WnH8i9waM8EJG8zwWqg). Story section MS-P1m;
claims in response 328. Lane 1, money piece: first of two independent judges (judge J second, not read). Round 1 of 2.

**Verdict: FAIL** on one should-fix (four untested shape rules). Everything else holds.

## Gates (my run)
- pytest -n auto: 10320 passed, 16 xfailed.
- `ruff check`, `ruff format`, `check_imports` and `check_records` are clean.

## Checked
- **The gap measure is reproduced exactly.** I ran `tools/ms_p1m_margin_gap.py` through Drive.
  - 13,736 rows on 37 sessions, and "not measured" of 760 (legs not listed) and 304 (`MarginOutsideModel`).
  - All 25 cells of the story's table (share below, minimum ratio), NIFTY split into monthly and weekly, match to
    the printed digit.
- **Per-proposal SPAN with no new read.** `ArchivedSpanMargin` reads the session's first-archived file and checks its
  SHA-256 against A9's manifest (a missing row is named separately). It requires the file to be written before 09:00
  (`SpanFile.written_in_time`, now shared with A14's job and A14c's run; their tests are unchanged and pass). It reads
  in A14's daily mode, uses A14's calculator and exposure rule on the trade's own legs and lot, applies C2's STR1 cap,
  and takes the factor in force from A14c's file.
- **Fail-closed, by name.** Each of these is a `RiskInputError`, so law 3 refuses:
  - not archived; no manifest row; a SHA mismatch; written at or after 09:00; damaged, or a method change;
  - an expiry-day, out-of-model or unlisted leg (`MarginOutsideModel`);
  - plain `TradeTerms`; any Drive failure (class name only); no factor file, or a stale factor
    (`factor_in_force` raises `RiskInputError` too).
- **The factories make the units agree.** `road_proposal` and `road_open_trade` take the lot and legs from the
  terms; an open trade's units are side x lot x lots.
- **Labels on every record.** `record()` carries the method, the factor label ("k measured on NIFTY monthly only
  [reasoning only]") and the broker label. `trade_record()` adds the factor row, file, SHA-256, legs, lot and
  per-lot parts.
- **Byte-identical where required.** `git diff origin/main...0499f885` names no file under `research/data/margins/`,
  `fno/risk/` or `fno/checks/`.
- **Plants: 15 of my own, 11 caught.** Caught: the condor's order; an open trade ignoring lots; any index accepted;
  the SHA check off; the 09:00 check off; 09:00 itself allowed; no STR1 cap; the broker margin stressed; history mode;
  the broker label dropped; lot 1 in the calculator.

## Should-fix: four of `RoadTradeTerms`'s shape rules are untested
- **Defect:** each of these passes every test in `tests/nse_margins`:
  - PDS marked as selling the higher put;
  - CDS marked as selling the lower call;
  - CCS marked as selling the higher call;
  - a fly or condor checked on the call wing only (`out[0] != width`).
- **Why it matters:** the shape check is what makes the structure code true. C2's STR1 cap
  (`stress_cap_per_lot(structure, ...)`) and the bucket sides are chosen by that code. A spread whose wrong leg is
  sold, or a condor with a wider put wing, would be priced and bucketed as something it is not.
- **Test it must pass:** for each of PCS, CCS, CDS and PDS, the legs with the wrong leg sold are refused (one case
  each, not only PCS). A fly and a condor whose put wing alone is not `width` out are refused. All four plants above
  then fail.

## Notes (no action required for this story)
- **Integration.** MS-P1d's margin law today reads `margins.csv` rows and refuses everything else (the owner-facing
  note of judge 488). It changes only when d builds every school proposal and open trade through `road_proposal` /
  `road_open_trade` and uses `ArchivedSpanMargin`. Until that lands, the pilot stays NIFTY condors and flies only.
- **The gap script's steps.** `STRIKE_STEPS` fixes FINNIFTY at 50, while MS-P1a2 found FINNIFTY's November strikes 100
  apart. Such widths fall into the 760 "not listed", so the table is right on what it measured, not on every width.
- **Not reproduced.** I did not reproduce the claims' real-file checks (NIFTY SF 100 equal to `margins.csv`, and
  four hand-worked spreads). Judge J may.

## Addendum 1

**Scope:** story/ms-p1m-margin-rows at 0c0447f8, round 2 of 2 (first judge, independent of judge J).
- My should-fix: wrong-leg-sold tests for each spread, put-wing-only tests for SF, SC and BF.
- My note: the gap script now reads each expiry's own strike step.
- Judge J's finding: the expiry-day ELM is now priced (`ExpiryDayIndexExposure`) instead of refused. Being new
  pricing, I judged it too.

**Verdict: PASS.**

- **Gates (my run):** 11018 passed, 1 skipped, 16 xfailed. `ruff check`, `ruff format` and `check_imports` are clean.
- **The should-fix is met.** All four round-1 survivors are now caught: PDS, CDS and CCS orientation, and the put
  wing alone off-width. All 15 of my round-1 plants are caught.
- **Expiry-day ELM.** On its own expiry day (from 20 Nov 2024), a short index option carries its usual 2% (3% beyond
  10% out of the money) plus 2% of the index (SEBI/HO/MRD/TPD-1/P/CIR/2024/132 para 5.6, effective 20 Nov 2024, as
  cited). Bought legs carry none. Any other day uses A14's rule unchanged. An earlier expiry day, or a day after
  expiry, is still refused. Each trade record names the extra.
  - **4 new plants, 4 caught:** no extra; the extra before 20 Nov 2024; the extra on bought legs; the extra not
    recorded.
- **The gap measure, re-run by me through Drive.** 14,800 comparisons, "not measured: none". Only the FINNIFTY-M row
  changes: SC 75% below, min 0.82; PCS 97%, 0.85; CCS 94%, 0.88; CDS 5%, 0.87; PDS 10%, 0.87. All 25 cells equal the
  story's revised table, and the lowest ratio stays 0.76.

**Still open from round 1, for the orchestrator (not this story's):** MS-P1d must build every school proposal and
open trade through `road_proposal`/`road_open_trade` and use `ArchivedSpanMargin` before any non-NIFTY trade is
possible.
