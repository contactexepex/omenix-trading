# Judge 518: MS-P1a4, per-expiry lots (second judge)

**Scope:** story/ms-p1a4-lots at 03a467b0, diff merge-base..03a467b0. Judge I (session_01MvZneCLZqBuiGyNxawdVee), the
second judge (money piece: lot size sets a trade's size); Judge B passed it (479.4), and I did not read that verdict.
Lane 1. Round 1 of 2.

**Verdict: PASS.** No finding.

## Checked
| Point | Result | Evidence |
|---|---|---|
| `RoadDay.lots` and `lot_for` | MET | `contracts/roads.py`: `lots` names every recorded expiry, each above zero, and the nearest one equals `lot`. `lot_for` gives that expiry's own lot; without `lots`, only a recorded expiry has `lot`. Plants caught: `lot_for` returning `lot`, the nearest-lot check dropped, an unrecorded expiry given `lot` |
| Proposals size on the plan's own expiry lot | MET | `drivers/proposals.py:44-46`: units and C2's lot both come from `lot_for(plan.expiry)`, and `Proposal.lot` is the builder's own lot. No other school module reads `road_day.lot`. Plant (back to `road_day.lot`) caught |
| b unchanged, and the live catalogue still closes on mixed lots | MET | b fills no `lots`, so every recorded expiry carries the one lot that b's `ArchivedLots` proves (it closes `lot_mismatch` when the expiries differ) |
| Gates | MET | full `pytest -n auto` 13,804 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean |

## Plants
4 planted, 4 caught.
