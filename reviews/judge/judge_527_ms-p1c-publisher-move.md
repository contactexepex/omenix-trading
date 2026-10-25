# Judge 527: MS-P1c receipt publisher move to storage

Judge B, 23 Oct 2026. Story/ms-p1c-publisher-move at 0a60ddd0, one commit; lane 1, routed by the orchestrator.
The dashcam's owner agreed to the move.

**Verdict: PASS for the move. It merges only once its merge tip is checked** (its importers on main and the
collision with ins-wiring, below).

## Claims vs reality

| Claim | Reality |
|---|---|
| Pure move, names and behaviour unchanged | True. Git sees a rename at 96% similarity, and the only lines that differ in the file are its 3 imports turned relative. Every class, constant and message is identical. The importers changed only their import line (seals, store, dashcam wiring, harness, test_store) |
| Golden test pins the seal SHA and the receipt text from before the move | True. I ran `test_the_move_to_storage_changed_no_byte_of_the_seal_or_its_receipt` on the merge base (pre-move code, import adjusted): it passed with the same values (seal 5a6b1a85..., receipt tail `\t532\t2026-11-02T09:40:00+00:00\ttest\trun1`) |
| Plants fail | My own plants on the moved file, run on `tests/school`: `--diff-filter=A` changed to `M`: 29 failed; `_deepen` skipped: 2 failed; the commit time replaced by now: 29 failed |
| Committer folder unchanged | True. `build_dashcam` still builds `REPOSITORY / RECEIPTS_FOLDER / DATA_AREA / SCHOOL_AREA` (`receipts/data/school`); only its import line changed |

Gates on 0a60ddd0 (run by me): 13,984 passed, 16 xfailed; ruff, format and check_imports clean.

## Merge conditions (not defects in the move; each must hold on the merge tip, which I will check)

1. **Importers on current main.** Main now has `fno/school/instructor/outputs/store.py:13`,
   `fno/school/instructor/wiring.py:28` and `tests/school/instructor/outputs/test_store.py:10`, all importing
   `fno.school.dashcam.publisher`. A trial merge is textually clean but fails on import
   (`ModuleNotFoundError`). With those three lines changed to `fno.storage.receipt_publisher`, my trial merge passed
   14,270 tests and check_imports. Test it must pass: the full suite on the merge tip, and
   `git grep "dashcam.publisher\|dashcam import publisher"` finds nothing.
2. **Collision with story/ms-p1j-ins-wiring (judge 507.13).** That branch adds `RemoteReceipts` to the old file and two
   more importers (`fno/school/fleet/run_receipts.py`, `fno/school/instructor_step_wiring.py`), and a merge-tree of
   the two branches reports conflicts. If ins-wiring merges first, this move must take `RemoteReceipts` with it
   unchanged, and the golden test must still pass.

## Notes

- `fno/storage` now imports `fno.research_engine.ledger.Git`, which no storage module did before. check_imports allows
  it, and the import is a small stdlib-only helper.
- The story file has no Claims entry and the work register has no row for this move (CLAUDE.md asks for a row in the
  first commit).

## Addendum 1

**Verdict: PASS** on the merge tip f4d54311 (0a60ddd0..f4d54311: current main merged in, and the three importers main
gained). This meets merge condition 1.

- **Still a pure move:** `git diff origin/main...f4d54311` covers 10 files. The only changes are import lines, the
  file's rename (its 3 imports turned relative) and the golden test. `git grep "dashcam.publisher\|dashcam import
  publisher"` finds nothing, and there is no re-export.
- **Gates on f4d54311 (run by me):** 14,275 passed, 16 xfailed; ruff, format and check_imports clean. It merges
  cleanly with current main.
- **Plant:** `--diff-filter=M` in the moved file fails 20 tests and errors 5 in `tests/school/dashcam` and
  `tests/school/instructor`.
- **Condition 2 still holds:** a merge-tree with story/ms-p1j-ins-wiring (bda6a49d, FAIL in 507.13) still reports
  conflicts. Whichever merges second carries `RemoteReceipts` and the two new importers (`run_receipts.py`,
  `instructor_step_wiring.py`) to `fno.storage.receipt_publisher` unchanged. I will check that merge tip.
