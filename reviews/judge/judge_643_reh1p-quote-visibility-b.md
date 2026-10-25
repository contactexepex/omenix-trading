# Judge 643: REH1p, Groww's raw quote files in a rehearsal (story/reh1p-quote-visibility @ 678be37b4, PR #156), judge B, round 1 of 2

**PASS (1 minor). Lane 1** (what a rehearsal may read: look-ahead). Story and code in one round; I did not read judge F.
Code: `fno/rehearsal/quote_sidecars.py` (new), `visibility.py` (the sidecars after receipts and manifest rows),
`drive_wiring.py` (one argument), tests `tests/rehearsal/test_quote_sidecars.py`.

| Check | Result | My evidence |
|---|---|---|
| No look-ahead | MET | a raw quote file is visible at `max(finished_at, committer time of the first first-parent commit on main adding its sidecar)` (`quote_sidecars.py`), compared with the replay clock in `Visibility`. Plants "earlier of the two" (6 failed), "finish time only" (5) and "not first-parent" (1) are caught |
| Only real vouchers count | MET | the sidecar is read as its commit holds it (`git show <commit>:<path>`), never the working tree (plant caught); `raw_file_saved: false` never counts (plant caught); only Groww's quote datasets under the raw area (plant "any dataset" caught); no `main` in the record: nothing counts |
| No live record touched | MET | read-only: `git log` and `git show` on the record checkout; writes stay in REH1's `DryrunDrive` (unchanged) |
| Nothing absent counted | MET | a file with no committed sidecar on main stays invisible, so a capture the day never recorded is REH1b's "not recorded", never a success; the order in `Visibility` keeps receipts and manifest rows first |
| Gates | MET | trial merge into origin/main 4295944c8 (clean, 11515b147): ruff, format (2,636), imports (2,765), record scan (9,301), check_numbers clean; **16,602 passed, 1 skipped, 13 xfailed** (token kept) |

## Findings

1. **Minor m1:** the docstring's "the first commit on main that added the sidecar ... the oldest is kept" has no test.
   My plant keeping the newest adding commit (`setdefault` on the newest-first log) survives the 228 rehearsal tests.
   It errs late, never early, and only matters for a sidecar deleted and re-added on main, which a write-once sidecar
   never is. A test with a sidecar added, removed and re-added would pin it.

## Notes

1. Committer time stands for "the record held it", as in REH1g's manifest rows: a commit made at 15:01 and pushed at
   16:00 is visible from 15:01 in a rehearsal. This is the same accepted approximation, said once here.

## Plants

8 planted, 7 caught; the survivor is m1.
