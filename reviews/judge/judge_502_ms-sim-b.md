# Judge 502: MS-SIM-b, spread buckets and scenarios

**Scope:** story/ms-sim-b at cc2c5f15 (stacked on story/ms-sim-a), b's own diff b481ab70..cc2c5f15. Story section
7.2 and 7.4 SIM-b, Claims 7.7. Lane 1 (practice records). Round 1 of 2. Judge H (session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: FAIL.** 1 should-fix (criterion 5, which the Claims honestly leave undone), 1 minor.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | 29 sessions insufficient, 30 give three scenarios | MET | `model.py:56`; plant (29 limit) caught |
| 2 | Median, p75, p95 with a known answer; one-sided and empty are insufficient | MET | Linear percentile; plant (p95 to 0.9) caught |
| 3 | A session counts once; a big session doesn't dominate; two roads of one underlying on one day count once | MET | `learner.py`: per-session median keyed by (bucket, session); plant (median to max) caught |
| 4 | Only verified recorded captures; a failing one is skipped with its reason | MET | `recorded.py` over MS-P1b's `CaptureReader`; plant (exception type) caught |
| 5 | Relative against rupee spread, with numbers from the recorded days, in Claims | NOT MET in Claims; the substance holds | My run below |
| - | 30-session rule, no pooling | MET | `scenarios` reads only its own bucket. There is no fallback to a neighbour; fewer than 30 gives `InsufficientSpreadData` |
| - | Gates | MET | pytest -n auto: 11,798 passed, 16 xfailed. ruff check/format, check_imports and check_records are clean |

**My criterion-5 run.**
- Setup: this container has the Drive settings. I used `recorded_snapshots` over MS-P1b's verified `CaptureReader`,
  13-22 Oct 2026, all 5 roads. For each bucket I took the coefficient of variation of the half-spread, with the
  half-tick floor, over all its two-sided valid quotes.
- Result: the relative half-spread varies less than the rupee one in **41 of 48 buckets**. Examples:
  - NIFTY under 1%, 8-21 days: 0.50 against 0.93;
  - NIFTY 2-4%, 22-45 days: 2.30 against 3.29;
  - BANKNIFTY under 1%, 0-7 days: 0.35 against 0.76.
- The 7 exceptions are far or deep strikes of FINNIFTY and MIDCPNIFTY, plus one 3-quote bucket, for example
  MIDCPNIFTY 2-4%, 22-45 days: 1.17 against 0.81.
- Every bucket has only 1-6 sessions. So the relative choice has **some evidence**, not strong evidence.

## Findings
1. **Should-fix: criterion 5 isn't in Claims.** The story requires the choice "with the numbers from the recorded
   days, in Claims". Put the comparison there (the figures above, or the builder's own re-run), with its label and the
   7 buckets where rupees vary less.

**Minor:**
- (a) Spreads learned from Oct-Nov 2026 captures will price 2019-26 closes. The label "spread measured at 15:00" says
  when in the day, not when in time. Add the capture period to the label so a practice result doesn't read as having
  2019's spreads. This is reasoning only: spreads were likely wider in earlier years, so practice is optimistic.

## Plants
8 planted, 8 caught.

## Notes
- b is stacked on a, which fails (judge 500). Re-judge b on a's fixed tip.

## Addendum 1

**Round 2 of 2:** story/ms-sim-b at b62bc0b5 (merges a's 662447ee; b's `spreads/` code unchanged). **Verdict: PASS.**
Lane 1.

**Gates (my run):** pytest -n auto: 11,802 passed, 16 xfailed. ruff check/format, check_imports and check_records are
clean.

**Findings:**
1. **Criterion 5 in Claims: ACCEPTED.** The Claims carry the builder's own re-run: 41 of 48 buckets, the 7 exceptions,
   1-6 sessions a bucket, labelled "some evidence", revisit at 30 sessions. That matches my run.
- **Minor (a): ACCEPTED.** `SPREAD_LABEL` now names the capture period: "spread learned from forward captures since
  13 Oct 2026, measured at 15:00".
