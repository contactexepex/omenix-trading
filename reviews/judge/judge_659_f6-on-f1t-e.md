# Judge 659: F6, Book 3's engine on F1t's port (story/f6-on-f1t @ e805c6466, stacked on story/f1t-code @ 7850269ed), judge E

**PASS (judge 2 of 2; no blocking or should-fix finding). Lane 1** (it decides paper trades). Judge E, own session;
judge B's verdict not read, no coordination. It merges only after F1t round 2.

## Criteria (the orchestrator's six, and the story's Claims 1-12)

| # | Criterion | Result | My evidence |
|---|---|---|---|
| 1 no write to the constitution, a D6 file, a frozen file or earlier ledger rows | MET | `BOOK3_WRITE_PATHS` = `journal/book3_ai/`, `book3/strategies/`, `research/ledger.csv`. F1t's `OutsideSnapshot` puts back anything written elsewhere; `run_check` refuses a file outside the paths. `tests/book3/test_write_paths.py` checks every version's paths against the constitution, every D6-hashed tracked file and every v4 byte-checked or recorded file. P1 (widened to `book3/`): caught. P2 (ledger prefix check off): caught. `register` refuses an existing id or spec file; names match `[a-z0-9]+(-[a-z0-9]+)*`, so no path escapes. P17b (earlier registry rows edited): caught |
| 2 every trade "strategy not yet passed" | MET | `served.strategy_status` is always `research`; F1t's label says "passed" only when every traded status is `paper`. P3 (status `paper`): caught. P12 (key dropped): caught. P13 (proposal status guard off): caught |
| 3 only passed cards cited | MET | `_cards` counts a card only with `card` not null; an unknown id refuses the day before any write. P4 (null cards counted): caught |
| 4 NoJudge never blocks Book 3, recorded | MET | `NoJudge`: `blocks` only for Book 2; its verdict file is written once and every record's `judge` names it (run check). P5 (NoJudge always blocks): caught. P6 (`judge` null): caught |
| 5 Book3Sheet at the pack's cutoff, no look-ahead | MET | The sheet reads `at_cutoff` on the common pack's own snapshot; strategies `on(day)` skip any proposed on or after the day; the decider rebuilds the sheet and refuses any difference. P7 (`SHEETS` empty): caught. P8, P15 (same-day strategies allowed): caught. P9 (sheet comparison off): caught. P10 (sheet built eagerly, outside the per-book guard): caught. P11 (widths dropped): caught |
| 6 live switch null | MET | `daily.live_from.book3_ai: null` on the branch and on the trial merge; `live_ai_books` packs and fires only books with a date |
| judge 400 SF1 | MET | P16 (`PlaybookError` no longer caught per strategy): caught |
| Gates | MET | Trial merge 1a0de560c (e805c6466 + origin/main ea79fe255): ruff clean, format clean (2,749 files), check_imports clean (2,904 files), record scan clean (9,491 files). Full suite with the token kept: **17,509 passed, 13 xfailed, 0 failed** |

## Plants

19 planted, each alone on `tests/book3`, `tests/ai_trading`, `tests/desk` and `tests/playbook` (828 tests),
restored after with `git checkout --` and `__pycache__` cleared. 17 caught; 2 equivalent, by evidence:
- **P17**, the registry's earlier rows reordered: `edited_rows` compares row content, so a reorder is no edit. My
  P17b (content edited) was caught.
- **P14**, the sheet built on tomorrow's strategy list: it survived the suite, so I probed it with the repo's own
  builders, a strategy committed with `proposed_on` today:
  - unplanted, `on(today)` lists none;
  - planted, `on(tomorrow)` lists `b3-sc-v1`, yet the sheet still holds 0 opportunities;
  - the reason is D2's `OpenedPlaybook`, which keeps only strategies opened before the day (`opened_playbook.py:27`);
  - the decider's sheet comparison (P9 caught) is a third guard.
  - No outcome can change, so this is not a gap.

## Findings

None blocking, none should-fix, no minor. Every claim I checked holds as written.

## Answers to the orchestrator's questions

- **Can Book 3 write its constitution, a D6 file, a frozen file or earlier ledger rows?** No (criterion 1).
- **Is every trade labelled?** Yes: "strategy not yet passed". The decider sets `research` for every record, so no Book 3
  trade can read "passed".
- **Can it cite an unpassed card?** No.
- **Does NoJudge block it?** No, and the verdict file is in every record.
- **Look-ahead in the sheet?** None found: its market data is the cutoff snapshot, and same-day strategies are kept
  out by three separate guards.
- **Live?** No: the switch is null.
