# Judge 652: F6 on F1t's port, Book 3's engine (story/f6-on-f1t @ 4061a51e0 on story/f1t-code @ b8f0585c1), judge B (1 of 2), round 1 of 2

**FAIL (1 should-fix, 1 minor). Lane 1** (decides paper trades). The re-judge of judge 400, on the round "Claims:
the round on F1t's port" (`docs/stories/F6-F7-book3.md`). I ran the gates on a trial merge of 4061a51e0 (which
contains b8f0585c1) into origin/main dd8992423 (clean, dd77cbc78). ruff, format (2,727), imports (2,856), record scan
(9,404) and check_numbers are clean; **17,280 passed, 1 skipped, 13 xfailed** (token kept).

| Orchestrator's check | Result | My evidence |
|---|---|---|
| (1) F1t's contract; a real trade passes F1t | MET | `Book3Decider` is an `AiBookDecider` on `AcceptedDecision`, `DecisionRefused`, `DecidedRun` (`ai_trading/ports.py`); `test_through_f1t.py` takes a real trade through F1t's real `Promoter` and `run_problems` |
| (2) Every chosen trade is labelled | MET | `served["strategy_status"] = PlaybookStatus.RESEARCH` (`decider.py:40, 115`); F1t's `strategy_label` gives "strategy not yet passed". Plants: label dropped, labelled as `paper`: both caught |
| (3) Write paths; constitution; ledger | PARTLY | `BOOK3_WRITE_PATHS` = `journal/book3_ai/`, `book3/strategies/`, `research/ledger.csv`; the constitution is `book3/constitution-v1.yaml`, outside them. F1t commits only the write paths, and `is_under` resolves `..` and links. The strategy id is D1's `NAME_PATTERN` (`schema.py:138`), so no path escape. The ledger is written only by `Ledger.register`, which appends `book3:<strategy_id>` (`registry.py:96`), and the real 108-row ledger round-trips byte-identical (my run), so frozen rows 101-108 cannot change. **But "never the constitution" has no test: SF1.** O12e is not on main, so its rule cannot be checked here beyond the `book3:<id>` form |
| (4) Prompt registered with its hash | MET (value), minor (test) | `sha256(agents/book3/decide_v1.md)` = 93d5fb96..., the registered value (my run); first added on this branch (e1c715e15); `prompt_text` refuses a mismatch at fire time. No test pins it: m1 |
| (5) Only a passed card is cited | MET | `decider.py:143` counts a card only when `card` is not null; plant "unpassed card citable" caught |
| (6) NoJudge never blocks, recorded | MET | `judge` = `AcceptedDecision.judge` in every record; F1t's run check matches it and refuses chosen trades only under `judge_blocks` |
| (7) Live switch null | MET | `daily.live_from.book3_ai: null`; plant setting it is caught |
| Book 1 unchanged | MET | Book 1's paths keep their defaults (`book=BOOK1_RULES`, no `served` context, no strategy fields, `strategy_id` "" and read only by Book 3's constitution check); the four committed Book 1 `inputs.json` (19-23 Oct) round-trip byte-identical through the new `DayInputs` (my run); plant "Book 1 inputs gain a key" caught |
| Judge 400's findings | MET | SF1: `strategies.py:39` catches `PlaybookError` per strategy (plant caught); SF2: `test_orders_exits.py:131` edits today's time exit and asserts the decided exit; M18: the served-merge order plant is caught |

## Findings

1. **Should-fix SF1: "never the constitution" is unpinned.** My plant widening `BOOK3_WRITE_PATHS` to `book3/` (which
   holds `constitution-v1.yaml`) passes all 1,025 tests in book3, ai_trading, playbook, books and checks. The write
   paths are F1t's only guard on what Book 3's run may commit, and the owner's constitution v1 (Q10) must never be
   one of them. Fix: a test that no write path of any registered version covers `book3/constitution-v1.yaml`, any
   file D6 hashes, or a byte-checked v4 file (`is_under` on each), and that the ledger is appended only (an existing
   row changed fails).
2. **Minor m1:** no test checks that the registered prompt hash matches the file. My plant with a wrong hash passes
   1,025 tests. `prompt_text` would refuse every fire once live (fail closed, every day `not_fired`). Add
   `REGISTRY.current(BOOK3_AI).prompt_text(ROOT)` to a test.

## Plants

13 planted, 11 caught. The survivors are SF1 and m1. A third, Book 1's proposal given a `strategy_id`, survives too
but is equivalent: only Book 3's constitution check reads it.

## Addendum 1: round 2 (the last), e805c6466 on F1t round 2 7850269ed

**PASS. Lane 1.** I ran the gates on a trial merge into origin/main ea79fe255 (clean, 0949dd4f7). ruff, format (2,749),
imports (2,904), record scan (9,491) and check_numbers are clean; **17,508 passed, 1 skipped, 13 xfailed** (token
kept). I judged F6's own changes; F1t's round 2 (`collect`, `promote`, `time_limit`) is F1t's judges'.

- **SF1: FIXED.** `tests/book3/test_write_paths.py` fails any registered version whose write paths cover the
  constitution, any tracked file whose SHA-256 a D6 row registers, or any v4 byte-checked or recorded file, and it
  asserts that the protected set is real. My round-1 survivor (paths widened to `book3/`) now fails. Beyond the ask:
  `Book3Decider` refuses the day when the ledger's bytes no longer start with its earlier bytes after registering
  (`decider.py`; plant "ledger rewrite allowed" caught).
- **m1: FIXED.** Each registered prompt is checked through `prompt_text` against its file; my wrong-hash plant now
  fails.
- **The builder's own fix, `Book3Sheet`: MET.** D2 over Book 3's tradable strategies with no picks, put in Book 3's
  private pack; `SHEETS` maps a book to a lazy builder, built only for the run's packed books. So Book 3's sheet is
  never built while `book3_ai` is not live, and a failure refuses that book alone. Plants: the sheet built for an
  unpacked book (1 failed); the sheet run with picks (41 failed).
