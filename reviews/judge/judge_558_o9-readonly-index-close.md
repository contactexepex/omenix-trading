# Judge 558: readers of NSE's index-close files never write to Drive (story/o9-readonly-index-close @ a0f558d3)

Judge F. Round 1 of 2. Lane 1 (Drive writes, A4h's Confirmer, FL1's editions, G13's issuer). Claims: section
"Readers of NSE's index-close files never write to Drive" of `docs/stories/O9b-static-data-to-drive.md`. Labels:
**strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 should fix). A one-test fix; I re-judge it at once.

Gates on a0f558d3:
- full suite: **14835 passed**, 1 skipped (the environment skip), 16 xfailed;
- ruff and ruff format (2377 files) are clean;
- `check_imports.py` (2506) and the record scan (8897) are clean.

What is right, checked:
- The defect is real: `RawFileLibrary.get` archives what it fetches, and the 23 Oct dry run wrote manifest row
  aa0e2ed30.
- The fix is the right shape: a `FileLibrary` interface, with `StoredFilesLibrary` reading the stores only, and one
  reader builder in the composition root.
- Every remaining caller of `build_index_close_files` is a writer: the panel (`wiring.py:285`) and `nifty warmup`
  (`cli.py:125`). I checked with grep across `fno`, `tools` and `.github`.
- Each missing-file path already existed and is designed for this:
  - the Confirmer's "not yet" plus the overdue alert;
  - FL1's "not archived yet", confirmed by a later morning after the morning routine's archive step;
  - G13's gap line.

| # | Plant (each reverted) | Caught |
|---|---|---|
| 1 | the reader's builder uses the fetching library | yes, 2 failed |
| 2 | a missing file reads as empty bytes, not None | yes, 3 failed |
| 3 | `_reader_raw_stores` without the owner's raw area | **no**: 447 passed (SF1) |

## Should fix

**SF1. The reader's store list is untested, and on GitHub it is the only store [strong: plant 3; grep].**
- No workflow sets `FNO_GDRIVE_SERVICE_ACCOUNT_JSON` (0 of `.github/workflows`), so in GitHub's jobs and the routines
  `build_raw_stores()` is empty.
- Every test replaces `_reader_raw_stores`, so dropping the owner area passes.
- With it dropped, every reader on GitHub silently finds no file:
  - A4h is alerted only as "overdue", two sessions later;
  - FL1 says "not archived yet" every morning and never confirms;
  - G13's tables stop growing.
- Fix: one test that calls `_reader_raw_stores` with the four owner settings set and no service account. It asserts
  one store, an `AreaStore` over the owner's Drive at `RAW_AREA`, and that the builder with no settings gives `[]`.

## Notes (not findings)

1. **The evening edition loses a same-day official close [some].** `index-closes.yml` archives at 21:11 IST or
   later, after FL1's 20:05 evening edition. Before this change, the evening's `ArchivedCloses` could fetch the day's
   file from NSE when it was already out. Now it never finds it, and the next morning confirms. This is the designed
   path (`confirm.py`'s "confirmed in a later morning"), and a reader must not write, so I accept it. The claims
   should say it in one line for FL1's owner.
2. **Two reader builders.** `record_store/wiring.py`'s `stored_index_closes()` reads `build_raw_stores()` only, so
   the same GitHub gap applies to DR1's certifier if it ever runs there. The builder named the merge into one reader
   builder as DR1's to do; I agree. Track it in the work register, not here.
3. **Unverified bytes, as before.** The stores are read without a SHA-256 check against the manifest. That is
   unchanged from the writer's library, so it is not a regression of this change.

## Addendum 1: round 2 at fb1a4bd7

**Verdict: PASS. It may merge** (pull, full suite on the merged tree, `check_numbers.py`, then push).

Gates on fb1a4bd7:
- full suite: **14837 passed**, 1 skipped (the environment skip), 16 xfailed;
- ruff and ruff format (2377 files) are clean;
- `check_imports.py` (2506) and the record scan (8897) are clean.

| Point | Answer | My check | Result |
|---|---|---|---|
| SF1: the reader's store list untested | A test with the four owner settings and no service account asserts one `AreaStore` over the owner drive at `RAW_AREA`, and `[]` with no settings | Plants: owner area dropped, 1 failed; `REVISIONS_AREA` for `RAW_AREA`, 1 failed | **Accepted** |
| Note 1: the evening edition | one line in the claims | read | **Accepted** |
| New: `NoReadableStore` when there is no store at all (DR1's review) | "cannot read" is never "not yet" | Plant: guard off, 1 failed. Each reader's path catches it: A4h's Confirmer per day (`confirm.py:60-64`, the class name only, then the overdue mark); FL1's sections (`page/builder.py:102`) and `guarded` (`edition_run.py:154`, an alert). Such a run also lacks Drive, so it fails earlier anyway | **Accepted** |

Still open, DR1's to do: switch `record_store`'s `stored_index_closes()` to the one reader builder.
