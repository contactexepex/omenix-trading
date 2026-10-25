# Judge 576: T1d code, the card names failed or refused steps (story/t1d-failed-steps at 5cbd3c4c7), round 1

**PASS, lane 1.** Judge I, routed by the orchestrator, 24 Oct 2026. Judged: `git diff 2c80be430 5cbd3c4c7`
(T1d's own changes; R2's round 2 at `2c80be430` is judged by judges B and E). It touches only `fno/cards/`
(4 files), `tests/cards/test_problem_steps.py` and `docs/stories/T-cards.md`; `git diff 2c80be430 5cbd3c4c7 -- fno/desk
fno/daily` is empty. Merges to main together with R2's -b head.

## Criteria

| # | Verdict | Evidence |
|---|---|---|
| 1 | MET | `problem_steps.py:23` calls O1's `run_log.problem_steps`; tests at lines 38, 52, 161; plants J1, J2, J8 caught |
| 2 | MET | no line on ok, not_live, empty log (tests 46, 52, 171); J14 (reason in line) caught |
| 3 | MET | `steps or {}`; `status_lines({})` gives no line (test 46) |
| 4 | MET | `runner.py:59` calls the same `problem_steps`; no `PROBLEMS` left in `fno/daily`; test 69 builds the real `DayRunner` line and the card line from one log |
| 5 | MET | reads only `RunLogReader.steps`; reader refuses odd shapes once (`rule_checks.py:71`, J6 caught); wiring pinned (J7 caught) |
| 6 | MET | `rule_checks.py:108,113`: failed/refused decisions give "decisions step failed: raised:...", `data_check_failed` (J5, J9, J11 caught); other statuses no code of their own |
| Judge 570.1 condition 2 | MET | failed decisions never list "status"/"reason": J3 and J4b (no status check, raw result as books) caught |
| Checklist (pending_judge_I) | MET | rule is O1's, not a copy; DecisionOutcome uses `problem_steps` itself, not the set; the three named plants caught (J1, J2, J3) |

Builder's points checked: odd shapes give "not readable (steps are not name -> {result: {...}})" and
`data_check_failed` (test 133, J6, J13 caught). Every committed run log on `main` (388 versions of 7 files in
history, my own script) has the accepted shape, so no real day turns unreadable. C4 refusals are read on every path
(J10 caught). `{"status": None}` is a step-level result (test 110). P5 (`book_results` dropped) is equivalent: it
empties only results whose status is failed or refused, which always carry `status` and are taken first by
`_decided`; my J4 (same mutation) survived for that reason, agreed.

## Plants

17 planted on the merged tree (tests/cards, tests/daily, tests/desk), each restored with `git checkout --` and
`__pycache__` cleared; tree clean after. 15 caught. Survivors: J4 (equivalent, above) and J15 (the problem line
emitted twice: no test says the line appears exactly once; criterion 1 says "one line"). J15 is minor: the code
appends it once (`ruled_status.py`), a regression would be visible on the card.

## Gates (5cbd3c4c7 merged with origin/main 385fe5b44, merge clean)

- `ruff check` clean; `ruff format --check` 2445 files formatted; `check_imports` clean (2574 files);
  `check_records` clean (9004 files).
