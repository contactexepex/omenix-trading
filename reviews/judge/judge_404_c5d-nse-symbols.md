# Judge 404: C5d, NSE contract IDs in C5's bucket map (story/c5d-nse-symbols at 09b3b412)

**Verdict: PASS. Lane 1 (it decides a trade: C2's and C4's bucket caps).** S1's text owner must agree the
PROTOCOL.md line, which the builder has asked for.

## The bug, checked
With `quotes.provider: auto` the captures fall back to NSE when Groww's settings are missing. NSE's IDs read
`OPTIDXNIFTY13-10-2026CE21950.00`. The old rule, "letters before the first digit", gives `OPTIDXNIFTY`, which is no
bucket, so C2 and C4 refuse every trade that day. This is a real path in normal running (Groww's settings expire or are
missing), and it fails closed, but it loses the day.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | One rule for both formats | MET | `fno/contract_symbols.py`: drop NSE's instrument code (`OPTIDX`, `OPTSTK`, `FUTIDX`, `FUTSTK`, the keys of `fo_bhavcopy.LEGACY_INSTRUMENTS`, not typed twice), then the letters before the first digit |
| 2 | One copy, C4 still independent of C2 | MET | both `fno/risk/buckets.py` and `fno/checks/validity_caps.py` import it; C4 imports nothing from `fno.risk` (judge 83) |
| 3 | Score-time freeze list | MET | PROTOCOL.md (a draft) adds `fno/contract_symbols.py`, required by `test_scoring_closure.py` because `buckets.py` imports it |
| 4 | Fails closed for unmapped names | MET | e.g. `NIFTYNXT50` still reads `NIFTYNXT`, which is unmapped, so it is refused, as before |
| 5 | Gates on a trial merge with main | MET | 8016 passed, 18 xfailed; 2 failed, the 2 that fail on main itself (not this change); ruff and check_imports clean |

## Planted mutations (all reverted)
| Mutation | Caught |
|---|---|
| The instrument-code strip removed (old behaviour) | yes, 6 failed |
| C4's copy of the rule made wrong | yes, 24 failed |

## Note (not should-fix)
Groww's symbols never start with an NSE instrument code, so the prefix strip cannot wrongly cut a Groww underlying
today. If a provider ever adds a symbol beginning with `OPT` or `FUT`, the real-fixture tests are where it would show.
