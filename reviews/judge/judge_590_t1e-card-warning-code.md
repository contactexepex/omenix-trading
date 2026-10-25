# Judge 590: T1e code, a failed or refused step turns the card's headline into a warning (story/t1e-card-warning at c80ad6cc0)

**PASS, lane 1.** Round 1 of 2. Judge I, own session (session_01CHtddAzFcEdQh4HFiz3mqU), 24 Oct 2026. Judged against
the passed text (judge 577.1) and the owner's 24 Oct rows 328-331. The code is at d7855f7ea. c80ad6cc0 changes only
`T-cards.md` (Claims), as stated. `git diff origin/main c80ad6cc0 -- fno/desk fno/daily` is empty.

## Criteria

| # | Verdict | My evidence |
|---|---|---|
| 1 | MET | `render.opening` (`render.py:45-49`): headline + T1's first line on line 1, detail on line 2, `Status:` on line 3; exact lines asserted (`test_card_warning.py`, `test_only_exits_failed_...`); L1, L2, L14 caught |
| 2 | MET | `GLYPH = "⚠️ WARNING:"`; the reason-code test checks every code in `SEVERITY`, `status.REASONS` and C4's check name; L12 caught |
| 3 | MET | `SEVERITY` order `data_check_failed` > `hard_rule_breach` > `step_problems`; L3 (order swapped) and L16 (code ignored) caught |
| 4 | MET | `summary(..., warned)` qualifies only a final "no breach"; L17 caught |
| 5 | MET | clean, empty and missing logs give T1/T2's card unchanged (`lines[0] == FIRST`, `Status:` on line 2) |
| 6 | MET | `UNREADABLE` warning for bad JSON and a malformed shape, with `data_check_failed` |
| 7 | MET | no bottom line in `RuledStatus`; the list appears once (count test); L14 caught |
| 8 | MET | `ProblemSteps.findings` calls `run_log.problem_steps` through `RunLogReader`; runner-versus-card test kept; L9 (refused dropped) caught |
| 9 | MET | the delivery file holds `reason_code: step_problems`, with no glyph, "WARNING" or list; L8 caught |
| 10 | MET | `test_card_contract.py` reads codes from `status.REASONS` and `SEVERITY`, and the enum from the pinned yaml; L13 caught |
| 11 | MET | placement only in `opening`; (b) is one line (docstring); L1 caught by tests 1 and 8 |
| 12 (new) | MET, accepted | `CardBuilder._warning` asks the warning apart from the status; a raising status keeps it; a raising warning source is named missing; L6, L18 caught |
| 13 (new) | MET, accepted | `issue._warning`: the Drive record gets `"warning": {headline, detail}` or null, never the repository; L7 caught |
| 14 (new) | MET, accepted | unreadable log gives `data_check_failed`, never `step_problems`, even with no rule reading it; L4 caught |

**My ruling on criteria 12-14: all accepted.** Each only adds or keeps a warning; none loosens a passed criterion. 12
closes a hole the passed text left as Out (a status crash hid the list; owner "instead of hiding", row 322); 13 keeps
the list in the Drive record only (criterion 9 and test 9 check the repository); 14 gives the more accurate code.

**Owner decisions.**
- Placement (a), warning first on line 1 (row 328): built, line 1 still contains PAPER ONLY.
- Token kept in tests (rows 329-330): my full run kept `FNO_SLACK_BOT_TOKEN` set. I read #fno-desk, #fno-forecast and
  #fno-intraday for the run's window (14:04:31-14:16:18 UTC). #fno-desk shows only the orchestrator's "DRY RUN …
  replay" posts, in T1d's card format, and the other two channels are empty. So no test posted.

**Re-pin (row 331).**
- The diff is only the enum (+3 codes), its description, the 2.14 version note, `schema_version` strings in the
  examples, `pin.json` (commit, version, 3 SHA-256s) and the pin test's "2.13.0"→"2.14.0".
- My `python -m fno market contract-check` prints "pinned W11 contract 2.14.0 (commit a7cadfc3bc0a): same as the
  dashboard's" (dashboard `main`). The SHA-256 test passes.

## Plants

15 planted (L1-L18), run one at a time on `tests/cards`, `tests/daily`, `tests/market_read_models`, each restored with
`git checkout --` and `__pycache__` cleared; tree clean after. **15 caught, 0 survived.**

## Gates (c80ad6cc0 merged with origin/main fb10b9da9 as dafc0e859, clean; token kept)

- `ruff check` clean; `ruff format --check` 2515 files formatted; `check_imports` clean (2644); `check_records`
  clean (9093).
- `python -m pytest -q -p no:cacheprovider -n auto`: **15645 passed, 1 skipped, 15 xfailed, 0 failed** (706 s).
- Sizes: largest changed file 112 lines (`card.py`); no class near 350.

## Notes (not findings)

- `card_record/v1` gains an additive `warning` key; nothing here reads it. The pin's commit hash is not confirmed
  independently (dashboard outside this session); `contract-check` confirms the files match its `main`.
- This weekend's rehearsal cards on #fno-desk show the problem T1e fixes: "Rule checks: no breach" above "Steps with
  problems today: margin_check (failed), quotes_done (failed)". The same posts show "step card failed:" with only a
  path and a hash as its reason. That is outside T1e; it is for the card step's owner.
