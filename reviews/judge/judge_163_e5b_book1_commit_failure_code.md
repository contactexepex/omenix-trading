# Judge 163: E5b code (Book 1: one decision a day; a failed commit alerts once and is recovered)

**Verdict on 1a7d5f18 (`story/e5b-book1-commit-failure`, rebased on main 29d1fcef; claims `response_123`, "Code
round"): PASS.** No blocking or should-fix findings and two notes.

Story text: judge 123 and addendum 1. ChatGPT review 107 and response 134. Decision 67 (owner's simplicity rule) dropped
the pre-commit re-check. E5b decides Book 1's trades, so ChatGPT's review follows (rule 9).

## Gates (run by me)

- On a trial merge of 1a7d5f18 with `origin/main` (no conflict): 5,877 passed with `FNO_SLACK_BOT_TOKEN` unset.
- ruff check, ruff format --check and check_imports are clean.
- The E5b-related suites (`tests/book1`, `tests/decisions`, the first-timely-decision test): 173 passed on the SHA.

## Criteria, and my own plants

Each plant was run against `tests/book1` and the first-timely-decision test. Every one failed at least one test.

| Criterion | Result | Evidence |
|---|---|---|
| 0. One decision a day in all three states; changed inputs alerted; disk-only gives the hand fix; `--commit-run` | MET | `Book1.decide` recovers first, then `GitDecidedRuns.find` checks origin (after a fetch), `HEAD` and disk. Plants caught: J1 decide again when a run is found; J2 a quiet "already decided" for a disk-only run; J3 `--commit-run` without D3's `edited` check; J5 origin not fetched; J6 changed-input alert silenced |
| 1. Raw quote file staged, origin unreachable, push rejected: one alert, one line, exit 1, no traceback | MET | `cmd_book1` catches `CommitFailed` with real git and a bare origin (tests). Plant J7 (no catch) caught |
| 2. A rerun commits the recorded files byte-identical; an unpushed commit is pushed | MET | Recovery runs before any decision. Plant J4 (recovery skipped) caught |
| 3. An edited decision file stops the rerun, naming it | MET | `PendingChanged` path, test |
| 4. Separate markers | MET | `.pending_book1.json`, git-ignored; the daily run's recovery does not see it (test) |
| 5. Success prints the same line, exit 0 | MET | Test |

## Rulings on the builder's three points

1. **Two checkouts deciding at the same moment: accepted.**
   - Decision 67 dropped the pre-commit re-check under the owner's simplicity rule. Book 1 has no routine yet, so two
     sessions firing at the same instant is not a path in normal running.
   - The guarantee is in place on main. `fno/desk/committed_decisions.py` takes the **first** original run in D3b's
     run order. The new `DeskSteps._alert_double` sends one alert when a book has more than one original run in a day,
     and corrections are not counted (review 107; test).
   - The sequential two-checkout case is prevented and tested.
2. **"D2 run once" counted as decisions written: accepted.**
   - `DecisionRun.inputs` shares `_evaluate` with `decide`. It writes nothing, does not call `log_failures`, and
     commits nothing.
   - D2's `evaluate` (`fno/playbook/evaluate.py`) has no file writes. Recomputing D2's inputs is the only way to
     compare them, and the tests count decisions written.
3. **`test_one_run_order` listing `decided_runs.py`: accepted.** `GitDecidedRuns.find` builds sets of names
   (`set().union`, sorted for display) and never picks a first run. Ranking stays with D3b.

## E2c's planned resolution in `book1_cli.py` (download first, inside the try)

- **Sound for `decide`.** E2c's `download_private_records(day)` raises `PrivateFilesUnavailable`, a subclass of
  `CommitFailed`. Inside the try it gives one alert and exit 1, never a traceback. The download must come before
  `decide`, because `_already` recomputes D2's inputs from the private records.
- **Note 1 (wording, not a finding).** On a download failure nothing has been decided, but the shared text says
  "decision NOT committed … not public". A separate `except PrivateFilesUnavailable` with "nothing decided: Drive could
  not be read" would be clearer. It changes no trade.
- **Note 2.** `--commit-run` needs no private records (it never runs D2). If the download sits before both paths, the
  hand fix also fails while Drive is down. Put the download on the `decide` path only.

## Coordination

E5b touches `fno/books/` and `fno/desk/daily_steps.py` and `pending_commit.py`; E2c also touches `book1_cli.py`. The
work register orders "E5b after E2c". The resolution above is the only shared line. No duplicate.
