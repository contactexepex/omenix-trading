# Judge 25: story B2, cycle simulator

**Verdict: PASS.** No blocking or should-fix findings; 2 minor findings.

I agree with both of the builder's data findings. I support the proposal on the long-fly price check, which is a
protocol decision for the owner and ChatGPT.

The story's "judge verifies" step asks me to recompute one real cycle per structure by hand. I did it for three
cycles that the builder did *not* pre-work, chosen to stress the rules. I used my own script, which reads the raw
panel CSV, picks the dates and strikes itself and applies a charges formula I typed from `config.yaml`; it imports
nothing from `fno`. All three match the app to the paisa.

**What I judged**
- **Repository:** trading `main` at bc93cbb, which contains B2 commit 8c2f3e2.
- **Claims:** `reviews/claude/response_45_2026-10-13-b2-cycle-simulator.md`.
- **Story:** `docs/stories/B-research-engine.md`, B2.
- **Protocol:** `research/2026-10-12-experiment-1/PROTOCOL.md`, sections 3 and 4.

## Checks run by the judge

```
$ python -m pytest -q                          713 passed
$ python -m pytest -q tests/research_engine    75 passed
$ ruff check fno tests tools                   All checks passed!
$ python tools/check_imports.py                clean: 158 files
```

### The app's 99 results (my own dump through the composition root)

| | Traded | Net | Wins | Largest modelled max loss | Worst realised | Widths |
|---|---|---|---|---|---|---|
| SF | 33/33 | −Rs 18,286 | 12 | Rs 4,878 | −Rs 4,024 | 300 × 33 |
| SC | 33/33 | +Rs 5,055 | 24 | Rs 9,807 | −Rs 6,298 | 300 × 22, 250 × 9, 200 × 2 |
| BF | 33/33 | −Rs 34,735 | 3 | Rs 9,997 | −Rs 4,634 | 150 × 18, 100 × 15 |

- **Width skipped for a data reason** (`unfillable` or `bad_prices` at a wider width): none.
- **Realised loss above its modelled maximum:** exactly one, SF July 2024 (−Rs 4,024 against Rs 2,886).

Every figure in the builder's claims (sections 2, 3.1 and 3.2) is reproduced.

### Independent hand recomputation of three real cycles

These are my own date rule, my own strike rule and my own charge function.

