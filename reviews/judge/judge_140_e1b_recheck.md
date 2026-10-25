# Judge 140: E1b re-check on today's main: `story/e1-topup` 5e3e5bf840c83f83353a47907c67ffca39990114 (on top of judge C's PASS at ddcefcc, judge 110 addendum 2), judge A

**Number note.** `judge_110` is judge C's file, so I used 140, the next free number.

**Why there is a re-check.** E1b was merged onto today's `main` and 4 tests failed:
- `fno/constants.py` went over 350 lines after P1;
- P1's catalog test named `starting_cash`, which E1b renames to `capital`.

## The changes since ddcefcc (main merges aside)

| Commit | Change | Check |
|---|---|---|
| ee8ba24 | The budget constants move from `fno/constants.py` to a new `fno/budget/constants.py`. Seven budget modules and two tests import from it. P1's fixture reads `state.capital`. The story adds review 111's wording | The 20 removed lines and the added ones are identical, the same names and values: a pure move. No module imports a moved name from `fno/constants.py` any more (I searched `fno`, `tests` and `tools` for every moved name). It is CLAUDE.md's "module-specific constants at the top of their module" case. `fno/constants.py` is now 331 lines |
| 4fac898 | Re-pin to dashboard a696b4d. Three files change: `fno-paper-trades.yaml` (`opening_value` maps to `account_state:capital`), `blocks-home.yaml` and `blocks.json` (the books at Rs 20 lakh, judge 136) | All **33 pinned files**: the SHA-256 at dashboard a696b4d equals `pin.json`, and the trading copies are byte-identical (0 mismatches). The contract version stays 2.7.0 |
| 5e3e5bf | Merge of main f2ec754 | — |

**The story wording (review 111).** "Only capital is cut at the decision time: fills are not, so rebuilding a whole
account from the ledger as of a past time is not supported."
- This states a limit; it changes no behaviour.
- It is consistent with Book 1 replaying from stored inputs: no decision reads a past account state rebuilt from the
  ledger.

## Gates, run myself on a trial merge of 5e3e5bf with origin/main as of now (510d98f)

- `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q`: **5565 passed, 0 failed**. The builder's one failure, the A16b
  verifier test, is fixed on main by c791051 and is included here.
- `ruff check fno tests tools`: clean;
- `ruff format --check fno tests tools`: clean;
- `python tools/check_imports.py`: clean.

### Verdict: PASS for 5e3e5bf840c83f83353a47907c67ffca39990114

- The constants move is a pure move.
- The re-pin is consistent with dashboard a696b4d.
- The fixture follows E1b's rename.
- The full suite passes on today's merged tree.
- Judge C's code verdict (110 addendum 2) stands for the rest.

## Addendum 1 (15 Oct 2026): E1b merge check and rule 8

| Check | Result |
|---|---|
| Recomputed merge equals the merge commit | **MET.** `git merge-tree --write-tree 3baf0e8 5e3e5bf` gives fc9ceab…, which equals the E1b merge **d8efc3b**'s tree. 65ec7c7 is a later merge of main |
| Branch files identical | **MET.** `fno/`, `tests/`, `contracts/` and the E1b story are the same in 5e3e5bf and d8efc3b |
| Rule 8, the real top-up (data commit 400d692) | **MET.** 9 files, only the command's own writes: per book, one `capital_top_up` row (amount 1,500,000, capital after 2,000,000, filled at 19:29:16 IST), `positions.json` and the day's equity row. **My own read** of `PaperAccount.capital(at)` on `main`: all three books show 500,000 at **15 Oct 15:00** and 2,000,000 at **16 Oct 15:00**. Today's decision is untouched, and tomorrow's sees Rs 20 lakh, as the story says |
| CI on `main` | **NOT MET.** `checks` on 65ec7c7 (the E1b merge, before the data commit) succeeded. `checks` on **400d692** (the data commit) **failed**: `tests/books/test_paper_account.py::test_the_committed_starting_state_is_the_13_oct_rs_5_lakh_opening_and_no_positions_for_each_book` asserts that the repository's own journal holds 500,000 for each book. The real top-up made that false, as designed |

**The root cause.**
- The test pins the committed journal's state, and its docstring says the books stay at Rs 5 lakh "until the owner
  decides how they are reopened".
- E1b's top-up is that reopening, so the test describes a state that has now ended.
- The top-up was committed without running the suite on the data commit, and CI caught it.

**Expected fix.** Restate the test for the committed state after the top-up. For each book:
- `capital()` equals 2,000,000, which equals `paper_account_rs()`;
- the ledger has the opening row plus one `capital_top_up` row;
- there are no positions;
- `capital(15 Oct 15:00)` equals 500,000.

This is a test change on money records, so it is lane 1 (a quick judge check). Do not rewrite the data.

### Merge check: NOT MET until CI on `main` is green again with the restated test

The code merge and the real top-up are correct.

## Addendum 2 (15 Oct 2026): the CI fix, `story/e1b-journal-pin` dde94700b40a94402bd9bcbceecc46deb27e6f6f

**The change.** One test in one file, `tests/books/test_paper_account.py`, is restated for the true committed record.
For each book:
- **Ledger:** exactly two rows, the opening of `500000.0` and a `capital_top_up` of `1500000.0` dated 2026-10-15;
- **Capital:** `capital()` equals 2,000,000, which equals `paper_account_rs()`;
- **No fills;**
- **`positions.json`:** cash and closed equity at 2,000,000;
- **Equity history:** exactly the rows for 13 Oct (500000.00) and 15 Oct (2000000.00), both with 0 open trades.

**Stricter than before.** The test now names each row's kind, amount and date, and the history's dates. The old
version only counted rows. It matches the data commit 400d692 I read in addendum 1. No data is touched.

**Gates.**
- `tests/books`: 40 passed.
- On a trial merge with origin/main, the full suite gives **5667 passed**.
- `ruff check` and `ruff format --check` of the file: clean.

**Note (one line).** It does not also assert `capital(15 Oct 15:00) == 500,000`, the point-in-time cut. That cut is
covered by E1b's own unit tests on fixtures, and I checked it on the real journal in addendum 1.

### Verdict: PASS for dde94700b40a94402bd9bcbceecc46deb27e6f6f

- E1b's merge check closes when the first `checks` run on `main` with this test is green.

## Addendum 3 (15 Oct 2026): E1b merge check closed

- **CI on `main` is green.** `checks` run 38755685061 on **2355b80** succeeded: a full run, 14:55-15:04 UTC.
- **That tree holds every part of E1b.** It contains the E1b merge d8efc3b, the real top-up data 400d692 and the
  restated test dde9470. The test file is identical to the one I passed in addendum 2.
- Merge and rule 8 were already MET (addendum 1).

**E1b is done.**
