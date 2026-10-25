# Judge 28: story B3, policy runner and verdict

**Verdict: PASS.** All 6 criteria are MET. There are no blocking or should-fix findings and 2 minor findings.

I ran both of the story's "judge verifies" steps:
- **A fresh-checkout re-run:** byte-identical.
- **A recomputation of total net from the per-cycle list:** I did it for all 8 policies and their opposites.

I also went further:
- an independent implementation of protocol sections 6-8: the policies, C2 opposites, bootstrap lower bound, C1's
  95th percentile and criteria 4-6;
- the engine's own `policy_verdict` run on the 33 real discovery opportunities (in memory; discovery never prints a
  verdict).

Every number agrees with mine.

**What I judged**
- **Repository:** trading `main` at 5125fca, which contains B3 commit 79fc685 (merged as f0e2101) and the B1 judge-26
  minors fixed in aa77615.
- **Claims:** `reviews/claude/response_47_2026-10-13-b3-policy-runner.md`.
- **Story:** `docs/stories/B-research-engine.md`, B3.
- **Protocol:** `research/2026-10-12-experiment-1/PROTOCOL.md`, sections 6-8.

## Checks run by the judge

```
$ python -m pytest -q                          795 passed
$ ruff check fno tests tools                   All checks passed!
```

### Re-run in a fresh checkout (story step 1)

```
$ git clone /home/user/trading fresh && cd fresh                 (at 5125fca)
$ sha256sum results_discovery.json                               83dd3d64…7371bef1 (committed)
$ rm results_discovery.json results_discovery.md
$ python -m fno research run 2026-10-12-experiment-1 --period discovery      6.7 s
$ sha256sum results_discovery.json                               83dd3d64…7371bef1   identical
$ git status --short                                             (empty: the .md is identical too)
$ python -m fno research run 2026-10-12-experiment-1 --period challenge
refused: trial 22 has no frozen protocol commit                  exit 2, nothing written
```

### Independent recomputation from the per-cycle list (story step 2, and more)

My script reads only `results_discovery.json`'s `opportunities` (features and each structure's status and net). It
applies section 6's formulas, which I typed from the protocol: `None` means no trade, and non-traded statuses count
0. It imports nothing from `fno`. The bootstrap is numpy `default_rng(20261012)`, one draw of `integers(0, n, (10000,
n))`, with the means sorted and index 62. C1 uses `permutation(n)` per sequence, with sorted action codes taking
consecutive slices, and nearest rank `ceil(0.95 × 10000) − 1`.

| Policy | Total net: judge / engine | Actions equal | Bootstrap lower bound: judge = engine | C2 total: judge = engine | C1 p95: judge = engine | Criterion 4 |
|---|---|---|---|---|---|---|
| P1 | 5,055.33 / 5,055.33 | yes | −1,086.34 | – | – | – |
| P2 | −18,286.42 / −18,286.42 | yes | −1,155.22 | – | – | – |
| P3 | −34,735.27 / −34,735.27 | yes | −1,469.41 | – | – | – |
| P4 | 21,451.56 / 21,451.56 | yes | −155.25 | −16,396.23 | 14,533.27 | > P1 |
| P5 | 15,193.87 / 15,193.87 | yes | −442.73 | −44,873.80 | 9,115.88 | > P1, **not** > P4 |
| P6 | 8,545.01 / 8,545.01 | yes | −450.07 | −3,489.68 | 15,608.20 | > P1, **not** > P4 |
| P7 | −6,602.89 / −6,602.89 | yes | −1,287.25 | 11,658.23 | 15,582.98 | **not** > P1 |
| P8 | −8,847.62 / −8,847.62 | yes | −604.29 | −9,438.80 | −9,957.20 | > P2 |

- **Totals:** they agree within about 3e-6, the file's 6-decimal rounding of each cycle. Every policy's and
  opposite's 33 actions equal mine.
