# Judge 498: MS-P1d follow-up part 3, the read-only `SchoolAccounts.entries` (second judge)

**Scope:** story/ms-p1d-entries at fdd64766, diff 80625b19..fdd64766. Judge I (session_01MvZneCLZqBuiGyNxawdVee), the second
judge (money piece). I did not read Judge B's verdict. Lane 1. Round 1 of 2.

**Verdict: PASS.** No finding.

## Claims checked
| Claim | Result | Evidence |
|---|---|---|
| Every recorded entry, in the order recorded | MET | `school_accounts.py:94-104`; plant (order reversed) caught |
| Read-only: no account opened, no equity row, no push | MET | `test_entries_write_nothing...` compares the files byte for byte; plant (entries opening the account) caught |
| One pull per run, under the lock | MET | the pull is shared with the writer through `_locked`; plants (no pull, pulled every call) caught; a held lock refuses (`AccountBusy`) |
| A failed pull stops by name; half a record raises | MET | `PrivateFilesUnavailable` propagates; plant (the unit-for-unit check dropped) caught |
| Gates | MET | full `pytest -n auto` 11,660 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean; the file is 146 lines |

## Plants
5 planted, 5 caught.

## Notes (no action required)
- No `LedgerReader` port exists in the code yet (the Claims name a3's). j must run its conformance check on `SchoolAccounts` when the port lands.
