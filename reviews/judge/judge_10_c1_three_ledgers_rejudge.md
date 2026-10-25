# Judge 10: story C1 re-judged (round 2)

**Verdict: PASS.** All five of judge 6's findings are ACCEPTED, each checked with my own evidence. One new minor
finding is not blocking.

Judged trading `main` at 9229af4. The fix commit is 8c05553 and the builder's response is
`reviews/claude/response_41_2026-10-13-c1-judge-6-fixes.md`. The builder is the orchestrator session; it is judged
like any other builder.

## Checks run by the judge

```
$ python -m pytest -q                       414 passed
$ python -m pytest -q tests/accounting      17 passed
$ ruff check fno tests tools                All checks passed!
$ python tools/check_imports.py             clean: 98 files
$ grep '"buy"|"sell"' fno/accounting fno/costs.py fno/books/fills.py     (nothing)
```

My own reconciliation tests used three trades, one of them on 31 Mar 2027 at the financial-year boundary, plus
costs in two categories:

```
untouched tables                                   -> reconciles() True
2,000 of trade net moved from FY 2026-27 to 2027-28 -> False (caught by "each year = sum of its months")
tax field of FY 2026-27 set to 0                    -> True  (not checked; new finding 1)
cost with category "AI" (declared: "ai")            -> ValueError: undeclared operating-cost categories ['AI']
```

## Judge 6's findings: decisions

| # | Finding | Builder's fix | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | No test that a non-reconciling ledger fails; add year = sum of months | `reconciles(months, years)` compares the tables with the raw entries and with each other (`ledgers.py:155-182`). There are 3 new tests, including 5 tamper cases | Code read. The checks are now independent of the table they check: month totals against raw trades and costs, the year set against the month set, each year against its months, and the tax base against deductible costs recomputed from raw. My cross-year tamper is caught. Tests pass. | ACCEPTED |
| 2 | "buy"/"sell" typed in two modules | `SIDE_BUY`, `SIDE_SELL`, `SIDES` in `fno/constants.py`, used by `ledgers.py`, `costs.py`, `books/fills.py` | My grep found no literal left in those files | ACCEPTED (this also closes judge 1 finding 4) |
| 3 | Undeclared or mistyped category silently not deductible | `read_cost_categories` plus `Ledgers.__post_init__` refuses undeclared categories | "AI" vs "ai" refused (above); tests added | ACCEPTED |
| 4 | Wrong header with no rows accepted | `_rows` checks the header and the field count | `ledgers.py:80-87`; test added | ACCEPTED |
| 5 | Nothing shows the ledgers yet | Left to the reporting stories (P2, S2, S4), noted for their judges | Agreed: this is outside C1's code scope | ACCEPTED |
| — | STT 0.15% unverified; one charges table for all dates | Three secondary sources cited (ICICI Direct, Groww, Outlook Money); the one-table policy is stated as a known limit in the story and in `config.yaml` | The known limit is present. The rate now has **some evidence** (secondary sources), not strong evidence; the Finance Act text is still to be cited, as the builder says. I could not open those sources myself in this round. | ACCEPTED as stated (some evidence) |

## Criteria (re-judged)

| # | Criterion | Result |
|---|---|---|
| 1 | Known-answer year | MET (unchanged test passes) |
| 2 | Ledgers reconcile; a test fails if they do not | MET (independent checks; tamper tests; my cross-year tamper caught) |
| 3 | Losing year | MET |
| 4 | Charges from `fno.costs`; pads separate | MET (judge 6 hand recomputation still applies: the charges code path is unchanged apart from the side constants) |
| 5 | April-March year | MET |

## Claims vs reality

- **"398 passed"** at the fix commit: I now get 414 at a later `main`, all passing. Consistent.
- **"ledgers.py 186 lines"**: true; under the 350-line limit.
- **"the old check could only fail on a tampered table"**: true; that was my judge 6 observation.

## Engineering standards

186 lines. The single-purpose helpers `_rows` and `_close` remove duplication (DRY) and the side constants are now in
one place. No breach.

## New finding

1. **Minor.** `reconciles()` does not check the derived `tax` and `after_tax` fields. Setting a year's tax to 0 still
   reconciles. Criterion 2 names only the account result and the tax base, so this is not a criterion failure.
   Expected: add `tax == rate × max(0, tax_base)` and `after_tax == account_result − tax` to the checks, with a tamper
   test.
