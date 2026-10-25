# Judge 460: G13c code, per-contract ITM chance and its calibration (108faff8, response 315)

Judge B, 22 Oct 2026. Lane 1: a new story that writes evaluation records to Drive.
- Builder: G13/G13b (session_01UkTaDeTRF9ksDgQB9cTU5C).
- Branch: `story/g13c-itm-chance`.
- The story text passed in judges 452 and 452.1.
- Number claimed with `tools/claim_number.py`.

## Verdict: PASS (notes only); `itmchance calibrate` may run once, then merge with a merge commit

## Criteria

| Story criterion | Result | Evidence |
|---|---|---|
| 1. The chance equals F(K) or 1 - F(K) from `Distribution.cdf` | MET | `chances.py` rebuilds G13's own `Distribution` from the stored CDF and tails, never a copy. A put is F(K), a call 1 - F(K). My plant (put and call swapped) fails 11 tests |
| 2. Region and a missing distribution | MET | `body` exactly when K lies within the lower and upper tail strikes. No distribution gives G13's reason and no chance |
| 3. Calibration rows | MET | body strikes only, p = P(S_T > K), y = settlement > K (equal is not above). My plants fail 1 test each: equal counted as above; tail strikes used as rows |
| 4. The cluster bootstrap resamples expiries | MET | per-expiry sums, resampled with replacement through weights, 2,000 draws, a fixed seed. My plant (a degenerate resample) fails 1 test |
| 5. Write-once with a receipt; a rerun with no new settled expiry writes nothing | MET | `publish.py`: no write before an expiry settles, nothing when a report for that last expiry exists, O9's store |
| 6. A real-data run the judge can rerun | MET | see "My own run" below |
| 7. Gates | MET | see "Gates" below |
| Judge 452.1's settlement check | MET | see "Settlement" below |

### My own run (criterion 6)
I ran `calibration_report` myself through the verified Drive cache, as of 22 Oct, with no publish. My summary equals
the builder's:

| Item | Result |
|---|---|
| NIFTY | 93 settled expiries: 60 `futidx_settle`, 33 `sttlm_pric` |
| Left out | 29 Jun 2023 (40 issue days) |
| Rows | 280,778 over 92 expiries |
| Brier by bucket | 0.0341 [0.0298, 0.0392], 0.0632 [0.0557, 0.0720], 0.1063 [0.0940, 0.1205], 0.1497 [0.1276, 0.1748] |
| The 8-21 day, 0.45-0.55 bin | mean chance 0.500 against a frequency of 0.425 [0.340, 0.516] |
| Expiry-day change | read as 30 Sep 2025 |
| Settlement against close | equal on every settled expiry: 0 non-zero differences |
| BANKNIFTY | 0 settled |

### Gates

| Gate | Result |
|---|---|
| `tests/itm_chance` | 39 passed |
| full suite (`-n auto`) | 9,611 passed, 16 xfailed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,813 files formatted |
| `check_imports` | clean |

Every file is under 101 lines.

### Settlement (judge 452.1)
- `LegacyFileSettlement` sits behind E7's `SettlementPrices` interface. It takes the expiring future's `SettlementPrice`
  (`SttlmPric`); option rows must equal it or be 0, else the expiry is refused.
- `FirstSettlement` asks E7 first, and the legacy reader only when E7 has no file. E7 is unchanged.
- The close cross-check refuses a gap of half a paisa or more.
- My plants (the option check removed; the cross-check removed) each fail 1 test.

## Notes (one line each)

1. **The settlement chain in `wiring.py` is untested.** My plant (E7 dropped from the chain) passes the tests. The real
   run's 33 `sttlm_pric` settlements show the chain is wired correctly today.
2. **The two libraries are not compared in their overlap.** Jan-Jul 2024 is in both, and E7 always wins there, so no
   disagreement between them can show. Every settlement equals the official close, which bounds this in practice.
3. **29 Jun 2023 is left out.** It is G13's label for June 2023's contract, which NSE settled on 28 Jun (the holiday
   shift). The label was correct when the files were read. Leaving it out costs 1 expiry of 93. Re-mapping it is
   reasonable; let the owner decide (Q in response 315).
4. **The headline finding is descriptive and exploratory.** Up to 21 days, the frequency of settling above K sits 4-7
   points below the market's chance in the middle bins. This fits the negative-skew premium, where the risk-neutral
   median sits above the forward. Its intervals still include the chance in the bin I checked (0.340-0.516 against
   0.500): reasoning only, from spent data.

## Addendum 1: the review checks at 25d45c89 (number 460.1, claimed with `tools/claim_number.py`)

**PASS. This is the head to run and merge.** It supersedes 108faff8 for the merge.

| Change | Result |
|---|---|
| The label | E7's settlements are now labelled `udiff` |
| `Settled.outcome` and the report's `outcome_counts` | they count `udiff`, `futidx_settle` (marked "(no_close)" when no close existed), `close_mismatch`, `unsettled` and `refused` |
| New tests | E7's real reader over a fake library, the chain order (E7 first, legacy only without an E7 file), option rows equal to the future or 0 accepted, and a different non-zero price refused. This closes note 1 |

**The overlap check.** The builder reports, from real files, that E7 and the legacy reader give the same price on all
six NIFTY expiries of Jan-Jun 2024. I did not re-run this. It is consistent with my run, where all 93 settlements
equal the close.

**My checks on 25d45c89:**

| Check | Result |
|---|---|
| plant: the chain order reversed | fails 1 test (note 1 closed) |
| plant: a close mismatch counted as "refused" | fails 1 test |
| `fno/desk/` | no diff against main |
| `tests/itm_chance` | 42 passed |
| full suite | 9,614 passed, 16 xfailed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | clean |
| `check_imports` | clean |

## Addendum 2: d776b6c1, the settlement chain as a tested function (number 460.2, claimed with `tools/claim_number.py`)

**PASS. This is the head to run calibrate on once and to merge.** It supersedes 25d45c89.

**What changed.** `wiring.settlement_chain(udiff_library, legacy_library)` builds the chain, and both `build_settle`
and the tests call it. This closes note 1, the one plant that survived in the first review (E7 dropped from the
chain).

**My checks on d776b6c1:**

| Check | Result |
|---|---|
| plant: E7 removed from `settlement_chain` | fails 1 test |
| full suite | 9,614 passed, 16 xfailed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | clean |
| `check_imports` | clean |
