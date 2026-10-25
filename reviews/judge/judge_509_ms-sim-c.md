# Judge 509: MS-SIM-c, the historical road source and catalogue

**Scope:** story/ms-sim-c at 3c1a3cc6 (builder session_01W2JE3W9xYftEDWTysHkdVC). It merges main, MS-P1a3 (9ede0d1e) and
SIM-a/SIM-b round 2 (662447ee, b62bc0b5). I judged c's own files: `fno/school/simulator/source/` and
`tests/school/simulator/source/`. Story 7.4 SIM-c and Claims 7.7. Lane 1 (practice). Round 1 of 2. Judge H
(session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: PASS**, with 3 minor notes. Design A holds.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Catalogue and source pass a's conformance checks | MET | test |
| 2 | A leg that didn't trade has an invalid quote (volume 0 against 1) | MET | Plant (`volume > 0` dropped) caught |
| 3 | An impossible vertical is flagged, both legs unquoted | MET | Through the pilot's `impossible_keys` on point quotes; plant caught |
| 4 | Close minus and plus the half-spread, rounded outward, no negative bid; sizes `None` with `sizes_measured=False`; the live fill path refuses | MET | `quotes.py`. No size constant anywhere (`grep 10**9 / SIZE_GATE` is empty). A3's `two_sided` treats unmeasured sizes as present, and the live `price_leg` refuses them (test). Plant (sizes 10**9 put back) caught |
| 5 | Look-ahead: only the session's own chain is read | MET for the source | `test_only_the_sessions_own_chain_is_read`; plant (window re-check removed) caught. The driver-decision half of 7.4 test 5 needs the runner (SIM-d) |
| 6 | Insufficient bucket: no quote, counted, never zero spread | MET | Plant caught |
| 7 | Dated lot and STT | MET | a's `DatedTerms`; 2022 and 2026 STT test |
| - | Every output labelled practice | MET for c | `snapshot_id` is `practice_<road>_<day>_<scenario>`. The stdout labels are SIM-d's |
| - | Claims say plainly it hasn't run end to end on real data | MET | Claims: "**Not yet run on real data:** the catalogue and source are tested on fixtures ... SIM-d's dry run does the end-to-end run" |
| - | Gates | MET | pytest -n auto: 12,001 passed, 16 xfailed. ruff check/format, check_imports and check_records are clean. `source/` is 237 lines |

## My real-data run
- Setup: a throwaway script over the Drive archive. `RawFileLibrary(build_archive_stores(), StoredFilesOnly())`, so
  there is no NSE fallback; the request log shows only Google hosts. Empty spread model, median scenario.
- 2 Jun 2025: NIFTY-M and NIFTY-W open (lot 75, step 50 on each expiry). BANKNIFTY-M closes `lot_mismatch` (its two
  monthlies carry different lots after the April 2025 change).
- 4 Mar 2024: NIFTY lot 50, BANKNIFTY lot 15, step 100.
- 24 Jun 2021 (legacy): every road closes `capture_missing` for no index close. That is SIM-d's known A10 item.
- FINNIFTY and MIDCPNIFTY: `not_in_data_spend` on every day.
- Priced legs: 0 everywhere, as expected with no 30-session bucket yet.
- **Impossible on closes:** 42-177 of 260-436 traded legs a road-day.
  - Within 5% of the spot, the whole-chain rule flags 7-70.
  - The same legs judged only among themselves are flagged 7-57.
  - So most flags come from the closes' own staleness. The whole chain adds about 10-30%, which supports the Claims'
    "conservative" reasoning.
  - Practice on closes will refuse many wing legs. SIM-d's report should show that share.

## Findings
None blocking or should-fix.

**Minor:**
- (a) Plant `body = sorted([])` in `_digest` (the quotes dropped from the digest) survived. The code hashes the quotes,
  but no test pins it, although the Claims say "digest covers close". Add a test: one changed close, same spot, gives
  a new digest.
- (b) The Claims' "not changed: `sys.path` insert in `history/edge1.py`" is stale. a's round 2 replaced it with a load by
  file path, which this tip holds. Correct the line.
- (c) The Claims give only `tests/school` (1,414) for this tip, and the full run is "in the message". Put the full-run
  count in the Claims (my run: 12,001).

## Plants
9 planted, 8 caught, 1 survived (minor a).

## Notes
- Merge order, as the orchestrator says: a3, then d's part 4, then SIM-c.

## Addendum 1

**Follow-up:** story/ms-sim-c at fde1dd95 (one test file and the story text, on 3c1a3cc6). **Verdict: PASS**, unchanged.
`tests/school/simulator` passes (118) and ruff is clean.

- **Minor (a), withdrawn: my plant was wrong.** `body = sorted([]) or sorted(...)` is the original expression,
  because an empty list is falsy. It changed nothing, so it couldn't fail a test.
  - A real plant (the comprehension filtered to no quotes) is caught at 3c1a3cc6 and at this tip. The builder was
    right.
  - The new test `test_the_digest_covers_the_quotes_themselves` pins it further.
- **The builder's noted survivor (bid left out of the digest): ACCEPTED as a noted gap.** I reproduced it.
  - A practice quote's bid and ask both come from one close and one half-spread, so a bid-only change with the same ask
    is a tick-rounding edge. The case where the bid rounds to nothing changes `last` and validity counts elsewhere.
  - It's a minor test gap, not a defect. The code hashes the bid.
- **Minor (b), ACCEPTED:** the stale `sys.path` line is corrected.
- **Minor (c), ACCEPTED:** the full run at 3c1a3cc6 (12,001 passed) is now in the Claims and matches mine.
- **New SIM-d criteria:** 13, a lot per expiry (the 2 Jun 2025 BANKNIFTY case), and 14, the impossible-leg share in the
  report. They record my real-run observations correctly.
