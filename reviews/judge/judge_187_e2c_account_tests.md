# Judge 187: "not weakened" check of `fix/e2c-account-tests` 75103ee4 (tests only)

Judge B. The E2c builder, asked by the orchestrator. The commit fixes the 2 tests that E2c's merge step `d9f67c4`
(`git rm --cached` of the account folders) broke on `main` (judge 177 addendum 4). It is one commit on `f78c775` and
changes 2 test files; no code changes.

## 1. `tests/books/test_paper_account.py`
- **Before:** the test read each book's committed ledger (opening Rs 5 lakh, top-up Rs 15 lakh on 15 Oct),
  `positions.json` and equity history from `journal/<book>/account/`. That folder is no longer committed, by the
  owner's E2c decision.
- **Now:** it asserts each book's committed `daily_totals.csv` exactly: the header, `2026-10-13,500000.00,0,0,0` and
  `2026-10-15,2000000.00,0,0,0`. It also asserts that closed equity equals `paper_account_rs()`. I checked: the file on
  `main` holds exactly these lines.
- **Ruling: not weakened beyond what the move requires.** The facts the old test proved still hold in the public
  record: the Rs 5 lakh opening on 13 Oct, Rs 20 lakh after 15 Oct, no trade and no fill. The row kinds,
  `positions.json` and the marked-equity column now exist only in Drive, which tests never touch.
- **Optional, not required:** to keep the old row-level check, a history test could rebuild `daily_totals` from
  `git show d9f67c4^:journal/<book>/account/cash_ledger.csv` and compare. It would check a fixed past commit, which
  adds little. I do not ask for it under the simplicity rule.

## 2. `tests/market_read_models/test_home_blocks.py`
- **Now:** three accounts are started in a seed folder, moved to a `LocalIndexStore` Drive with `move_accounts`, and
  downloaded into a separate checkout with `download`. The real `build_session_rows_builder(...).home.on(DAY)` then
  runs, with `market_wiring.ROOT` pointed at that checkout.
- **Every old assertion is kept:** limit 150,000, the book names, `approved == []`, and "started", now on the
  checkout. One is added: each book's value equals `paper_account_rs()`.
- **Not vacuous (checked).** Patching `ROOT` changes only `BooksReader(ROOT, ...)` in that builder. The approvals'
  `LATEST_FROZEN_EXPERIMENT` and the other module paths are bound at import to the real repository, so
  `approved == []` still reads the real frozen experiment. If the download is skipped, the checkout is empty and
  "started" fails, so the test depends on the download path.
- **Ruling: not weakened; stronger.** It now runs the E2c path (move, download, read) through the live wiring.

## Gates
Both files: 22 passed. The builder reports 6,120 passed and 1 failed in a fresh full-history clone with no account
files on disk. The remaining failure is G7's V6a count test (judge 177 addendum 4c), the orchestrator's to fix.

**Verdict: PASS for 75103ee4 (not weakened).** Merge it.

## Addendum 1 (15 Oct 2026): lane 1, and the G7 count fix `fix/g7-v6-counts-fixed-date` 4b9309dd

Judge A is right: editing an existing test is lane 1 (refinement 1). This verdict is therefore the lane-1 PASS for
75103ee4, above. The orchestrator asked for one verdict covering both red-main fixes.

**G7, 4b9309dd** (one test file, 7 lines added, 2 removed):
- **The change:** `committed()` now keeps the committed panel's closes only up to
  `DISCLOSED_THROUGH = 2026-10-14`. Both callers use it: the disclosed-counts test and judge 127's hand-value test.
  The exact numbers are unchanged.
- **The right date:** response 127's counts and G7's back-fill (`f891d9b`, "2017-01-03 to 2026-10-14") were taken on
  the panel up to 14 Oct. The panel now ends on 15 Oct (checked), which is why V6a's count became 2,410.
- **Not weakened:** both tests keep their exact expected values. My plant, moving the date to 13 Oct, fails both.
  The tests still pin the disclosed numbers to a fixed data window, which is what they always meant. The file passes
  with 9 tests.

**Verdict: PASS for both 75103ee4 and 4b9309dd (not weakened).** Push them. Then run the full suite on `main` once,
which should be all green.