**SF, expiry 25 Jul 2024** (the builder's anomaly cycle). Decision 10 Jun, entry 11 Jun, exit 4 Jul; spot at
entry 23,264.85.

| Leg | Entry (close) | Exit (close) |
|---|---|---|
| sell 23250 CE | 557.80 | 1,168.65 |
| sell 23250 PE | 363.10 | 36.00 |
| buy 23550 CE | 383.05 | 867.40 |
| buy 22950 PE | 269.15 | 21.85 |

Credit 268.70, so the terminal loss is 31.30 per unit. Entry charges Rs 228.26; worst-case exit charges Rs 103.25;
pads Rs 520.

| | Judge | App |
|---|---|---|
| Modelled max loss | **Rs 2,886.01** | Rs 2,886.01 |
| Gross | −Rs 3,035.50 | |
| Charges | Rs 468.74 | |
| Pads | Rs 520 | |
| **Net** | **−Rs 4,024.24** | −Rs 4,024.24 |

At the exit, the call spread closes at 1,168.65 − 867.40 = **301.25, above its 300-point width**. That is the
builder's finding 3.1, confirmed from the raw rows.

**SC, expiry 25 Nov 2025** (a width-250 cycle). Decision 13 Oct, entry 14 Oct, exit 4 Nov; spot 25,145.50. Body:
25650 CE (nearest 25,648.41) and 24650 PE (nearest 24,642.59).
- **Width 300:** credit 68.65 gives a max loss of **Rs 15,807.13, over the cap**. One wing (25950 CE) was on
  settlement, 1 of 4 legs, which is allowed.
- **Width 250:** credit 120.85 gives a max loss of **Rs 9,161.14**, which fits; the app also gives Rs 9,161.14.

| Leg | Exit |
|---|---|
| 25650 CE | 311.95 |
| 24650 PE | 35.40 |
| 25900 CE | 191.75 |
| 24400 PE | 23.10 |

Gross −Rs 757.25, charges Rs 275.80, pads Rs 520, **net −Rs 1,553.05**; the app gives −Rs 1,553.05.

**BF, expiry 24 Feb 2026** (the builder's "debit at least the width" case). Decision 12 Jan, entry 13 Jan, exit
3 Feb; spot 25,732.30; ATM 25750.

| Width | Debit | Max loss | Fits? |
|---|---|---|---|
| 300 | 266.30 | Rs 18,106.86 | no |
| 250 | 226.20 | Rs 15,505.37 | no |
| 200 | 189.40 | Rs 13,117.96 | no |
| 150 | 144.85 | Rs 10,227.77 | no |
| 100 | **101.10** | **Rs 7,389.48** | yes (app: Rs 7,389.48) |

Gross −Rs 406.25, charges Rs 384.42, pads Rs 520, **net −Rs 1,310.67**; the app gives −Rs 1,310.67.

A long iron fly pays at most its width at expiry. A debit of 101.10 for a 100-point fly cannot win at any index
level, so the builder's question in section 4 is real.

### Criterion 7: all 33 cycle dates, recomputed with my own rule from the calendar CSV

```
distinct meeting-1 cycles 33, mismatches 0
app cycles 33 equal to meeting 1 (expiry, entry -> decision, exit): True
```

### Do the tests bite? Eight deliberate breaks

All reverted; `git status` clean.

| Break | Tests failing |
|---|---|
| M1: "more than half on settlement" becomes "half or more" | **0 (survives)** |
| M2: ATM tie goes to the higher strike | 1 |
| M3: SC call tie goes to the lower strike | 1 |
| M4: charges on the raw price instead of the filled price | 4 |
| M5: exit at 20 days instead of 21 | 6 |
| M6: widths tried smallest first | 7 |
| M7: settlement price used even when the leg traded | 11 |
| M8: worst-case exit charges dropped from the max loss | 4 |

## Criteria

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 1 | Hand-worked SF, SC and BF match to the rupee | The tests pass, and their charges fixture is written independently of `fno/costs.py` (I read it). My three real-cycle recomputations match to the paisa. M4 and M8 are caught. | MET |
| 2 | Zero volume uses settlement, flagged; 3 of 4 flagged is `unfillable` | Tests pass; M7 caught. The exact-half boundary is untested (M1, minor 1). | MET |
| 3 | A credit equal to the width is `bad_prices` | Test passes. As written, the rule checks only "cannot lose"; see the protocol point below. | MET |
| 4 | Only 150 fits, so 150 is used; none fit gives `no_trade_cap` | Tests pass, and M6 is caught. On real data, my BF Feb 2026 recomputation walks 300 → 100 with each loss over the cap. | MET |
| 5 | Every traded cycle's modelled max loss is at most Rs 10,000; a realised loss above it is reported | 99 of 99 are within the cap (largest Rs 9,997). The one realised loss above its model is reported and pinned by a test, not hidden. | MET |
| 6 | Tests for ties, an unlisted wing, a zero price and a holiday window | Tests present and passing; M2 and M3 caught | MET |
| 7 | 2024-26 dates equal meeting 1's with next-day entry | My own recomputation: 33 of 33 | MET |

## Claims vs reality

- **All numbers in sections 2, 3 and 6:** reproduced by my dump, and three cycles reproduced by hand.
- **"Access attestation: only 2024-26 read":** consistent with the code (`read_nifty_panel(..., (2024, 2025, 2026),
  cycle_rows)` in the real tests). My own recomputation also read only 2024-26 files.
- **Signature differences from the story** (the calendar injected; `CycleSimulator` with `CycleTerms`): stated, and
  sound. They follow the project's dependency-injection rule.
- **Not stated:** the strikes are chosen from the **entry day's** spot and chain (`simulator.py`: `session_on(entry_day)`).
  The protocol does not say which day chooses the strikes. Choosing at the entry close, where the fill is priced, is
  coherent, but it is a protocol choice and should be written down (minor 2).

## The builder's findings: decisions

| Finding | Judge's check | Decision |
|---|---|---|
| 3.1: SF July 2024 realised −Rs 4,024 above the modelled Rs 2,886, from exit closes breaking the width bound | Raw rows confirm a 301.25 spread on a 300 width. The cap rule as written bounds only the terminal payoff, as the builder says. | AGREED (strong evidence: raw data) |
| 3.2: discovery numbers (SF −18,286, SC +5,055, BF −34,735) | Reproduced exactly | AGREED, numbers only. They are in-sample (meeting 1 already saw this period), so they carry no evidence of profit. |
| Section 4: `bad_prices` should also cover a long debit at least the width ("cannot win") | Feb 2026 recomputed (debit 101.10 at width 100). A long iron fly's terminal value is at most W, so the trade cannot win. | **SUPPORTED** (strong evidence: arithmetic plus data). A protocol change for the owner and ChatGPT, before the freeze. |

**Judge's addition to the protocol question (reasoning only).** Finding 3.1 is the exit-side mirror of the same
problem: a closing spread worth more than its width is an impossible price, just as a credit at least the width is
at entry. The protocol could flag exit prices that break the width bound (report them, not drop them), so B3 can show
how much of a result rests on such closes.

## Engineering standards

- **Sizes:** five modules, 49 to 124 lines, 880 lines in all.
- **Patterns:** an interface plus template for the structures; injection through `CycleTerms`; wiring only in
  `fno/composition.py`.
- **DRY:** existing pieces are reused (A3's panel reader, A5's `monthly_as_of`, A1's calendar, `fno.costs`).
- **Status values:** `CycleStatus` is an exhaustive `StrEnum` in `fno/constants.py`.
- **Breaches:** none found.

## Findings (minor)

1. **The "more than half of the legs on settlement" boundary is not tested.** Changing it to "half or more" (M1)
   passes all 75 tests. No 2024-26 cycle has exactly 2 of 4 legs on settlement (only SF Sep 2024 has 1), so today's
   results do not change, but the 2019-23 challenge period may hit it. Expected: a test where 2 of 4 legs are on
   settlement and the cycle trades.
2. **The day that chooses the strikes is not written in the protocol or the claims.** The code uses the entry day's
   spot and chain. Expected: one line in protocol section 4 (or the story) stating it, so B3 and any re-run use the
   same rule.
