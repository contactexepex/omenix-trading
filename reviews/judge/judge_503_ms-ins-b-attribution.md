# Judge 503: MS-INS part b, the P&L attribution

**Scope:** story/ms-ins-attribution at f5d30e50 (builder session_01LH7m9r5TCAKgZbeHVYkiTD), diff a2c26465..f5d30e50
(code to 0467b66f, then story text). Story MS-market-school.md INS-b and "INS-b Claims". Lane 1, one judge.
Round 1 of 2. Judge K (session_019ZApRwkUiNMKDsf1k4W44z).

**Verdict: FAIL.** 1 should-fix, 1 minor. The method, the Greeks and the hand numbers are right. A net that its own
fills don't support is silently put into the residual.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Hand-computed spread to Rs 0.01 | MET | I re-derived entry Greeks by hand: d1 0.0240, put delta -0.4904, gamma 0.008310, vega 95.71, theta -166.20; T0 = 21 x 1440 + 28 = 30,268 minutes |
| 2, 3 | Pure forward move / pure time step | MET | tests; plants on theta's time sign and Greeks at the step's end caught |
| 4 | Identity on fixture and 200 random paths | MET by construction | holds only when the net is the fills' cash: finding 1 |
| 5 | Step merging | MET | incomplete middle points and closed-road sessions both counted (plants caught) |
| 6 | Unsolvable IV to the residual | MET | `iv_unsolved` plant caught |
| 7 | Settlement last step | MET | intrinsic at settlement, vega 0; call/put intrinsic swap caught |
| 8 | Poor fit at Rs 200 and 25%, boundaries | MET | `>=` and `or` plants caught |
| 9 | One snapshot: costs only | MET | test |
| 10 | Sign of q / end Greeks fail test 1 | MET | both plants caught |
| - | Corrected trade attributed once | MET | `test_corrected.py` through a's real resolver |
| - | Gates | MET | see Notes |

## Findings
1. **Should-fix: the outcome's `net` is trusted without checking it against its own fills.**
   - `residual = outcome.net + charges + spread - parts.total` (`attribute.py:83`). The residual equals mid-to-mid
     P&L less the Greeks only if `net == entry.cash + exit.cash`. Nothing checks that, and no part on `main` builds
     `OutcomeRecord`s yet (j will).
   - My run: the hand-test path (true net -275.18, residual +5.41) with its net moved by Rs -500 is still
     attributed, with residual -494.59. A smaller error (under Rs 200) is not even `poor_fit`.
   - Part c reads the residual for its causes, so a bad record becomes a wrong lesson. That is the "never a guess"
     rule INS-a holds for every other input.
   - Expected: a path whose net differs from its fills' cash by more than Rs 0.01 is not attributed (or is marked as
     a data fault for c), with a test. If the net is meant to differ (pad, other costs), the story says by what, and
     the code accounts for it.

**Minor (fix with the round):** `attribute.py`'s module docstring still says costs come from the record's
`slippage_vs_mid`. The code and the story now measure the spread from the fills.

## Plants
20 planted, 18 caught. Survivors:
- Plant 5 (vega at expiry taken from `end_sigma` when present) is equivalent: a settlement point has no sigma.
- The net check is absent, so there was nothing to plant (finding 1).

Caught: leg sign, end-of-step Greeks, half gamma, theta time sign, both poor-fit boundaries, closed-road merges,
exit spread, complete-point filter, `iv_unsolved`, `closed_on` from entry, theta rate term, undiscounted delta,
15:00 close, `started_at` time, 365.25 days, swapped intrinsic, forward day count, NaN mid.

## Notes
- **Gates (my run, python3 after routine setup):** pytest -n auto 11,814 passed, 16 xfailed. ruff check and format,
  check_imports and check_records are clean.
- The deviation (wrapping B1's `Black76` directly for minutes) is accepted by the orchestrator's ruling and keeps one
  pricer. The integer-day parity forward is negligible, as `points.py` says.
- INS-e criterion 8 (orphan corrections counted and alerted) records judge 501.1's minor; no code yet, as stated.

## Addendum 1: round 2 at e1fdbca0

**Verdict: PASS.** Lane 1, one judge. Scope: the single commit f5d30e50..e1fdbca0.

| Round-1 finding | Result | My evidence |
|---|---|---|
| SF1 net trusted | ACCEPTED | `net_matches_fills` (`contracts.py:80`) requires net = entry.cash + exit.cash to Rs 0.01. The reader adds `net_mismatch_fills`, and `attribute` returns None. My round-1 probe (net moved by Rs -500) now gives None. Plants caught: the check removed from `attribute`, the check removed from the reader, a strict `<` tolerance, and exit cash dropped from the sum |
| Minor docstring | ACCEPTED | it now says the spread is measured from the fills and `slippage_vs_mid` is not read |

- **Side effects checked:**
  - The fixtures' nets are now their fills' cash, so the hand test's numbers are unchanged.
  - The `test_reader.py` split keeps 88 instructor tests (my run: 88 passed). The largest test file is 197 lines.
- **Gates (my run):** pytest -n auto 11,821 passed, 16 xfailed. ruff check and format, check_imports and
  check_records are clean.
