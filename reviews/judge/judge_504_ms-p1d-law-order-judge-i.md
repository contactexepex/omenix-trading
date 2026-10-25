# Judge 504: MS-P1d law order (second judge)

**Scope:** story/ms-p1d-law-order at 2de9c037, diff merge-base..2de9c037. Judge I (session_01MvZneCLZqBuiGyNxawdVee),
the second judge (money piece). I did not read Judge B's verdict. Lane 1. Round 1 of 2.

**Verdict: PASS.** No finding.

## Claims checked
| Claim | Result | Evidence |
|---|---|---|
| The data checks run before the limits | MET | `safety/wiring.py:38-52`: protected, the 4 quote gates, impossible price, then max loss, the 3 caps, margin room, daily stop, brake. Only the order changed: the same 13 laws, and `SafetyLaws` still runs all of them and keeps every reason |
| The first reason is the root cause | MET | a missing or one-sided leg names its quote first, with `max_loss` still among the reasons; a valid quote with too large a loss names `max_loss` alone. My plant (the old order back) fails 3 tests |
| Nothing else depends on the order | MET | no production module reads `refusals()` yet. The order changes only the reasons' sequence in a record, never pass or refuse |
| Gates | MET | full `pytest -n auto` 11,663 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean |

## Plants
1 planted, 1 caught.

## Notes (no action required)
- When j or g report "the first reason", they now get the root cause. A count by reason should still count every reason, since a starved risk law is kept as a consequence.
