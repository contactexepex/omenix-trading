# Judge 477: O9b step 1, the VIX pilot, text and code (story/o9b-vix @ 05543aae)

Judge F. Round 1 of 2. The umbrella text passed in judge 475 add. 1. Step 1's text, its gap list and the claims are in
`docs/stories/O9b-static-data-to-drive.md`. Lane 1 (Drive, a workflow).

## Verdict: PASS. It may merge in the builder's stated order. 1 minor.

The order: move, then `data-cache sync` and `pytest -m data` green, then merge once `main` is green, then the first
scheduled run, then the removal commit with `.gitignore` and the hook refusal.

Gates on 05543aae: **9839 passed, 1 failed**; ruff, ruff format (1862), `check_imports.py` and the record scan (8001)
are clean. The failure,
`test_v4rules_phase2.py::test_every_committed_g7_record_row_carries_this_trees_method_hash`, is not this branch's:
- it fails the same way at the branch's merge base (b0b5135d);
- it passes on today's `main` (e0a4ac46);
- merging `main` in before the merge clears it.

Checked in the code:
- `ReceiptedRowLog`: write-once parts named by run id. The rebuilt table is the first part whole plus each later
  part without its header, so it equals the moved file byte for byte. A run with no rows writes nothing.
- `ReceiptedSnapshots`: the newest is current.
- Both read only through `DriveCache.sync` and refuse an incomplete cache (`DriveDataUnavailable`).
- `move_into`: a second move is a no-op; Drive holding other bytes refuses, overwriting nothing; read-back is
  verified.
- A17's `RowLog` port is moved, not copied.
- `vix-history.yml` commits receipts and manifests only.
- `data-checks.yml`: read-only, an explicit `failure()` alert step (O10 sees it), on capture-watch.
- `-m data` overrides `addopts`' `not data`.

## Plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | later parts keep their header line | yes, 2 failed |
| 2 | an incomplete cache read anyway | yes, 2 failed |
| 3 | the move overwrites differing Drive bytes | yes, 1 failed |
| 4 | a run with no rows writes a part | yes, 1 failed |
| 5 | the oldest snapshot read as current | yes, 1 failed |

## Minor

**The window between the move and the merge [reasoning only].** Until the merge, `main`'s old `vix-history.yml` still
appends to the repository file. A run in that window (a month's rows land on the 1st) would leave Drive's first part
without those rows. The move command catches this (`DIFFERS`), so:
- re-run `vix-history move` right before the merge, and merge only on `already in Drive, equal`;
- don't let the window cross 1 Nov.

After the merge (quality rule 8): cite the first scheduled run and the first `data-checks` run.

**Note (no new number): head dafedbe3.** Beyond merges of `main` (other judges' changes), the only change since 05543aae is one
import line in `fno/storage/row_log.py` (`from .raw_store import RawFileStore`, the A17 owner's nit). Checked by diff. The
PASS stands at dafedbe3, and the G7 failure is gone now that `main` is merged in.

**Merge check (ef9e976b, no new number).**
- The table's receipt SHA-256 `8d77cb52…` (789,682 bytes) equals `sha256sum` of the committed `india_vix_daily.csv`.
- The first `data-checks` run, 39769005484 on the merge commit, concluded **success** (read through GitHub's API).
- Still owed: the first scheduled `vix-history` run on 23 Oct, then the removal commit.

## Addendum 1: the removal commit (story/o9b-vix-removal @ 9c2ac0b6)

**Verdict: PASS. It may merge.**

- **The first scheduled run on the Drive path:** `vix-history` run 39911658650 (schedule, 23 Oct 06:28 UTC),
  **success** (read through GitHub's API). Its commit holds only three check-snapshot receipts. No table part, since
  September was already archived.
- **The removal:**
  - the 4 data files leave HEAD; the README stays and says where the data is;
  - `.gitignore` covers both paths;
  - `MOVED_VIX_FILES` is a `ForbiddenFiles` entry wired in `build_record_scanner`, so `git add -f` is refused too.
    My plant (the entry left out of the scanner) fails the test.
  - The one-off `move` command and its repository paths are gone.
- **Checks:** no `fno/`, `tests/`, `tools/` or workflow reader of `research/data/vix` remains (grep). vix_history,
  record_scan and o9b: 150 passed. The full-tree record scan is clean (8,658 files).
- **Reasoning only, for a later step (the builder's own note):** writing a check snapshot only when it differs from
  the latest would bring back "no change, no commit".

## Addendum 2: the data-checks trigger (story/o9b-data-checks-trigger @ 5a423497)

**Verdict: PASS. It may merge now** (urgent: the false "lost run" rows keep growing).

**My miss, said plainly.** In the main verdict I checked `data-checks.yml`'s steps and its alert, but not the cost of
its push trigger. `receipts/data/**` matches every job's receipt push, several an hour. GitHub keeps one pending run
per concurrency group and cancels the others, and O10's watcher records each as lost: **24 rows** in
`research/ops/capture_errors.csv` on 23 Oct (counted on `main`).

The fix:
- the push paths are `tests/**`, `fno/storage/**` and the workflow itself;
- the 09:41 IST daily run checks the new receipts;
- `tests/o9b/test_data_checks_workflow.py` pins the trigger. My plant (`receipts/data/**` put back) fails it.
- tests/o9b and the schedule tests: 21 passed.

**For the orchestrator:** `data-checks` in O10's `REPLACEABLE` set is O10's call. It is reasonable while the job can
still cancel a pending run on a burst of test pushes, which is far rarer now. The 24 existing rows are false losses,
not failed data checks.

## Addendum 3: data-checks in O10's REPLACEABLE (story/o9b-data-checks-trigger @ ccfc340a)

**Verdict: PASS. Both parts (the trigger, addendum 2, and this) may merge together.**

- `fno/health/run_failures.py`: `REPLACEABLE = ("news-capture", "data-checks")`, with the O10 builder's condition
  beside it. It holds only while data-checks records nothing per push or per day.
- The reasoning is sound: GitHub cancels the older pending run, and the newest pending one runs and checks the same
  committed state, so a run cancelled before any step is replaced, not lost. A run cancelled after a step is still
  one row and one alert, and the new test covers both.
- Checks:
  - tests/health and tests/o9b: 163 passed;
  - my plant (the old one-entry tuple) fails 1 test;
  - the code delta from 5a423497 is this tuple and its comment only.
