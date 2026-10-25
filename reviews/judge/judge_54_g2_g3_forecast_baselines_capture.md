# Judge 54: stories G2 (frozen baselines) and G3 (Book 1 capture)

**Verdict: G2 PASS. G3 PASS as built.**
- **G3's limit:** G3 cannot forecast live today. The frozen G1 protocol (section 1) allows no live forecast until E2
  exists, and no daily closes after 12 Oct are in the repository. Both are known gaps for ChatGPT and the owner, not
  builder defects.
- **G3's daily job has not run yet.** Its first real record waits for the next trading day.
- **Minor findings:** 1.
- **Cross-story impact:** G2's back-fill exposes 2019-2023 outcomes. That is recorded in judge 53 for experiment 1's
  freeze.

**What I judged**
- **Repository:** trading at 011f5aa.
- **Claims:** `reviews/claude/response_62_g2-g3.md`.
- **Stories:** `docs/stories/G-forecasts.md`, G2 and G3.

## Checks run by the judge

```
$ python -m pytest -q tests/forecast                 68 passed
$ python -m fno forecast backfill --check            back-fill unchanged (recomputed, byte-equal)
```

**My look-ahead plant:** the base rate counts an outcome resolved **on** `d` (`<=` for `<` in `history.py:79`).
**Caught** (1 failing). The protocol says an outcome counts only if resolved before `d`'s cutoff, and it does.

**My hand check (lognormal fixture):** S0 100, σ 20%, τ 28/365, no carry.
- spread = 0.2 × √(28/365) = 0.055386.
- m = −σ²τ/2 = −0.04 × 0.076712 / 2 = **−0.001534**.
- Q1 = N(−0.001534 / 0.055386) = N(−0.0277) = **0.4890**. Q2 = 1 − N(0.5613) + N(−0.5222) = **0.5881**.
- Both equal the asserted values. See minor 1 on the docstring.

## G2 criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | A look-ahead test proves no baseline uses data after its cutoff | B1's harness on real days (15 values unchanged); my `<=` plant caught | MET |
| 2 | Each baseline reproduces hand-computed values | My lognormal values above; the risk-neutral carry ln(22,050 / 22,000) / (16/365) = 0.051788; the base-rate window example; OLS recovered exactly | MET (minor 1) |
| 3 | The refit schedule is fixed; a refit uses only earlier data | First trading day of each month; harness test with every later value changed | MET |
| 4 | Every value labelled with method and version | `<baseline>/v1/close-proxy/iv30:<state>`; Book 1 carries its method file's SHA-256 | MET |

## G3 criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | Five probabilities per session day, or a recorded "no forecast", never imputed | Tests: a trading day gets 5 records; a closed day none; a record is written once. Today the records are "no forecast … no-live-inputs" under the frozen protocol. | MET (first real run pending) |
| 2 | Book 1's method is identical on every day of a version | The method hash is in every record. The back-fill check shows Book 1 = the mean of the two baselines on all 9,605 day-question pairs. | MET |
| 3 | Forecasts committed after the deadline are ignored | Deadline 15:30 IST, tested at 15:12 and at one second past. The capture runs G1's freeze check first, and the workflow uses `fetch-depth: 0`. | MET |

**Agreed with the builder:**
- **Not overriding the frozen protocol** to read the A4 snapshot was right. The protocol says no live forecasts until
  E2.
- **The v2 proposal goes to ChatGPT:** the A4 snapshot by 15:00, closes to d−1, and the 15:00 spot standing in for
  d's close, as B7's live F1 does.
- **The closes gap is real:** a daily NSE index-close download is needed before any live base rate or model is
  current.

## Minor 1: the hand-worked docstring is wrong

- `tests/forecast/test_baselines.py::test_lognormal_probabilities_by_hand` writes m = −0.000767 and "Q2 = 1 −
  N(0.5475) + N(−0.5360)". The correct m is −σ²τ/2 = **−0.001534**, so the z-values are 0.5613 and −0.5222.
- The assertions compute m correctly and pass. Q2 is about 0.588 either way, which is why the tolerance hid it.
- The docstring's own m would give Q1 = 0.4945, not the asserted 0.4890.
- **Expected:** correct the comment, because a hand-worked value that does not match its own arithmetic misleads the
  next reviewer.

## Cross-story impact (see judge 53)

- The back-fill (`5632bfc`) holds challenge-period Q1-Q5 probabilities, and its base-rate column reveals individual
  2019-2023 outcomes.
- That is legitimate for G4's evaluation, but experiment 1 is not frozen yet. Its access record must list this file
  and the judge's views, and experiment 1 should be frozen before anyone opens those rows again.
