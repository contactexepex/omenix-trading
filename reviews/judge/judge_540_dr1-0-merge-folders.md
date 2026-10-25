# Judge 540: DR1-0, merge Drive folders doubled by a race, and receipt an unreceipted file (story/dr1-0-merge-folders @ e0d18564)

Judge F. Round 1 of 2. Lane 1 (O9's Drive record store; a write repair). Labels: **strong**, **some**, **reasoning
only**.

## Verdict: FAIL (1 should fix). The design is right; one safety check is untested.

Gates on e0d18564: **14610 passed, 0 failed**, 1 skipped, 16 xfailed; ruff, ruff format (2342), `check_imports.py`
and the record scan (8824) are clean.

The orchestrator's three questions:
1. **The refusal paths: right and tested.** A tie in verified files, two same-named items, or a folder and a file
   with one name each refuse the whole plan, and `apply` does nothing on any refusal. A receipt that already exists
   is never replaced. Plants 1, 2, 5 and 6 below were caught.
2. **Can the kept copy be one with unreceipted or mismatched files over a verified one? No** [strong: code read].
   - The kept copy holds the most files whose bytes match their receipts.
   - A file in both copies is a clash, so it is refused, never chosen between.
   - A mismatched file in only one copy stays mismatched whichever copy is kept, and the read-back names it.
   - Unreceipted files are never counted.
   - Plant 3 (keep the fewest verified) was caught.
3. **The read-back after `--apply`: right in the code, untested.** That is SF1.

Also right: nothing is deleted (each emptied copy is renamed `<name>.merged-<day>`); both commands print until
`--apply`; a rerun after a partial failure is safe, because the kept copy's count only rises.

## Plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | a tie not refused | yes, 1 failed |
| 2 | a name clash moved anyway | yes, 1 failed |
| 3 | the copy with the fewest verified files kept | yes, 3 failed |
| 4 | **`apply` skips the read-back (returns no problems)** | **no: 15 passed** |
| 5 | `apply` runs despite refusals | yes, 1 failed |
| 6 | an existing receipt replaced | yes, 1 failed |

## Should fix

**SF1. The read-back after `--apply` is untested [strong: plant 4].**
- `FolderMerge.check` reads every receipt under the path through the path-based store, and the command exits 1 on any
  problem. It is the only proof that readers can use the path after the merge, and it is what the orchestrator
  asked about.
- With it removed, all 15 DR1 tests pass.

Fix: a test where, after `apply`, a receipted file is missing or holds other bytes (planted in the fake Drive), so
`apply` returns that problem and `merge-folders --apply` exits 1. Plus the clean case: no problems, exit 0.

## Note for the `--apply` run (reasoning only)

Run it when no job writes under `data/daily_runs/full`, outside the daily run (14:05-16:20 IST): a write landing
mid-merge could create a third copy. The repaired receipt's push time will be today, so O8 judges that day's run-log
receipt by today's push. That is late, and honestly so; Drive's creation time is in the receipt for the record.

## Addendum 1: round 2 at accf28e7

**Verdict: PASS. DR1-0 may merge.** `--apply` runs only after the orchestrator's go: outside 14:05-16:20 IST, with
nothing writing under `data/daily_runs/full` (the builder proposes a weekend).

SF1 is fixed, tests only (the code is unchanged from e0d18564):
- after `apply`, a receipted file that is missing or holds other bytes is named and the command exits 1 (both cases);
- a clean merge returns no problems.

My plant from round 1 (`apply` returns `[]`) now fails 2 tests. tests/dr1: 18 passed; ruff clean. Round 1's full suite
(14,610 passed) stands for the unchanged code.
