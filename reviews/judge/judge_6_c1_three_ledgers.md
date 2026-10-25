# Judge 6: story C1, cost and tax accountant (three ledgers)

Verdict: **FAIL**. There are 0 blocking, 1 should-fix and 4 minor findings. The code is correct on every hand
check I made. The FAIL is for an acceptance criterion whose own test requirement is missing.

**What was judged:** `main` at 7846936, story commit e8b6823 (12 Oct 2026). I read in full `fno/accounting/ledgers.py`
(140 lines), `tests/accounting/test_ledgers.py`, `accounting/*.csv` and `fno/costs.py`.

**There is no builder claims file for C1.** No `reviews/claude/response_*` names it. The only claim is in
`conversations/2026-10-12.md` (about line 1520): "trade ledger with pads and every charge from the one charges model;
account ledger by month after operating costs; tax as an assumed scenario on the April-March year, deductible
categories declared ...; no carry-forward modelled; reconciliation check; 7 tests including the worked example". I
judged from the story, that claim and the code.

## Checks run by the judge

```
$ python -m pytest -q tests/accounting      7 passed
$ python -m pytest -q                       (full suite passes; see later verdicts for counts)
$ ruff check fno tests tools                All checks passed!
$ python tools/check_imports.py             clean
```

**Story's "judge verifies" step: one month's three ledgers recomputed by hand.** The repository has no trades and
an empty `accounting/operating_costs.csv`, so I built the month myself. It has two trades and three cost rows. The
cost rows are `ai` 1,200, `other` 300, and `AI` 500, a case typo. The charges are from `config.yaml`, recomputed by
my own formula: brokerage 20 per order; STT 0.15% on sell premium; exchange 0.03503%; SEBI 10 and IPFT 50 per
crore; stamp duty 0.003% on buys; GST 18% on brokerage + exchange + SEBI + IPFT.

```
iron-fly trade (4 legs, pad 1): hand net 918.64, code net 918.64
month 2026-11: trade_net -1,803.93; operating_costs 2,000.00; account_result -3,803.93   (hand: -3,803.93)
FY 2026-27: tax_base -3,003.93 (hand, only "ai" deductible: -3,003.93); tax 0.00
```

The "AI" row (wrong case) was silently treated as not deductible (finding 3). A tampered tax base makes
`reconciles()` return False, so the check works, but no test shows it (finding 1). A header with wrong columns and
no rows is accepted (finding 4).

## Criteria

| # | Criterion | Builder's claim | Judge's own evidence | Result |
|---|---|---|---|---|
| 1 | Known-answer year: trade net 12,000, account 9,000, tax base 9,000, tax 2,808, each separate and labelled "assumed scenario" | Worked example tested | `test_the_known_answer_year_from_the_story` checks every number and the label; `tax_by_year()` keeps each value under its own key (`ledgers.py:118-125`). It is a library result only: nothing prints or publishes the three ledgers yet (finding 5). | MET |
| 2 | The ledgers reconcile; **a test fails if they do not** | "reconciliation check" | `reconciles()` (`ledgers.py:128-140`) compares month totals with the trade and cost totals, and each year's account result and tax base with their definitions. My tampering makes it return False. **No test ever feeds it a non-reconciling ledger**, so the part "a test fails if they do not" is unproven by the suite. | PARTLY |
| 3 | Losing year: tax 0, loss shown, no carry-forward (note) | Tested | `test_a_losing_year_...`: tax 0, base -5,000, note present | MET |
| 4 | Charges per trade equal `fno.costs` for every leg; pads separate | Tested | Test plus my hand recomputation (918.64 = 918.64); pads are a separate field; charges are computed on the fill price | MET |
| 5 | Financial year April-March (31 Mar 2025 in FY 2024-25) | Tested | `financial_year` and its test, both boundary days | MET |

## Claims vs reality

- **"7 tests including the worked example"**: true (7 passed).
- **"reconciliation check"**: exists and works on my tamper. It is untested in the failing direction (finding 1).
- **"every charge from the one charges model"**: true (`order_charges_breakdown`).
- **Design text names a `TaxModel`, `TradeLedger` and `AccountLedger`**: the code has one `Ledgers` class plus
  `trade_line`. That is acceptable at 140 lines (KISS); noted only because the story's expected design differs.

## Project rules and engineering standards

- **Size:** 140 lines, under 350.
- **Interfaces:** none needed.
- **Repeated strings:** the side strings "buy" and "sell" are typed in `ledgers.py` and again in
  `fno/books/fills.py`. This is the same point as judge 1 finding 4; they belong in `fno/constants.py` (finding 2).
- **Secrets:** none.
- **Money safety:** no price is invented. The sell fill price is floored at 0, and the pad then counts only up to
  the quoted price.

## Findings

1. **Should fix.** Criterion 2 requires that "a test fails if they do not" reconcile; no such test exists.
   Expected: a test that builds a ledger whose account result or tax base disagrees with its parts (as my tamper
   did) and asserts `reconciles()` is False. Add a cross-check that each financial year's totals equal the sum of
   its months.
2. **Minor.** The side values "buy" and "sell" are typed in two modules. Expected: one constant in
   `fno/constants.py`, used by `ledgers.py` and `books/fills.py`.
3. **Minor.** An operating-cost category missing from `deductible_categories.csv` is silently treated as not
   deductible. This includes a case typo ("AI" vs "ai"). The error is in the safe direction (more modelled tax), but
   it is silent. Expected: refuse an unknown category, or report it, with a test.
4. **Minor.** `read_operating_costs` checks the columns only row by row, so a header with wrong columns and no rows
   is accepted. Expected: check the header itself.
5. **Minor (for P stories, not C1's code).** Nothing yet shows the three ledgers to the owner (no CLI, report or
   publish path). The story's goal, "every result shown in three ledgers", is only reached when a report uses
   `Ledgers`. Expected: the reporting stories (P2/P3, S) wire it in.

**Unverified, outside C1:** `config.yaml` says "stt_sell_pct: 0.15 ... raised from 0.1% by Budget 2026, from 1 Apr
2026". I could not verify this from any source available to me. One charges table is used for every trade date, so
historical research trades are charged today's rates. That is conservative while today's rates are higher, but it
should be stated where research results are reported. The owner may want this rate confirmed from an official
circular.
