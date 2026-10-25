# Judge 508: CI's two red tests (story/ci-two-red-tests at b958b5a7)

**Verdict: PASS (lane 1: a forecast-record test's comparison). Merge: pull, one full run on the merged tree, push.**
It changes tests only, plus a register row; no `fno/` code, and the committed back-fill file is untouched.

## Findings and evidence
1. **NSDL alert test: fixed at the root.** The alert reads `GITHUB_SERVER_URL`, `GITHUB_REPOSITORY` and
   `GITHUB_RUN_ID` (`fno/alerts/run_location.py`). The test now clears them and covers both cases. It passes with
   those variables set to an Actions run (16 of 16 in the two files). Strong evidence.
2. **Back-fill check: the cause holds up, re-derived here.** `norm_cdf` is `0.5*(1+math.erf(x/√2))`
   (`fno/analytics.py:14`). On my glibc 2.39, `math.erf` differs from a correctly rounded erf (mpmath at 200 bits) on
   4.7% of 20,000 random inputs, never by more than 1 ULP. CORE-MATH's erf in glibc 2.43 is correctly rounded, so a
   1-ULP last-bit change in about 1 call in 10 is what its arrival predicts. The builder measured 10.7% on the real
   inputs. That moves a probability by at most about 2e-16, matching the claimed maximum of 2.2e-16 on 215 of 38,560
   records. Some evidence: I could not run glibc 2.43 here; the builder's run under its loader is the direct proof.
3. **It is not masked drift.** Every other column is still compared exactly, the header and the row count are
   checked, and "no forecast" stays exact. The guard tests fail on each of these:
   - a probability moved by 1e-9;
   - a forecast appearing where there was none;
   - a changed date;
   - a missing row.

   My mutation, the tolerance loosened to 1e-6, fails the 1e-9 guard (1 failed). Strong evidence.
4. **1e-12 is tight enough.** It is about 4,500 times libm's 2.2e-16 and far below anything a changed input, rule or
   day can move. A real method change shows in other fields or by orders of magnitude more. Reasoning only.

## Gates
On b958b5a7 merged with today's `main` (no conflicts), one run:
- 11,920 passed, 16 xfailed, 0 failed;
- `ruff check` clean; 2,136 files formatted;
- imports clean; record scan clean (8,396 files).

## Answer to "does anything else in production byte-compare a recomputation": yes, one
`python -m fno forecast-scores replay --day D` (`fno/forecast_scoring/replay.py:57`, G1 protocol v3) recomputes a live
day and compares `forecasts.csv` byte for byte. The live captures run on GitHub's `ubuntu-latest` runner, which has
used glibc 2.43 since 21 Oct, while a cloud session like mine has glibc 2.39. So a replay of a day captured since then,
run here, can falsely report "not reproduced" on an erf-based probability.

It is a hand-run audit command, not a test or a scheduled step, so it does not block this branch. Its owner (G1 or
G4's scoring) should compare probabilities with the same 1e-12 tolerance, or record the libm version with each
capture. Also checked: the money checks' erf (`fno/checks/validity_pricing.py`) already compares with tolerances;
Drive's write-once store names back-fill files by content hash, so a recomputation makes a new file, never a
conflict.
