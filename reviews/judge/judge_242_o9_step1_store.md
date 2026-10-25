# Judge 242: O9 step 1, the Drive data store (lane 1)

Verdict: **PASS** at `aa79450b` (`story/o9-step1-store`, base `e10b38ab`). This PASS has one condition, given under "Follow-ups" below.

## What was checked
- I read every new file in full: `fno/storage/receipts.py`, `data_store.py`, `drive_cache.py`, `part_table.py`, `snapshot.py`, `data_wiring.py`, `tests/o9_store/test_store.py` and `.gitignore`.
- The branch is one commit, with 9 files and 485 lines added. Every file is under 350 lines; the largest is the test at 175.
- I confirmed by reading `GoogleDriveUploadStore.put` that Drive is write-once: the same bytes are a no-op, different bytes raise `RawFileConflict`, and it re-checks with a fresh lookup.

## Claims vs reality
| Builder claim / story section 2 | Reality | Status |
|---|---|---|
| `DataStore.put` is write-once into area `data/` and returns the SHA-256 | Writes to Drive first, then the receipt. If the Drive write fails, no receipt is written; the ordering mutation is caught. | met |
| `ReceiptWriter` writes and commits `receipts/<path>.sha256` | `ReceiptFolder` is write-once: the same digest keeps the first receipt, a different digest is refused. It writes atomically. The A16f origin-main committer is wired in `data_wiring.py`. | met |
| `DriveCache.sync` lists Drive, downloads what is new, verifies against receipts and keeps a local index | The receipts are the index and Drive is **not** listed. A Drive file with no receipt is invisible, which is the safer design. MISSING and DAMAGED files are reported and never written. | met, by a different design that the story does not record |
| `PartTable`: write a part, read the union (CSV **and JSONL**), **latest-wins** for supersessions | It writes one part per run (named by run_id) and reads the union. A part with different columns is refused. **CSV only.** Latest-wins is left to each table ("stays each table's own rule"). | **partial** |
| `Snapshot`: versioned state files, newest wins | `write_snapshot` / `latest_snapshot` pick the newest by sorted name. | met |
| 14 tests; 2 planted mutations caught | 14 tests pass. I planted 7 mutations myself; 6 were caught (table below). | met |
| 6975 passed | 6986 passed on the trial merge with `origin/main` 7df28078. The 11 extra tests came from main. | met |

## Mutations (planted by me against `tests/o9_store`, each one restored afterwards)
| # | Mutation | Result |
|---|---|---|
| 1 | Receipt with a different digest accepted (`if False:`) | caught |
| 2 | Cache trusts any present file without checking its SHA | caught |
| 3 | Column-mismatch check in `read_parts` removed | caught |
| 4 | Oldest snapshot returned instead of the newest | caught |
| 5 | `drive.put` removed from `DataStore.put` | caught (9 failures) |
| 6 | Receipt written **before** the Drive write | caught (`test_a_failed_drive_write_leaves_no_receipt`) |
| 7 | Damaged download written to disk anyway | caught |
| 8 | Receipt temp name `.part` changed to `.tmp` | survived. The rename is cosmetic, but it shows that atomic replace is not tested. Follow-up. |

## Gates (trial merge with `origin/main` 7df28078)
- `pytest -n auto`: 6986 passed.
- `ruff check`: clean.
- `ruff format --check`: 1242 files already formatted.
- `tools/check_imports.py`: clean.

## Project rules
- The 350-line limit is met.
- Constants are named at the top of each module.
- Concrete classes are wired only in the new root `fno/storage/data_wiring.py`.
- No secrets. No order code. No real Drive calls in tests.
- **Misses (both follow-ups):**
  - The `docs/WORK_REGISTER.md` O9 row was not updated in the first commit. It still says "text v2 for the judge" and names the branch `story/o9-data-to-drive`.
  - `CLAUDE.md`'s list of composition roots does not name `fno/storage/data_wiring.py`.

## Must-fix
None for this step. What is built is correct and tested.

## Follow-ups
1. **Condition of this PASS.** Before any step moves a JSONL table, or a table whose later rows supersede earlier ones, do one of two things:
   - build JSONL reading and latest-wins into `PartTable`; or
   - amend story section 2 to say these stay per table, and name where each table's rule lives.
   Also record in section 2 that `DriveCache` uses receipts as its index instead of listing Drive.
   "Section 2's five parts" is not fully true until one of these is done.