- `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -p no:cacheprovider -n auto`: **15169 passed, 15 xfailed, 0
  failed** in 722 s, load average 10.9 at start, 5.2 at end. The builder's timing failure
  (`test_a_live_holder_keeps_its_lock_after_its_lease_expires`) did not recur in this full run; one run, no rerun
  needed. (A first attempt was stopped by my own tool's time limit before it printed a result; not counted.)
- Sizes: largest changed file 181 lines (`rule_checks.py`); no class near 350.

## Notes (not findings)

- Minor: a test asserting the problem line appears exactly once would catch J15.
- Minor: `RuledStatus(problems=None)` is optional only so T2's older tests construct it unchanged; production
  always passes it, and the wiring test pins that.
- Pre-existing (T2, not T1d): a per-book decisions entry that is not a dict (`None`) would raise `TypeError` past
  `_read`; none exists in history. A malformed previous-day log makes today's execution line unreadable (fails closed).
- Known limit, for the owner, not for me: when only a non-ruled step fails (for example `exits`) the card still says
  "Rule checks: no breach" with the problem line last. The passed text keeps the status unchanged; already put to
  the owner.

## Addendum 1 (re-check in its own session)

**PASS at 5cbd3c4c7, lane 1.** Judge I, in its own session (session_01CHtddAzFcEdQh4HFiz3mqU), 24 Oct 2026, as
DESK_DECISIONS 24 Oct ("every builder and judge runs in its own session") asks. Judged: `git diff 2c80be430 5cbd3c4c7`
only. It touches `fno/cards/` (4 files), `tests/cards/test_problem_steps.py` and `docs/stories/T-cards.md`, nothing
else; `git diff 2c80be430 5cbd3c4c7 -- fno/desk fno/daily` is empty. The owner's later "warning headline" ruling is
T1e's, not judged here.

| # | Verdict | My evidence |
|---|---|---|
| 1 | MET | `problem_steps.py:23` calls `run_log.problem_steps`; line appended once after the outcomes (`ruled_status.py:61`); my K1 (status dropped), K2 (order reversed), K3b (line moved above the summary) caught |
| 2 | MET | `ok`/`not_live`/empty log give no line (tests 46, 52); K16 (only `failed` counts) caught |
| 3 | MET | `steps or {}`; `status_lines({})` no line; K14 (`steps or {}` removed) caught |
| 4 | MET | `runner.py:59` uses the same `problem_steps`, `WITH_PROBLEMS` unchanged; test 69 builds the real `DayRunner` line from one log |
| 5 | MET | reads only `RunLogReader.steps`; reader refuses odd shapes (`rule_checks.py:71`, K4 caught); wiring pinned (K10 caught) |
| 6 | MET | `rule_checks.py:108,113`: failed/refused decisions give "decisions step <status>: <reason>" with `data_check_failed`; K5 (severity swapped), K6, K9 (refused not a data failure), K17, K18 (C4 skipped on failure) caught |
| 570.1 cond. 2 | MET | a failed decisions result is never iterated as books; `_decided` takes any top-level `status` first |
| pending_judge_I | MET | rule moved, not copied (`runner.problem_steps is run_log.problem_steps`, no `PROBLEMS` in `fno/daily`); `DecisionOutcome` calls `problem_steps`, not the set |

Rule 6 sample: I re-made both Claims samples from the committed code (`status_lines` on the tests' planted logs);
they match the Claims line for line. Every committed run-log version on `main` (86, my own script) passes the new
`_well_formed` check, so no real day turns unreadable.

## Plants (addendum 1)

15 planted on the trial merge, one at a time, run on `tests/cards`, `tests/daily`, `tests/desk` (361 tests), each
restored with `git checkout --` and `__pycache__` cleared; tree clean after. 13 caught. Survivors, both minor:
- K3 (the problem line emitted twice): same as round 1's J15; no test says "exactly once".
- K12 (`_well_formed`'s `all` changed to `any`): every odd-shape test has a single step, so a log with one good and
  one odd step is untested. The code is right (`all`), and `RunLog.record` writes only the accepted shape.

## Gates (5cbd3c4c7 merged with origin/main d5ee18d02, clean; main since moved only by a post-mortem record)

- `ruff check` clean; `ruff format --check` 2445 files formatted; `check_imports` clean (2574 files);
  `check_records` clean (9009 files).
- `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -p no:cacheprovider -n auto`: **15168 passed, 1 skipped, 15
  xfailed, 0 failed** in 523 s (the skip is not in `tests/cards`, `tests/daily` or `tests/desk`: 361 passed, 0 skipped).
- Sizes: largest changed file 181 lines; no class near 350.

## Notes (not findings)

- Minor test gaps: a line-exactly-once test (K3) and a mixed good/odd steps log (K12).
- Round 1's notes stand: the `problems=None` default only for T2's older tests; the pre-existing T2 non-dict per-book
  entry; a malformed previous-day log fails closed.
- Round 1's verdict is confirmed. No blocking or should-fix finding.

## Addendum 2 (merge with R2's final head)

**PASS at 80b5259de, lane 1.** Judge I, own session (session_01CHtddAzFcEdQh4HFiz3mqU). Delta only:
- fa7278957 merges R2's final head ee5711075 (judges 569.3 and 570.3);
- 80b5259de changes one test line.

| Check | Verdict | My evidence |
|---|---|---|
| `git diff ee5711075 80b5259de -- fno/desk fno/daily` empty | MET | 0 lines |
| T1d's own changes since 5cbd3c4c7 are this one line | MET | All six T1d files at fa7278957 are byte for byte those at 5cbd3c4c7 (sha1 of each). `git diff 2c80be430 ee5711075` touches none of them, so the merge resolved nothing in T1d's files. `git diff fa7278957 80b5259de` is the one change |
| The change: `on_its_day=lambda day: True` on the fake DailyRun, nothing else, no assertion weakened | MET | The diff adds only that keyword (with `# fmt: skip`). The assertion `(code, last) == (1, "day done with problems: snapshot, fills")` and the card line are unchanged. R2's runner calls `self.daily_run.on_its_day(day)` (`runner.py:69`). With `True` it reads `retried_steps`, and the test's log has no `retry` key, so the expected line is the same |
| Without the line, the merged pair is red | MET | My plant (the keyword removed) on the trial merge: `AttributeError` at `fno/daily/runner.py:69`, 1 failed. Restored, tree clean |

## Gates (80b5259de merged with origin/main ac88bfeb3 as 7ea6e0f95, clean)

- `pytest -n auto tests/daily tests/timetable tests/desk tests/scoreboard tests/cards`: **646 passed, 0 failed**
  (77 s).
- `ruff check fno tests tools`: clean; the changed test file is formatted.
- Not run: the full suite, which the orchestrator did not ask for. Judges 569.3 and 570.3 judged R2's side.

No finding. On this PASS, R2 (ee5711075) and T1d (80b5259de) may merge together.
