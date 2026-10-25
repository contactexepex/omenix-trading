# Judge 519: MS-P1j seams for the simulator (second judge)

**Scope:** story/ms-p1j-sim-seams at 6d3aa180, diff merge-base..6d3aa180. Judge I (session_01MvZneCLZqBuiGyNxawdVee),
the second judge (it touches the live fleet's road closure); Judge B may judge it in parallel, and I did not read that
verdict. Lane 1. Round 1 of 2.

**Verdict: PASS.** No finding.

## Checked
| Point | Result | Evidence |
|---|---|---|
| Live is unchanged | MET | `SchoolFleet.rules = LIVE` by default, and `fleet_on` passes none. `plan_slot` closes a road holding an unmeasured quote as `sizes_not_measured` unless the rules are practice ones. Plants caught: the practice exception ignored, the closure dropped, the rules not passed, practice made the fleet's default |
| Only the practice root can pass practice rules | MET | d's isolation scan over `fno/` (judge 511) refuses `QuoteRules(...)` and practice imports outside the two practice roots; the plant making practice the default fails it |
| A mixed build fails safe | MET (reasoning) | practice rules on the fleet with live laws or a live fill port only lets the road open; the live quote gate then refuses `size_not_measured`. It never fills |
| `books_on` and the replay dashcam's `encode`/`decode` | MET | one construction for the pilot's books; `fleet_on` calls it with `build_fill_port`. The write-once check compares the encoded payload, so a subclass's encoding stays write-once. Plants caught: `encode` and `decode` bypassed |
| Gates | MET | full `pytest -n auto` 13,800 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean |

## Plants
6 planted, 6 caught.

## Addendum 1: the follow-up 6d3aa180..54ef5d40

**Verdict: PASS.** Live is unchanged.

- **The switch moved: MET.** `school.enabled` is read in `wiring.build_fleet`, which returns `SwitchedOff` (the school-off line, nothing built). The CLI no longer turns the switch on in a copy of the config.
  - The paths that reach the fleet: `school run` through `build_fleet` (switched), and the replay through `replay_wiring` (local writes only, and it forced the switch on before). No daily-run step calls the school yet.
  - Plant (the switch check removed) caught.
- **`FillStep.rules` carries the fleet's rules: MET.** The shared-size allocation no longer hard-codes `LIVE`. The rules field has no default, so a step never assumes live ones. Plants caught: live hard-coded in the allocation, and in the runner's `FillStep`.
- **Gates (my run):** full `pytest -n auto` 13,803 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean.
- **For j's daily-run step:** it must enter through `build_fleet` (or read `school.enabled` itself). `fleet_on` has no switch now.

## Addendum 2: the first-ticket fix 54ef5d40..1f767528

**Verdict: PASS.**

- Every store the fleet records into (the driver account, then its ticket ledger) is opened by the session's view before any fill (`runner._open` over `Books.stores`). So a driver's first ticket is no longer refused by d's store (`AccountError`, a record before a view).
- `FakeAccounts` and `check_account_port` now enforce the same rule as d's real store.
- Plants caught: the ticket ledger left out of `stores`, the fake's rule dropped, the runner viewing the driver account only.
- **Gates (my run):** full `pytest -n auto` 13,807 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean.
- **Note:** the ticket ledger's view now writes its own equity row each session, in the private ticket account. Tickets are never summed into rupees (story f), so no report reads that row.
