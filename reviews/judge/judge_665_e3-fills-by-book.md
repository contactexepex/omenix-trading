# Judge 665: E3 fills by book, the run log's `fills` result keyed by book

Branch `story/e3-fills-by-book` at `ca0de476c` (PR #162; story `docs/stories/E3-fills-by-book.md`). **FAIL, lane 1**
(1 should-fix, 1 minor; one judge). Judge session 01BvZZzF4XR48qNHNxLydQhf.

## Criteria

| Item | Verdict | Evidence |
|---|---|---|
| One reader for both shapes | MET | `fno/desk/fill_results.py` `trade_entries`, `trade_fills`, `book_refusals`; old flat and new shape read alike, step fields skipped (`tests/desk/test_fill_results.py`) |
| Nothing recorded rewritten; 17-24 Oct read the same | MET | no `journal/` file in the diff. The 7 committed logs hold no fill entries (the reader over `journal/runs/2026-10-*.json`: 0 entries, 0 refusals) |
| Book 1's 16 Oct line, same values under the book key | MET | `test_replay_day.py` pins `{book1_rules: {"trades": {id: {outcome, reason "4 legs filled", snapshot_id, sha256}}}}` |
| No other reader of run-log `fills` missed | MET | grep of `fno` and `tools`: the only production reader is the step's own written count (`daily_steps.py:160`). `opening_runs`, `committed_runs`, `pending_commit` and the school read no fill result. The public log recurses: both books' lines kept, trade IDs `unlisted:n` as before (my script) |
| Two books on one trade ID keep both lines | NOT MET (proof) | finding 1 |
| The changed tests are not weakened | PARTLY | the same values are asserted, but through `trade_fills` with no book, so no test checks which book a line sits under (finding 1) |
| Gates | MET | trial merge with main: ruff, format, imports, check_records and check_numbers clean; 17441 passed, 13 xfailed, 0 failed |

## Findings

1. **Should fix: the story's core claim has no test at the step.** Claim 1's test builds the result dict by hand
   and tests only the reader. My plant puts the old collision back into `DeskSteps._fill_books`: after each fill,
   the same trade ID is dropped from every other book's `trades`. The **full suite still passes** (17355 passed, 0
   failed). Two other plants were caught only incidentally: every book under `book1_rules` crashes on Book 1's
   refusal dict, and one shared key is caught only by Book 1's pinned key. Fix: a step-level test (`DeskSteps.fill`,
   or the daily run) where Book 1 and Book 2 fill the same opportunity, asserting both lines under their own books
   with their own values (e.g. `sha256` or reason). Where a test has Book 2's trades (`b1`, `b5`), read them with
   `trade_fills(result, BOOK2_HYBRID)`, so the book is checked too.
2. Minor: `trade_fills(old_flat, book)` gives Book 1's old trades for any named book (the test calls this "every
   book's view"). It is harmless while only Book 1 ever traded on old logs. The docstring should say a named book
   on an old log means Book 1.

## Plants

3 planted in `daily_steps.py`: (a) every book filed under `book1_rules`: caught, incidentally (3 tests);
(b) one shared key: caught by the 16 Oct pin (1 test); (c) the old collision: **survived the full suite**.

## Notes

- Claim 5 (the dashboard) is outside this repository; the orchestrator says it reads read models, not run logs.

## Addendum 1: round 2, head `59961fd7e` (code 378007eec)

**PASS, lane 1.** The orchestrator named head `6bb07be6c`, which does not exist on the remote; the branch's head is
`59961fd7e` (Claims gate line on top of 378007eec). That head is the one judged.

| Round-1 finding | Verdict | Evidence |
|---|---|---|
| 1 No step-level test of two books on one trade ID | FIXED | `test_book1_and_book2_on_one_opportunity_both_keep_their_fill_line` runs E3's daily run with Book 1 and Book 2 both on `t1`: both accounts fill, and both lines sit under their own book keys. My three plants in `_fill_books` are all caught: the old collision (by the new test), every book under `book1_rules` (6 tests) and one shared key (6 tests). Book 2's `b1`/`b5` and Book 3's `c1` are read through their own book |
| 2 An old flat log read for any book | FIXED | `trade_fills`: an owner of None counts as Book 1; the test pins `trade_fills(old, BOOK2_HYBRID) == {}`. My plant (the old rule back) is caught |

**Gates (trial merge with main, clean):** ruff, format, imports, check_records and check_numbers clean; full suite
17516 passed, 13 xfailed, 0 failed. **Plants this round:** 4, all caught.
