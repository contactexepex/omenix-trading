# Judge 174: C2c, the stressed margin on the whole margin, story text (judge G)

- **Judged:** `story/c2c-whole-margin-stress` at `3b4342c0853bb5bede37daba6ea090a9de652ac4` (builder session
  01Vm1WnH8i9waM8EJG8zwWqg). This is lane 1, money and risk, at quality rule 1 (story text before code). The change is
  the C2c section of `docs/stories/C-code-roles.md` plus one work-register row. 174 was the next free number on main.
- **Owner's decision:** DESK_DECISIONS row 203 (commit d68b1a9c): "Crash buffer applies to the whole margin" (owner:
  "Whole margin (Recommended)"). The story implements exactly that, and nothing more.
- **Verdict: FAIL (text).** One should-fix: criterion 2 contradicts the STR1 cap on the credit spreads. There are also
  3 minor findings. The formula, the figures and the C4 scope are right, so the fix is one sentence.

## What I checked

1. **The formula, by algebra (strong evidence).** New: `max(0, k·scan − NOV) + min(0, NOV) + k·exposure`.
   - **Credit row (NOV < 0):** `k·scan − NOV + NOV + k·exp = k(scan + exp) = k·initial()`. Exact.
   - **Debit row (NOV ≥ 0), k ≥ 1:** `k·scan − NOV ≥ k·scan − k·NOV`, so `max(0, k·scan − NOV) ≥ k·max(0, scan − NOV)`,
     and the result is never below `k·initial()`.
   - The premium term `min(0, NOV)` is still never multiplied, as judge 75 requires. At entry, the formula drops
     `min(0, NOV)`, as today.
2. **The 14 Oct figures.** I recomputed every row of `tests/risk/fixtures/margins_2026-10-14.csv` (NSE SPAN
   `nsccl.20261014.i1.zip`), uncapped, at k = 1.45. All four table rows match to the paisa:

   | Row | Broker | Stressed today | After C2c | At entry today | At entry after C2c |
   |---|---|---|---|---|---|
   | SF 100 | 59,899.32 | 60,269.33 | 86,854.01 | 66,340.33 | 92,925.01 |
   | SF 300 | 62,679.37 | 64,300.40 | 90,885.09 | 81,434.40 | 108,019.09 |
   | SC 300 | 67,594.67 | 71,427.59 | 98,012.27 | 81,580.59 | 108,165.27 |
   | BF 300 | 59,077.07 | 59,077.07 | 85,661.75 | 59,077.07 | 85,661.75 |

   The context's claim that the scan is 1-14% of the margin and that k adds +0.6% to SF 100 and 0% to every BF row
   today is right (SF 100: 60,269.33 / 59,899.32 = +0.62%).
3. **The STR1 cap stays on the SPAN part only.** The code caps only `_span` (`fno/risk/margins.py:103-107`) and
   `stressed_per_lot` (`fno/checks/validity_margin.py:93-95`). Keeping the exposure outside the cap is sound: NSE
   charges exposure on the short legs' notional, even inside a spread, so it is not bounded by the spread's maximum
   loss. This is reasoning, but consistent with how the broker computes the figure.
4. **Never below the broker's unstressed figure.**
   - Capped span ≥ broker span (the `max(broker, ·)`), and `k·exposure ≥ exposure` because settings refuse k < 1.
   - So the total is at least `initial()` for every code.
   - LC and LP (exposure 0, cap 0) are unchanged at their broker figure. This holds on the real rows.
5. **C4's independent copy.** The story names `validity_margin.stressed_per_lot`. It is the only other place that
   computes the stressed margin: `grep` finds no other consumer of `scan_per_lot_rs`, `.stressed(` or `at_entry(`
   outside these two modules except `rules.py`, which goes through `StressedMargin`. Criterion 3 requires C2 = C4 on
   every planted row, plus the three mutations in both copies. That is complete.
6. **The `record()` label and its pinned test.**
   - Today `margins.py:181` writes `"stresses": "scan risk only (judge 75)"` and `tests/risk/test_manager.py:55` pins
     it. The value describes the method, so changing it with the method is legitimate.
   - The new pin in criterion 5 is still an exact string, so the test is not weakened.