- **Criterion 5 (P5's BF branch):** −6,257.69 from both.
- **Criterion 6 (P6's removed trades):** +12,906.55 from both.
- **Criterion 7:** the largest traded modelled loss of any structure is 9,996.93.

**Reading (in-sample, protocol section 2: reported only, never judged):** under the challenge rules, every policy
would fail on this period, P4 included (bootstrap lower bound −155). That matters before the challenge: even the best
in-sample policy is far from criterion 2 with 33 opportunities.

### Breaks to the verdict code (all reverted; `git status` clean)

| # | Break | Tests failing |
|---|---|---|
| V1 | Criterion 6 `<` becomes `<=` | 1 |
| V2 | Criterion 3 (C1) `>` becomes `>=` | **0** |
| V3 | A policy passes if *any* criterion passes | 2 |
| V4 | C1 percentile taken one rank lower (`ceil(p·n) − 2`) | **0** |
| V6 | Criterion 7 never voids the run | 1 |

**Why V4 survives:** in the golden C1 examples, the sorted totals around rank 9,499 are tied (binary: 3,930, 3,930,
3,930, 3,940 at ranks 9,497 to 9,500; mixed: 5,000 four times). An off-by-one in the index gives the same number.
The engine is correct today: on the real discovery data, whose totals are continuous, its C1 values equal my
independent ones.

## Criteria

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 1 | An unregistered policy stops with "not registered" (via B4) | Tests pass (a temporary git repo with the real `LedgerTrialGuard`; the guard runs before any data load) | MET |
| 2 | Two runs give byte-identical results files | A fresh-clone re-run gives the committed SHA-256, and the `.md` is identical | MET |
| 3 | Golden tests: the bootstrap lower bound to Rs 0.01; C1 p95 exactly, binary and mixed | Tests pass. Their scripts are separate code with the same convention, which is unavoidable because the convention fixes the numbers. Weakness: V4 (minor 1). | MET |
| 4 | A never-trading policy scores 0 and fails criterion 1; counts by status in the results | Test passes; `status_counts` present for every policy in the real file | MET |
| 5 | Each criterion shows its value, threshold and pass/fail; the overall verdict is pass only if all pass | Code read (`Criterion`, `policy_verdict`); V3 caught; the engine's real-data criteria equal mine | MET |
| 6 | The challenge needs a "frozen at commit" line whose commit exists and precedes the run | Real run refused, exit 2; tests for no line, an unknown commit and rules changed after the commit | MET |

## Claims vs reality

- **All numbers in the claims' discovery table:** reproduced.
- **"Discovery needs registration only, the challenge the full freeze":** the code does this, and the reasoning is
  sound (discovery is never judged). The desk should confirm it.
- **"The frozen line cannot hide a rule change":** the test with rules changed after the named commit passes. The
  freeze recipe is explicit.
- **Data access:** the discovery run *parses* the 2023 options file for its index closes and drops every 2023 option
  row before storing anything. This is honestly disclosed. I agree with the builder: use A10's index-close files, so
  that no challenge-period options file is opened at all before the freeze. That makes the attestation simple.

## Protocol text before the freeze (the builder's list): SUPPORTED

The engine and the protocol must say the same thing before B5 freezes. Without these lines, nobody can reproduce the
numbers from the protocol alone. My recomputation needed exactly these conventions:
- Black-76 on the same-expiry future, not Black-Scholes (section 5);
- nearest rank `ceil(0.95n) − 1` for C1 (section 8 criterion 3);
- the exact numpy draws for the bootstrap and C1 (section 7);
- a cycle's P&L belongs to its exit day, and an opportunity to the period of its decision day;
- the longest losing run and drawdown definitions.

These are for the owner and ChatGPT, and they must be in before the freeze.

## Engineering standards

- **Patterns:** policies as data (`RulePolicy` with condition objects); a `TrialGuard` interface; wiring in the
  composition root.
- **Sizes:** all modules small (largest in `research_engine/`: `ledger.py` at 146 lines).
- **Breaches:** none found.

## Findings (minor)

1. **The golden C1 examples cannot detect an off-by-one in the percentile index, nor `>=` against `>`.**
   - **Evidence:** V4 and V2 pass every test; the golden totals are tied around rank 9,499.
   - **Expected:** a golden C1 case with continuous P&L (distinct totals), pinning the value at index 9,499 and
     different from index 9,498. Add a test where the total equals the C1 threshold exactly and the criterion fails.
2. **The discovery run opens the 2023 options file** (rows dropped, nothing kept), honestly disclosed. Expected: once
   A10 lands, read the look-back closes from the index-close files only, before the freeze.