2. `DriveCache.sync` only reports MISSING and DAMAGED files. Every caller (step 2 onward) must stop and alert on `not report.complete`. The judge will check each caller for this.
3. Restoring with `into=` writes into the checkout. Those paths must be git-ignored at the step that removes the data from git, or they will be re-committed.
4. Add a test that a crash between the temp write and the replace leaves no half-written receipt or cache file under the real name (mutation 8).
5. A writer name containing a tab breaks the receipt format. Refuse it in `DataStore` or `Receipt`.
6. Two runs in the same UTC second order their snapshots by random hex, so "newest wins" is not guaranteed there. This is unlikely, but it should be documented or tie-broken by `written_at`.
7. Update the register row and the composition-root list in `CLAUDE.md` (lane 3 / docs).

## Addendum 1 (16 Oct 2026): merge check, step 1 merged to main as 78d66a02

**Verdict: merge check PASS.**

- **The merge is exact.**
  - Its parents are 281583b9 (main) and aa79450b (the passed tip).
  - Recomputing it with `git merge-tree` gives a tree identical to 78d66a02 (empty diff).
  - `git diff aa79450b 78d66a02 -- fno/storage tests/o9_store .gitignore` is empty.
  - Against its main parent, it adds exactly the branch's 9 files (485 lines).
- **Later changes on main.** Only A14c (32db170b) has touched `fno/storage` since: `content_checks.py` and `raw_source.py`, which step 1 did not change.
- **CI.** Checks run 38872554601 on ffa0f74e, which contains the merge, ran the full suite and is green.

## Addendum 2 (16 Oct 2026): step 1 follow-ups at 6be069b3 (`story/o9-step1-followups`)

**Verdict: PASS at 6be069b3. The condition is met.**

The builder's own commit changes 4 files over the main merge 3114001f: `CLAUDE.md`, the story, `data_store.py` and `test_store.py`.

| Item from judge 242 | Reality | Status |
|---|---|---|
| Condition: section 2 must match the code | Section 2 now gives each part's real behaviour. PartTable writes CSV parts only, with supersession per table, and any step that moves a JSONL or superseding table must build or name its reader first. DriveCache uses receipts as its index, never lists Drive, and every caller stops and alerts when `not report.complete`. Paths written with `into=` are git-ignored only. Same-second snapshot ties are ordered by the random suffix, and callers must not rely on that order. | met |
| 3: `into=` paths git-ignored | Written as a rule in section 2; it will be checked at the step that removes the data from git | met (as a rule) |
| 4: atomic receipt write untested | New test: a crash in `Path.replace` leaves only the hidden `.part` file, and `read` and `under` see nothing. My mutation replacing the write with a direct `write_text` makes it fail. | met |
| 5: a tab in the writer breaks a receipt | `DataStore` refuses an empty writer or run_id, and any tab, LF or CR (4 tests). My mutation narrowing the check to tabs only makes the LF case fail. | met |
| 6: snapshot same-second ties | Documented in section 2 | met |
| 7: composition-root list, register row | `CLAUDE.md` now names `fno/storage/data_wiring.py`. The register row was updated on main separately (lane 3). | met |

**Rule text.** `CLAUDE.md`'s "GitHub files are the default store" becomes the owner's Drive-only rule (DESK_DECISIONS, 16 Oct), with "built step by step".
- This is accurate as a direction. But until each writer moves, most data still reaches GitHub.
- Read it as the target, not the current state.
- The 3 pm recorder section of `CLAUDE.md` is already consistent with it: sidecars only, with the raw files in Drive.

**Gates.** Trial merge with `origin/main` (8aacf8b1):
- `pytest -n auto`: 7075 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: clean.
- `CLAUDE.md` is 158 lines.

## Addendum 3 (16 Oct 2026): merge check, follow-ups merged as 067df59e

**Verdict: merge check PASS.**

- **The merge is exact.**
  - Its parents are 57408607 (main) and 6be069b3 (the passed tip).
  - Recomputing it with `git merge-tree` gives a tree identical to 067df59e.
  - Against its main parent it adds exactly the four reviewed files: `CLAUDE.md`, the story, `data_store.py` and `test_store.py`.
  - The only differences from the branch, in `content_checks.py` and `raw_source.py`, come from main (A14c, 32db170b).
- **CI.** Checks run 38874396783 on c70e5c92 contains the merge, ran the full suite and is green.