7. **Order and the register.** C2c goes before STR1b-2, which has not started. The register row is added and no other
   session owns `fno/risk/margins.py`. The owner-impact note (about a third fewer lots for the same capital) is stated
   plainly.

## Findings

### Should fix

1. **Criterion 2 contradicts the STR1 cap on CCS and PCS.**
   - The text says "for a credit structure this is exactly k × (what C2 counts)". Criterion 2 then tests "for credit
     rows C2's stressed figure equals `k x initial()` ... over every structure and width".
   - But CCS and PCS are credit rows with the STR1 cap. On the real 14 Oct rows the cap binds and the broker's span is
     kept. For example, CCS 300: the cap is `300 × lot − 11,306.75`, below 11,200 for a lot of 65 or 75, while the
     broker span is 20,736.30.
   - So the stressed figure is 9,429.55 + 1.45 × 29,538.53 = **52,260.42**, against k × initial = 56,503.72.
   - A builder following criterion 2 must either break the cap or fail the test. Criterion 4 says the cap stays, so
     the two criteria conflict.
   - **Fix:** criterion 2 covers uncapped credit rows (SF, SC). For CCS and PCS, state "at least `initial()` and at
     most `k × initial()`", with the CCS 300 figure above as a known answer at the real lot size.

### Minor

2. List in the claims every existing pinned figure in `tests/risk/test_margin_formula.py` and C4's margin tests that
   changes, each with its recomputation. A changed expected value then reads as a recompute, not a loosened test.
3. Also update the `capital.py` text "The owner's factor k stresses the scanning risk" (it is in scope as "the
   `capital.py` text"). The cap's rationale ("money it cannot lose a second time") is unchanged and still right for
   the SPAN part.
4. Criterion 1 could add one capped STR1 row, the CCS 300 above, so the real-row test covers the cap together with the
   stressed exposure.

## Project rules

- **Money safety:** nothing becomes looser. Every stressed figure rises or stays the same, and no figure falls below
  the broker's.
- **Scope:** no order path and no change to k's value, which belongs to A14c (judge 173). The change is a small,
  proportionate story, with no new class and no new pattern (row 156).

## Addendum 1: re-judge at `8a9a23e945c417cda528e3c4ca7388a77f3da66e` (judge G)

**Verdict: PASS (text).** The should-fix and all three minors are accepted, each checked against the data. The fix
reached me from the builder. I re-judged it as part of the judge and builder loop and report the verdict to the
orchestrator.

| # | Fix | Re-judge |
|---|---|---|
| 1 (should fix) | The intro and criterion 2 now give exact `k × initial` only for uncapped SF and SC, "not below" for BF, and "between initial and `k × initial`" for CCS and PCS, with 52,260.42 as the known answer | **Accepted.** I recomputed with lot 65 (`config.yaml` `lot_sizes: NIFTY: 65`). CCS 300: cap 8,193.25, 52,260.42 against 56,503.72. CCS 100: 45,788.37 / 47,119.24. PCS 300: 54,044.67 / 59,090.88. PCS 100: 46,394.17 / 47,997.65. All four lie between `initial()` and `k × initial()`. The builder's numbers are exact |
| minor 4 | CCS 300 (capped) added to the table and to criterion 1 | **Accepted.** Broker and stressed today are both 38,968.08, because the cap keeps the broker's span: 20,736.30 − 11,306.75 + 29,538.53. At entry after C2c: 20,736.30 + 1.45 × 29,538.53 = 63,567.17. Both checked |
| minor 2 | New criterion 6: the claims list every changed pinned figure with its recomputation | **Accepted** |
| minor 3 | The `capital.py` text change is named in scope | **Accepted** |

- CDS and PDS (debit, cap 0) equal `k × initial()`, so they also meet criterion 2's debit clause.
- The branch head `67a254e2` adds only `reviews/claude/response_163` and its README row (`git diff 8a9a23e9 67a254e2
  --stat`). The story text is unchanged.
- Next, under quality rule 9: ChatGPT's review before code.
