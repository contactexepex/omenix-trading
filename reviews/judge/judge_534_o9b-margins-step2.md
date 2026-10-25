# Judge 534: O9b step 2, the G4 margins to Drive, text and code (story/o9b-margins @ 162df9c8)

Judge F. Round 1 of 2. Lane 1 (money and risk inputs: C2's and C4's margin reads; Drive; two workflows). Labels:
**strong**, **some**, **reasoning only**.

## Verdict: PASS. It may merge in the stated plan. 1 note.

The plan: Tue 27 Oct 11:00-13:30 IST, after step 1b merges and `main` is merged in, with `margins move` before and
after, and the orchestrator's go.

Gates on 162df9c8: **14584 passed, 0 failed**, 1 skipped, 16 xfailed; ruff, ruff format (2337), `check_imports.py`
and the record scan (8783) are clean.

Checked in the code:
- New port `TableSource` (`FileTable`, `ReceiptedTable`). `ReceiptedTable` turns any `RuntimeError` or `OSError`
  (Drive's network included, the step 1b lesson) into `TableUnavailable`, naming the class only.
- **C2** (`fno/risk/margins.py`) raises `RiskInputError` and **C4** (`validity_margin.py`) raises `MarginProblem`, so
  an unreadable table refuses the trade: fail closed, no fallback (owner, 23 Oct).
- Both read one config key, `risk.margins.table`.
- A14c's evidence CSV goes through `ReceiptedSnapshots` before its factor row, so the row's `evidence_sha256` is the
  receipt's.
- The workflows commit receipts only.
- The two blocking points from the owner's A14/C2/C4 review are built in:
  - the catch-up move (step 1b's shared files);
  - a part without its last newline is refused at write and at read (`TableFileBroken`).
- Evidence files move with `exact=True`, never caught up.

## Plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | `ReceiptedTable` catches `RuntimeError` only (a network error escapes) | yes, 1 failed |
| 2 | C4 fails open: an unreadable table gives no rows | yes, 1 failed |
| 3 | C2 fails open: an unreadable table gives no rows | yes, 3 failed |
| 4 | the read-side last-newline guard off | yes, 2 failed |

## Note (for the owner, not a finding)

From the merge on, a Drive outage at decision time refuses every trade that needs a margin (C2 and C4 fail closed).
This is the owner's 23 Oct choice ("no fallback") and the safe direction. It means Drive's availability is now a
trading-day dependency, so a Drive sign-in that expires (O9's known risk) stops the desk until it is renewed. The
data-checks job and C4's own refusal lines make it visible the same day [reasoning only].

After the merge (quality rule 8):
- the first `nse-margins` and `stress-factor` scheduled runs on the Drive path;
- the first desk day's C2 and C4 margin reads.

## Addendum 1: the rebuilt step 2, story/o9b-margins @ 9b3a7922 (DRY1 g2)

**Verdict: PASS stands. It may merge in the stated plan**, after step 1b (judge 478 addendum 2).

9b3a7922 merges the PASSed step 2 head (e58dd0aa) with step 1b (61a0eee5). I read the merge's own changes with
`git show --remerge-diff`, which shows only how each conflict was settled. Five files had conflicts:

| File | How it was settled | My check |
|---|---|---|
| `receipted_rows.py` | keeps step 2's `NO_LAST_NEWLINE`; step 1b's empty-series guard comes in untouched | **union**. Present at the head: the empty-series guard (judge 536), `PartOutOfOrder`, `TableFileBroken` at write and at read, and `catch_up` |
| `moving.py` | keeps step 2's `exact=` line (`None if exact and current else catch_up`) | **right**. Evidence files are still never caught up |
| `data-checks.yml` | `MOVED: data/vix data/global-cues data/margins` | **all three groups** |
| `tests/o9b/test_moving.py` | step 1b's write-a-mid-line-part test is replaced by step 2's read-side test | **right**. Step 2 now refuses that write, so the old test could not set itself up |
| `tests/o9b/test_receipted_rows.py` | both tests kept | **union** |

The doc conflicts (story text, `WORK_REGISTER`) also settle as unions of both sides.

Gates on 9b3a7922:
- full suite: **14800 passed**, 1 skipped, 16 xfailed (the same environment skip as round 1; the builder's 14,801 ran it);
- ruff and ruff format (2380 files) are clean;
- `check_imports.py` (2509) and the record scan (8906) are clean.

| # | Plant (each reverted) | Caught |
|---|---|---|
| 1 | `exact=` ignored (evidence caught up) | yes, 2 failed |
| 2 | the write-side last-newline guard off | yes, 1 failed |
| 3 | the empty-series guard off | yes, 18 failed |
| 4 | `data/margins` dropped from `MOVED` | no test; **loud in the job** (below) |

Plant 4 is not a finding:
- the margins `data` tests read through `CacheOnlyDrive`;
- a file the sync step skipped fails them with "not in the verified cache: run `data-cache sync data/margins`";
- the job's alert step then posts to #fno-desk.

So a missing group shows the same day once margin receipts exist [strong, `tests/data_cache.py`]. The silent case
is a newly moved group with no `data` test at all. Optional, any later step: a test that every `cached_series`
folder's group is listed in `MOVED`.

After the merge: unchanged from round 1. The first `nse-margins` and `stress-factor` runs on the Drive path, and
the first desk day's C2 and C4 reads.
