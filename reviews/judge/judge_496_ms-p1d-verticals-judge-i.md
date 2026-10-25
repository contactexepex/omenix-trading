# Judge 496: MS-P1d follow-up part 2, verticals on b's rule and settlement on b's stores (second judge)

**Scope:** story/ms-p1d-verticals at c3f75f28, diff 390d7131..c3f75f28. Judge I (session_01MvZneCLZqBuiGyNxawdVee), the
second judge (money piece). I did not read Judge B's verdict. Lane 1. Round 1 of 2.

**Verdict: PASS.** No finding.

## Claims checked
| Claim | Result | Evidence |
|---|---|---|
| The impossible-price law uses b's `impossible_keys`, on the proposal's legs only, with b's 1e-9 tolerance | MET | `quote_laws.py:71-73`; d's own `_verticals` is gone, so the rule exists once (my judge 486 note). Plants caught: the check removed, the whole chain judged instead of the legs, tolerance set to 0, the total-bounds check removed |
| Settlement on b's `build_archive_stores` | MET | `execution/wiring.py:18-20`. Real runs on the archived 29 Sep 2026 file: the service account settles all 4 indices; without it, the owner's Drive is used; with neither, `RawFilesNotConfigured` by name. Plant: empty stores, caught |
| Gates | MET | full `pytest -n auto` 11,632 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean |

## Plants
5 planted, 5 caught.

## Notes (no action required)
- The law is a little stricter than d's own rule was, and still correct: b's function judges every pair of one type and expiry among the legs, not only bought-against-sold pairs. It also checks the single-leg bounds (a call's bid above the index, a put's bid above its strike). All of these hold for any real quote, so a refusal still means bad data.
- A refused law's `value` is now the number of flagged legs, not a rupee value; `limit` is empty. A report reading the value must not show it as rupees.
