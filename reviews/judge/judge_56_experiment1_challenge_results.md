# Judge 56: experiment 1 challenge results (2019-2023): no policy passed

**Verdict: the results are VALID as reported.**
- **Frozen engine:** the run came from the frozen engine.
- **Deterministic:** my own re-run there is byte-identical.
- **Recomputed:** P1, P2 and P3 totals and their bootstrap bounds equal my recomputation to the rupee.
- **Verdicts:** every pass or fail follows the frozen criteria.
- **Anomalies:** reported and quantified, never repaired.

**Conclusion (strong evidence for this test):** none of the 8 policies passes, so nothing from experiment 1 goes to
paper trading.

**What I judged**
- **Repository:** trading `a074eb9`: `research/2026-10-12-experiment-1/RESULTS.md`, `results_challenge.json/.md`,
  and the ledger.
- **Claims:** `reviews/claude/response_64_experiment-1-results.md`.
- **Frozen protocol:** `9d16431` (freeze `c52a6b8`, run commit `0c1c957`).

## Run provenance and determinism (my checks)

| Check | Result |
|---|---|
| `0c1c957` against `c52a6b8` | only `research/ledger.csv` differs (the protocol-commit step the guard needs) |
| A fresh worktree of mine at `0c1c957`: `sha256sum -c` of FREEZE.md's 45 files | **45 of 45 OK** (judge 53's condition met) |
| My re-run: `python -m fno research run 2026-10-12-experiment-1 --period challenge` in that worktree | `results_challenge.json` SHA-256 **`4826897e…`**, byte-identical to the committed file (24 s). The worktree was removed afterwards; nothing of mine was committed. |
| numpy | 2.5.3, as frozen |

## Recomputed from the results file

**Every traded structure's net equals gross − charges − pads:** 0 mismatches over all 60 opportunities.

| Policy | My total (no trade = 0) | Reported | My bootstrap lower bound (seed 20261012, `integers(0, 60, (10000, 60))`, sorted, index 62) | Reported |
|---|---|---|---|---|
| P1 (SC) | **−34,485.57** | −34,485.57 | **−1,783.1446** | −1,783.1446 |
| P2 (SF) | **−58,218.56** | −58,218.56 | **−1,782.5065** | −1,782.5065 |
| P3 (BF) | **+24,119.64** | +24,119.64 | **−612.7717** | −612.7717 |

**Verdicts against §8 (my script):**
- For all 8 policies, every criterion's `passed` equals its rule applied to its value: **0 inconsistencies**.
- Each policy fails at least one criterion: P1, P2 and P8 on 1 and 2; P3 on 2 only; P4 and P7 on 1, 2 and both parts
  of 3; P5 and P6 on 1, 2 and 3's random-timing control.
- `overall.passing_policies` is empty.
- **Criterion 7 holds:** the largest modelled maximum loss of any traded structure is **₹9,951.69**, at or below
  ₹10,000.

## Anomalies: reported, not repaired (§4)

**Impossible exits.** The `exit_outside_payoff` flag marks **7** traded results (SC 1, SF 2, BF 4). My sums without
them:
- SC **−23,139.73**
- SF **−42,703.25**
- BF **−2,642.49**

All equal RESULTS.md. So P3's only positive total rests on those exits, as stated.

**The 9 May 2019 case, checked in the panel** (now allowed: the run is done):
- NIFTY 11,301.80.
- The 11550 put closed **415.25 on 45 contracts**. The 11250 put did not trade, so its settlement of 107.35 was used.
- The spread is therefore 307.90, wider than the 300-point width. That is impossible at expiry and possible only with
  a stale close, as reported.

**What was not done, correctly:** the frozen protocol is not edited. The realised losses above the cap (11,346 and
13,728) are investigated in the text. The run is not voided, because criterion 7 concerns the modelled maximum, which
held.

## Notes (reasoning only)

- **The verdict does not depend on the anomalies:** without the flagged exits every policy is negative, and the
  no-settlement sensitivity is negative too.
- **Pre-freeze exposure (judge 53)** could only have flattered a pass. There is none, so it does not change this
  result.
- **For any next experiment:** exits priced from stale last trades of thin contracts are the weakest input. A
  liquidity floor or quote-based exits belong in a new protocol, never in this one, as RESULTS.md says.
