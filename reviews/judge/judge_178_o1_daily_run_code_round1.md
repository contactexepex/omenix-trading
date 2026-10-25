# Judge 178: O1 daily run, code round 1 (story/o1-daily-run at 75d2aa14)

**Verdict: PASS for round 1's scope** (the parts that do not wait for E2c). There is no blocking finding and no
should-fix. Five notes follow. Notes 1 and 2 must be done before the final code PASS or before the merge. Criteria 8
and 9 are not built yet (the reasons are below), so this is not the story's final code verdict.

Story text: `docs/stories/O1-daily-run.md` at 75d2aa14 (text PASS, judge 169 addendum 1). Claims:
`reviews/claude/response_165_o1-daily-run.md`, sections "Code round 1" and "O8 swap".

## Gates

- **Trial merge with origin/main as it was when checked:** clean. `python -m pytest -q` gives 6039 passed (claimed
  6038; main had moved on). `ruff check`, `ruff format --check` and `tools/check_imports.py` are all clean.
- **Trial merge with origin/main at fb4ced9f** (after the LR1 merge a024225a): CLAUDE.md conflicts in the
  composition-root list, and `fno/constants.py` becomes **351 lines**, over the 350 limit, so `tests/test_code_size.py`
  would fail. See note 2.

## Criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Order and days | MET | `test_a_session_runs_every_step_once_in_the_tuple_s_order` (log keys == `DAILY_RUN_STEPS`); the closed-day test; muhurat-only and special sessions keep E3's `RECORDED_SESSION_KINDS` |
| 2 | A failure never stops the next step | PARTLY | Raise and refusal are tested for `weather`, `forecasts_v4` and `book1`. **Not tested:** `card`, `quotes` (a raise in the start step), or a planted failure of each quote part. My probe on the branch's fakes: a raising `card` gives `failed`, one alert and "day done with problems: card"; a NIFTY part that exits 1 gives no O1 alert, NSE and the indices still commit, and the result is "not ok: nifty". So the behaviour is right and only the tests are missing (note 1). The stop test passes as written: the card never runs, E3's alert stands alone and the parts still commit |
| 3 | Restart | MET | `test_a_rerun_skips_every_recorded_step_and_restarts_no_part` |
| 4 | The quote parts are A4c's | PARTLY | Covered: start times (NIFTY and NSE at the run's start), indices after NIFTY's commit, NIFTY committing first, the desk's times unmoved by a 15:13 part, and a hung part. **Not tested:** the story's "a planted NIFTY failure..." case (probe above; note 1) |
| 4a | One git at a time; pathspec commit | MET | Real git: `test_each_part_commits_only_its_own_files_with_another_file_staged`. My mutation removing `-- <paths>` from `commit_paths` fails it |
| 5 | The card is T1's, last, never after the stop | MET | Order test and stop test |
| 6 | Not live | MET | `LiveFrom` tests; `config.yaml` `daily.live_from` all null |
| 7 | O8's contract | MET | O8 imports `DAILY_RUN_STEPS`; its private tuple and source-parsing test are gone; failed or refused are problems, `not_live` is neither missed nor a problem (new tests) |
| 8 | One prompt (CLAUDE.md section) | NOT BUILT (stated) | Waits for A4c's merge so it can carry A4c's lines word for word |
| 9 | Real day | NOT BUILT (stated) | Waits for the owner pasting the prompt |
| 10 | Engineering | MET at 75d2aa14 | `DayStep` interface; wired in `fno/daily/wiring.py` (listed in CLAUDE.md); largest new file 135 lines; no secret; never orders. Merge note 2 |

## Claims checked against reality

- **"The parts never run git."** True. `fno/quotes`, the weather and v4 capture modules have no git calls. The card only
  reads git (`GitHeadRecords`) and runs in the foreground after `quotes_done`. `desk book1` does run git (E5b's own
  commit), but it runs in the foreground while the run's only thread is blocked in `wait()`, so it never interleaves
  with a part's commit.
- **Pathspec commits keep the record scan.** Checked in a scratch repository with the real `.githooks`: a part file
  holding a planted e-mail address, committed through `Git.commit_paths` by pathspec, is refused by the scan
  ("e-mail address", values not shown). Nothing was committed.
- **Planted faults.** I re-planted two of the builder's four: no `--` pathspec, and indices that do not wait for NIFTY.
  Each made `tests/daily` fail (1 and 2 failures); both were reverted.
- **`fno desk run` removed.** Nothing calls it (no workflow, CLAUDE.md or routine line). Its CLI test is replaced by
  the runner's stop test and the `daily` CLI test.

## Text amendment: the `book1` step (accepted)

Reason: on main nothing calls `fno desk book1`. A `grep` of `.github/`, CLAUDE.md and the docs finds no caller, and
E5's own docstring said "No routine starts them yet". E3's `decisions` step only collects committed D3 records, so
without this step Book 1 records "no decision (late)" every session.

Placement is right. It runs after `pack`, which it needs, and before the 15:12 deadline. Its pathspecs are empty,
so the run sweeps up nothing of its own. E5b, which owns `fno/books/book1*`, is merged (bd6ff1e2 is on main), so
removing `add_run_command` from `book1_cli.py` collides with no open branch.

The stated duplicate alert on a failed Book 1 commit (E5b's alert plus "step book1 failed") is acceptable.

## Notes

1. **(Before the final code PASS) Close the criterion 2 and 4 test gaps.** Add a raise for `card` and `quotes`, a
   planted failure (non-zero exit) for each quote part, and the NIFTY-failure case. The behaviour is already right (my
   probe), so these are tests only.
2. **(At the merge) The merged tree overflows `fno/constants.py`.** With main at fb4ced9f the file reaches 351 lines,
   and CLAUDE.md's composition-root list conflicts with LR1's addition. When merging, split a cohesive block out of
   `fno/constants.py` (never squeeze lines) and keep both composition-root entries. Then re-run the full suite on the
   merged tree.
3. **(Merge order) O1 merges only after A4c.** `quotes record-indices` does not exist on main yet. If O1 lands first,
   the indices part would fail every day with an argparse error, recorded quietly under `quotes_done` (no alert by
   design). This is already implied by the CLAUDE.md section waiting for A4c; stated here so the merge check holds it.
4. **(Optional) A rerun after a died run.** The rerun's `quotes_done` records `NOT_IN_THIS_RUN`, and any part files
   the dead run wrote stay uncommitted until fixed by hand. The rerun could commit what it finds under each part's
   pathspecs. A session dying mid-day is a stated known limit, so this is not a should-fix.
5. **(Register) Ownership of the prompt.** `docs/WORK_REGISTER.md` still lists the Handover / routines row as owning
   "CLAUDE.md 3 pm section, routine prompts", and O1's row claims the same files. The orchestrator's ruling gives the
   prompt to O1 (story text, "Ownership of the prompt"). The orchestrator should update the Handover row so the
   register shows one owner. The E5b row also still reads "after E2c" although E5b is merged.

## Addendum 1: delta to 22e4dd7f (margin_check step, constants split)

**Verdict: PASS for round 1's scope.** This delta adds no blocking or should-fix finding. Note 2 is closed. Note 1
stays open: the criterion 2 and 4 tests have not arrived yet. Note 6 is new and optional.

- **Gates on a trial merge with origin/main (4e72c4e4 line, 15 Oct evening):** 6142 passed. `ruff check`,
  `ruff format --check` and `check_imports` are clean, and `tests/test_code_size.py` passes. `fno/constants.py` is now
  341 lines and `fno/constants_operations.py` 37.
- **The split (closes note 2).** The daily-operations block moved out whole. All 15 names in `__all__`
  (`RUN_LOG_DECISIONS_STEP`, the two step tuples, O1's four statuses and O8's health names) read the same through
  `fno.constants` as through the new module (checked in Python). The health values equal main's lines 343-346, and
  `RUN_LOG_DECISIONS_STEP` is still "decisions". It is one `import *` driven by an explicit `__all__`, so no caller
  changes. This is a split, not a squeeze. The CLAUDE.md conflict is resolved: both the LR1 and O1 composition roots
  are listed.
- **`margin_check` (text amendment, accepted).** It records A14c's agreed line (decision da0f769d; the A14c builder,
  15 Oct) as O1's first step. It runs the unchanged command, commits only `stress_broker_check.csv`, and stays
  `not_live` (`daily.live_from.margin_check: null`) while the command does not exist, so nothing calls Groww today.
  Tests: the order, failure and rerun tests now include it. The new wiring test shows the composition root gives every
  name in `DAILY_RUN_STEPS` a step.
- **T2's note (judge 180): the card comes after `decisions` and after 15:15.** MET by the order. `card` follows
  `quotes_done`, which follows `exits`. `exits` waits until `desk.timetable.execution_snapshot` (15:15), so the card
  can never start before 15:15 or before `decisions` (15:12).

6. **(Optional, reasoning only) Put `margin_check` after `quotes`, not before.** Each `CommandStep` waits for its
   child with no time limit. As the first step, a Groww call in A14c's command that hangs would hold back the start of
   the quote parts, the day's main data. The parts are child processes that wait for 14:55 themselves, so starting
   them first costs nothing and still avoids overlapping the 14:55 capture on the Groww key. There is no evidence of a
   Groww hang, so this is not a should-fix. Otherwise, when A14c lands, confirm its Groww request has a timeout.

## Addendum 2: O1 at f22ffc42 (note 1 tests; E2c merged in)

**Verdict: PASS for the code built so far.** No blocking or should-fix findings, and notes 1, 2 and 4 are closed.
Criteria 2 and 4 are now MET. Still to come before the story's final code verdict: criterion 8 (the CLAUDE.md section,
after A4c) and criterion 9 (the real day).

- **Note 1 closed.** New tests:
  - `test_quotes_or_card_raising_is_recorded_failed_with_one_alert` (quotes, card);
  - `test_a_quote_part_that_exits_non_zero_gets_no_o1_alert_and_the_others_still_commit` (each of the 3 parts);
  - `test_a_failed_nifty_still_starts_the_indices_after_it_and_lets_nse_commit`.

  Each asserts what my probe found: one O1 alert for a step that raises, none for a part (A4c's own alerts stand),
  the others still commit, and the indices start when NIFTY ends, whatever NIFTY's result.
- **Note 4: declined, and I accept the reason.** A killed recorder can leave a half-written sidecar or canonical, and
  only the recorder can tell whether an attempt is complete. Committing blind could put a broken record on `main`. The
  limit is now a Known-limits line.
- **E2c merge.** The resolution keeps both additions: E2c's `files` (private records downloaded before any step) with
  `_unreviewed` passed to `fills`, and O1's `day_steps`. `build_daily_run` passes both. The real-git pathspec test now
  stages a tracked file of another writer, because E2c ignores the account files in git. That is right: the test still
  proves a staged file is never swept in.
- **Gates on a trial merge with origin/main f78c7759:**
  - 6175 passed, 3 failed;
  - plain main at f78c7759, run at the same time: 6118 passed and **the same 3 failed** (`test_paper_account` 15 Oct
    top-up, `test_committed_closes_reproduce_the_disclosed_v6_counts`, `test_home_blocks` live wiring);
  - none of the 3 is in O1's files, so the builder's claim holds. Merge rule: they must be green on main (their owners'
    fix) before O1 merges, since the merge needs the full suite green on the merged tree;
  - `ruff check`, `ruff format --check` and `check_imports` are clean.
- Note 3 (merge after A4c) stands, and so does optional note 6 (start `quotes` before `margin_check`). The builder
  did not mention note 6.

## Addendum 3: O1 at 43943a52 (note 6 built: quotes first, 10-minute command limit)

**Verdict: PASS for the code built so far.** No blocking or should-fix findings. Note 6 is closed. Criteria 8 and 9
and the merge after A4c are still to come.

- **Order.** `DAILY_RUN_STEPS` now starts with `quotes`, then `margin_check`, so the quote parts (child processes that
  wait for 14:55 themselves) always start before any command that might call Groww. My mutation swapping the two
  makes `tests/daily` fail. The story table and the "No command holds the day" line match the code.
- **Limit.** Every O1 `CommandStep` (margin_check, weather, forecasts_v4, book1, card) is stopped after
  `COMMAND_LIMIT_SECONDS` = 600 and recorded `failed`, with nothing committed. The new test proves the stop, the
  10-minute bound and the empty paths. My mutation removing the limit makes it fail.
- **Gates on a trial merge with origin/main:**
  - 6176 passed, 3 failed: the same 3 that are red on plain main (judge 178 addendum 2), none in O1's files;
  - `ruff check`, `ruff format --check` and `check_imports` are clean.

Notes (one line each, reasoning only, not should-fix):

7. A 10-minute limit does not protect the 15:12 deadline for `book1`, which starts after the pack (up to about
   15:10). A hung `book1` could push `decisions` to about 15:20. E3's late rule then applies and the exits still run,
   so no trade or stop is decided wrongly. The claim "never holding the deadline" is too strong for `book1`.
8. `ChildProcess.stop()` kills only the Python child. A `git push` that `book1` started could outlive it and touch
   the checkout while the run goes on. No evidence that this happens, and a 10-minute hang of `book1` has not been
   seen either.

## Addendum 4: O1 at 71b00878 (notes 7 and 8)

**Verdict: PASS for the code built so far.** No blocking or should-fix findings. Notes 7 and 8 are closed.

- **Note 7.** The `CommandStep` docstring and the story's "No command holds the day" line now say plainly that the
  10-minute limit does not protect 15:12 for `book1` (which can start at about 15:10), and that E3's late rule
  decides that case. The claim now matches the behaviour.
- **Note 8.** Children start with `start_new_session=True`, and `stop()` kills the whole process group (`killpg`,
  SIGKILL; a child that already ended is tolerated). This also covers a quote part stopped at `FINISH_LIMIT`. The new
  test, `test_stopping_a_command_kills_what_it_started_too`, uses a real grandchild and checks it is dead (zombies
  count as dead). My mutation removing `start_new_session` makes it fail.
- **Gates on a trial merge with origin/main dd35b2e5:** the suite is now **fully green, 6180 passed** (main's fixes
  for the 3 earlier red tests are in). `ruff check`, `ruff format --check` and `check_imports` are clean.
- One-line note, reasoning only: in their own session, the children no longer receive a Ctrl-C or SIGTERM sent to
  the routine's process group. If the run itself dies, a running recorder carries on with no one to commit its files.
  That was already the case for a crashed parent, and the stated known limit (a rerun after a dead run) covers it.
  Nothing to change.

Still to come: criterion 8 (the CLAUDE.md section, after A4c), criterion 9 (the real day), and the merge after A4c.

## Addendum 5: O1 at 3e955e0c, re-run on main with parallel tests (orchestrator, 15 Oct)

**Verdict: PASS for the code built so far, unchanged.**

- **What moved since 71b00878:** main merges plus two story-text commits, 590d9491 (E8's `owner_timing_fills`) and
  68e548f0 (M2's `weather_alert`). No O1 code changed.
- **Gates on a trial merge with origin/main:** `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto` gives
  **6579 passed in 2 min 45 s**, with no test that fails only in parallel. `ruff check` and `check_imports` are clean.
- **The two text additions are accepted as records of agreed interfaces, not O1 scope.** Each step is built and
  judged in its own story after O1 merges, and O1 adds no code for either. Both sit after `quotes`, so neither can
  delay the 3 pm parts.

  For E8's and M2's judges, one point, reasoning only: E8's step is planned as its own `DayStep`, not a
  `CommandStep`, so it does not get O1's 10-minute limit. Whoever judges E8 should check it cannot hang the day
  before the exits.

## Addendum 6: O1 at ea008836 (unsent alerts are printed)

**Verdict: FAIL, one should-fix.** The new `ReportedAlerts` is right as far as it goes. But checking it showed a gap
of the same kind that I missed in addenda 0-5, so I own that miss here.

- **What is right.** Every alert the run sends itself (O1's step alerts, the quote parts' "NOT committed", and E3's
  desk alerts through the new `alerts` parameter) prints "alert NOT sent: <reason> | <text>" when Slack does not take
  it. The default for `build_daily_run` is unchanged for E3. Two tests cover this. Gates on a trial merge with
  origin/main: `-n auto` gives 6584 passed in 2 min 49 s; `ruff check` and `check_imports` are clean.
- **Should-fix 9: child commands' own "alert NOT sent" lines never reach the routine.**
  - **Path:** every O1 child (the three quote parts, `book1`, `card`, and later `margin_check`, `weather`,
    `forecasts_v4`) prints into a temporary file (`ChildProcesses.start`, `stdout=output`). The run keeps only the
    last 10 lines, inside the run log's `result.lines`, and never prints them.
  - **What is lost:** the recorder sends its own three alerts ("calendar says session, no same-day trades", "stopped,
    nothing recorded", "raw quote file NOT saved to Drive"; CLAUDE.md step 4). E5b's `cmd_book1` sends its own
    "NOT committed" alert, and the card prints its post outcome. When Slack is down or the token is missing or
    expired, each of these prints "alert NOT sent: ...". Today the routine sees that line and posts it with the Slack
    connector (CLAUDE.md steps 3-4). Under O1 the line goes only into a temp file. It may fall outside the 10 kept
    lines, and the routine is never shown it. So a "raw quote file NOT saved to Drive" day, on a day Slack also fails,
    reaches no one.
  - **Evidence:** the code (`processes.py` stdout to a temp file; `runner.py` prints one line; `KEPT_LINES = 10`).
    The alert texts come from CLAUDE.md and `fno/quotes/cli.py`.
  - **Expected fix (small):** when a child ends (or is stopped), the run prints, as they are, every line of its output
    that contains `alert NOT sent`. Read the whole output, not just the kept 10, before the temp file closes. Add one
    test: a fake child that prints an unsent alert line among more than 10 lines, and that line appears on the run's
    output. Criterion 8's routine line ("if the command printed 'alert NOT sent', post its lines") then covers child
    alerts too.

Everything else stays as in addendum 5.

## Addendum 7: the orchestrator's four checks on ea008836 (fix commit 48d58a97)

The verdict stays **FAIL**. Should-fix 9 gains part (b), from check 1.

1. **Does every alert path go through `ReportedAlerts`? No.**
   - **Covered:** O1's steps (`Alerted`), the quote parts' "NOT committed", and E3's `DeskSteps` and `_guarded`. The
     latter two get `alerts` from `build_daily_run`'s new parameter.
   - **9(b), in process, bypassing the wrapper:** two more senders are built inside the run with their own
     `build_alert_sender()` and never see the wrapper. Their "alert NOT sent" outcome is dropped exactly as before:
     - `build_exit_desk` (`fno/desk/wiring.py:41`, `ExitDesk`), the exits' alerts;
     - `build_book1_exit_rules` (`fno/books/book1_wiring.py:72`, `PlaybookExitRules`).

     The exits are the one step that must always be seen (design 9). Fix: pass the run's `alerts` into both (the same
     `alerts=None` default keeps their other callers unchanged). Extend the wiring test so that every sender the run
     builds is the `ReportedAlerts` instance.
   - **9(a), child processes:** as in addendum 6, their own lines are never relayed.
2. **Is E3 unchanged without the parameter? Yes.** `alerts or build_alert_sender()` in `build_daily_run`, and E3's
   tests pass unchanged.
3. **Can the printed line hold a token or secret? No.** The line is "<outcome> | <text>". By the `AlertSender`
   contract the outcome never holds the token: `slack_post` returns only the exception's type name or Slack's error
   code. The text is the alert text, which is already posted to Slack and committed in run logs, so the line adds no
   new exposure.
4. **Would the tests catch a dropped outcome? Partly.** `test_steps.py` checks that `ReportedAlerts` prints the unsent
   line and stays quiet on a sent one, and that the wiring hands the run a `ReportedAlerts`. It would not catch the two
   bypassing senders in 1, or the children's lines (9(a)).

## Addendum 8: O1 at d03d5d97 (should-fix 9(a) built)

**Verdict: FAIL.** 9(a) is closed. 9(b) (addendum 7) is not built yet; this commit was probably made before the
builder saw addendum 7.

- **9(a) closed.** `ChildProcess` reads the child's whole output once, both when the child ends (`lines()`) and when
  it is stopped (`stop()`). It prints every line containing "alert NOT sent" exactly as written; the phrase comes from
  the sender's own `NOT_SENT`, so the two cannot drift apart. The run log still keeps the last 10 lines. The quote
  parts and the `CommandStep`s both reach that read: `_finish` and `CommandStep.run` call `lines()`, and
  `QuoteParts.finish` and `CommandStep` call `stop()`. Two real-child tests cover it: the line among 14 lines, and a
  child stopped while asleep. My mutation that never reports fails 2 of them; `tests/daily` passes 39.
- **9(b) open.** `ExitDesk` (`fno/desk/wiring.py:41`) and `PlaybookExitRules` (`fno/books/book1_wiring.py:72`)
  still build their own senders inside the run. Expected fix as in addendum 7.

## Addendum 9: O1 at f01bf9d7 (should-fix 9(a) and 9(b) built)

**Verdict: PASS for the code built so far.** Should-fix 9 is closed (both parts), and there are no new findings.
Still to come: criterion 8 (the CLAUDE.md section, after A4c), criterion 9 (the real day), and the merge after A4c.

- **9(a):** as in addendum 8, unchanged.
- **9(b):** `build_exit_desk(cfg, alerts=None)` and `build_book1_exit_rules(root, alerts=None)` now take the run's one
  `ReportedAlerts`, and their other callers keep `build_alert_sender()`.
  - **My grep** of every `build_alert_sender()` in `fno/` at f01bf9d7 finds no other sender built inside the run's
    process: the gate gets the run's `alerts`, and the rest are other commands' CLIs and wirings. Book 1's decider
    (`book1_wiring.py:33`) runs in its child process, which 9(a) relays.
  - **The new test** `test_every_sender_inside_the_built_run_is_its_one_reported_sender` walks the real run's
    objects. My mutation putting `build_exit_desk(cfg)` back fails it.
- **Gates on a trial merge with origin/main:** `-n auto` gives **6590 passed** in 2 min 48 s; `ruff check` and
  `check_imports` are clean.

## Addendum 10: O1 at 0dbe8f94 (the whole git history first; main merged)

**Verdict: PASS for the code built so far.** No blocking or should-fix findings.

- **`Git.unshallow` and `WholeHistory`.** Asked for by E8 (judge 203 should-fix 1).
  - **Behaviour:** when `git rev-parse --is-shallow-repository` says true, the run fetches the full history before
    the first step. A failed fetch sends one alert through the run's `ReportedAlerts` and the day goes on. That is
    the right choice: stopping the day would lose the quotes and the exits, and E8's step refuses by itself in a
    shallow checkout.
  - **Tests:** a real shallow clone becomes whole; a whole checkout is left alone; a missing origin gives one alert;
    the runner fetches the history before the day.
  - **Timing, measured by me:** a fresh `--depth 50` clone of exepex/trading took **6.7 s** to unshallow (2,756
    commits, pack about 139 MiB). It finishes long before 14:55.
- **Merge.** main's `RUN_LOG_EXITS_STEP` moved into `fno/constants_operations.py` (listed in `__all__`), and
  `DESK_RUN_STEPS` uses it. Sizes: `constants.py` 338 lines, `constants_operations.py` 48.
- **Gates on a trial merge with origin/main:** `-n auto` gives **6859 passed** in 2 min 55 s; `ruff check` and
  `check_imports` are clean.
- **One-line note, reasoning only:** the fetch has no time limit and runs before `quotes`, so a hung fetch would hold
  back the 3 pm parts. A `timeout` on this one git call, or starting `quotes` first, would close that. The measured
  6.7 s says it is unlikely.

Still to come: criterion 8 (after A4c), criterion 9, and the merge after A4c.

## Addendum 11: O1 at 8a7ca874 (quote parts before the download; E4c's double print removed)

**Verdict: PASS for the code built so far.** No blocking or should-fix findings. This closes judge 204's note A (the
O1 side) and note B.

- **Parts before the download.** `DayRunner` now starts the quote parts after the whole-history fetch and before
  `DailyRun.run`, so before E2c's download. A Drive outage at the download therefore stops the desk with E3's one
  alert, but the parts still end and commit (NSE needs no Drive).
  - **After a stop,** `_finish_parts` waits at least until `desk.timetable.fills_by` (read from the timetable, not
    typed), so a stop at 14:35 still covers every part's window.
  - **No double start.** A rerun whose log already holds `quotes` starts no part, and the `quotes` step's own
    `start` does not start them again (`QuoteParts.start` acts once per day).
  - **A closed day.** Each recorder exits on its own calendar rule; `busy()` ends the wait at once and nothing is
    committed.
  - **Tests:** the Drive-down-at-download case (stop line, one alert, the three part commits); the closed-day case;
    the order history, then parts, then day. My mutation removing the early start fails 3 tests in `tests/daily`.
- **E4c's double print.** The `print(outcome)` in `DeskSteps._fill_one` is gone (E4c's owner agreed). The unsent
  line now comes once, from `ReportedAlerts`, and E4c's text and test say so. `build_daily_run`'s default sender is
  reached only by E3's own tests, so no live path loses the line.
- **Gates on a trial merge with origin/main:** `-n auto` gives **6860 passed** in 3 min 2 s; `ruff check` and
  `check_imports` are clean.

Still to come: criterion 8 (after A4c), criterion 9, and the merge after A4c. Judge 204's O2 row (a) should now say
that the parts still record on a download outage; the O2 builder updates it with the code.

## Addendum 12: O1 at d123dbb9 (addendum 10's note done)

**Verdict: PASS for the code built so far.** Addendum 10's note is closed.

- **Order.** The quote parts now start before the whole-history fetch and before the Drive download, so neither can
  delay the 3 pm parts.
- **Time limit.** `Git.unshallow` runs with a hard limit of 120 s (`subprocess` timeout). A time-out becomes a
  `GitError`, which means one alert and the day goes on.
- **Test.** `test_a_hung_fetch_is_stopped_at_its_limit_and_is_one_alert` covers it. My mutation removing the timeout
  makes it fail.
- **Gates on a trial merge with origin/main:** `-n auto` gives **6870 passed**; `ruff check` and `check_imports` are
  clean.

Still to come: criterion 8 (after A4c), criterion 9, and the merge after A4c.

## Addendum 13: O1 at efa57570 (E6's pauses in the run, commit b2d98c40)

**Verdict: FAIL, 1 should-fix.** The design is right:
- E6's real `ScorecardRun` runs with `pause=True` after `exits`, through the run's one `ReportedAlerts`, and commits
  `playbook/`;
- `DailyRun._unscored` blocks every book's entries at the next session when the step failed, was refused or never ran
  after the exits;
- the exits always run.

This closes judge 214's gap: nothing ran E6's pauses before. It is a text amendment that adds safety, and I accept it.

- **Checked:**
  - `_unscored` returns nothing when the last log has no `exits`, so E3's `_unreviewed` covers that case without a
    double block;
  - it is off when the run has no `reviews` step (E3's own tests);
  - the default for a missing step is `failed` / "not run".
- **Gates on a trial merge with origin/main:** `-n auto` gives **6899 passed**; `ruff check` and `check_imports` are
  clean. The builder's planted faults (no `_unscored` in the fills; `pause=False`) are named with the tests that catch
  them.
- **Should-fix 10: a day without a valid snapshot blocks the next day even when there is nothing to mark.**
  - **Path:** `ReviewsStep.run` returns `refused` whenever the snapshot is not valid, so `_unscored` then blocks
    every book's entries the next session. The stated reason is that open positions cannot be marked.
  - **Why that is too wide:** with no open position in any book, nothing needs marking. Closed losses are still
    judged (the builder's own test), so the refusal costs a trading day and protects nothing.
  - **It happens in normal running:**
    - the 15:15 capture failing twice is a normal case (O2's Groww family; C3's "no valid execution snapshot");
    - today all three books hold 0 open trades (`journal/*/daily_totals.csv`, judge 216's count);
    - so the first capture failure blocks the next session for nothing.
  - **Fix:** refuse only when some book has an open position (through the same `paper_accounts` and `DeskRecords`
    the scorecard reads). With none, record `ok`, saying "no open position to mark". Add one test each way.

## Addendum 14: O1 at e57046f3 (should-fix 10)

**Verdict: PASS for the code built so far.** Should-fix 10 is closed.

- **The rule now.** With no valid snapshot, `ReviewsStep` is refused only when the scorecards count an open position
  (`sum(len(card.open_marks))`). With none open, it is `ok`, ending "no open position to mark". A closed loss still
  pauses either way.
- **The count is the real one.** `build_scorecard` makes one `OpenMark` for every open trade, marked or not, so an
  empty mark set still counts each open trade (the refused test has 1 open trade and reports `open=1`).
- **Tests and mutation.** One test each way, with the real `ScorecardRun`. My mutation putting the old rule back
  (`if valid:`) fails the nothing-open test.
- **Gates on a trial merge with origin/main:** `-n auto` gives **6900 passed**; `ruff check` is clean.

Still to come: criterion 8 (after A4c), criterion 9, and the merge after A4c.

## Addendum 15: head e5ac277e (criterion 8, the routine text; final before merge)

**PASS on criteria 1-8 and 10. Criterion 9 (one real trading day) is a post-merge check:** the routine runs `main`,
so it cannot happen before the merge and the owner's new prompt. Since e57046f3 there are two commits:
- **017f3203**, a merge of main. Its one conflict, in `fno/constants.py`, keeps main's `ENV_GITHUB_OUTPUT` and
  `PROTOCOL_*` (344 lines).
- **e5ac277e, criterion 8:** CLAUDE.md's "3 pm quote recorder" section becomes "Daily desk routine".
  - The stored prompt is one sentence, and O7's setup line is unchanged.
  - `python -m fno daily run` is listed with its three end lines and the "alert NOT sent" and conversation-log rule.
  - A sub-section gives A4c's steps word for word. **My script comparison:** steps 2, 3, 3b and 4 equal the text on
    `story/a4c-all-indices` 0be99326 exactly. It is led by "the routine never runs these commands itself … the `git
    add` lines are also the hand fix".
- **Trial merge in the real order** (main, then A4c 0be99326, then O1 e5ac277e):
  - **CLAUDE.md conflicts** (A4c's section against O1's rewrite). Resolve with O1's version. I checked that nothing of
    A4c's is lost: the only A4c lines missing from O1's file are old main wording that main has since reworded (O8,
    LR1, O9).
  - With that resolution, 7293 passed (`-n auto`, Slack token unset).
  - `tests/quotes/test_routine_commit_paths.py` (A4c's), `tests/daily/test_routine_section.py` and
    `tests/test_routine_setup.py` pass on the merged CLAUDE.md.
- **Post-merge (criterion 9, as rule 8):** on the first trading day after the merge and the owner's prompt, the run
  log `journal/runs/<date>.json`, the commit list (each part's own commit, NIFTY first) and the card go into response
  165. I check them then.

## Addendum 16: head 4a4bede0 (A4c merged in), then E2d on main

- **4a4bede0 itself:** it contains A4c (9d7e92b4). The "Daily desk routine" section is unchanged from e5ac277e (diff
  empty), and the builder reports 7383 passed. Addendum 15's PASS covers its content, and criterion 9 is a post-merge
  check on Monday 19 Oct, as the orchestrator accepts.
- **But main has moved:** E2d (8349f141, "per-trade daily marks after the exits", judge 262 PASS) merged after it. A
  trial merge of 4a4bede0 with main 8349f141 **conflicts in code**: `fno/desk/daily_run.py`, `fno/desk/daily_wiring.py`,
  `fno/health/desk_checks.py`, `tests/health/test_desk_and_data_checks.py` and `tests/timetable/test_entry_check_alert.py`.
  Unresolved, 26 tests fail and 20 error.
- **Not mergeable as is.** Merge main (E2d) into `story/o1-daily-run` and resolve. E2d's marks step must keep its place
  after the exits inside O1's run (`DAILY_RUN_STEPS`, with O8's tuple), and must not run as a second desk path. Then
  send me the head. I re-check the resolved files and run the full suite.

## Addendum 17: merge resolution 8534b2b8 (main d86e4584: A4c and E2d)

**PASS: O1 may merge.** Criterion 9 is a post-merge check on Mon 19 Oct (addendum 15).
- **Parents:** 4a4bede0 and d86e4584. Every file that differs from main is one O1 already changed (the builder's `comm`
  check; I reran it, and it is empty).
- **E2d's step inside O1's run:** `"trade_marks"` is in `DESK_RUN_STEPS` right after `exits`, so `DAILY_RUN_STEPS`
  runs exits, then trade_marks, then reviews, then quotes_done, then card. The desk plan runs `self.marking.run(day)`
  at the execution snapshot, and `MarkingStep` takes the run's one alert sender. There is no second desk path. O8
  reads the constant, with no local tuple.
- **`AFTER_EXITS` is derived from `DAILY_RUN_STEPS`** (exits and every later step) instead of E2d's fixed pair. That
  is right: the fixed pair would have said "exits not reviewed today" for a stop at reviews, quotes_done or card. The
  new parametrized test fails with the fixed pair put back (builder).
- **Gates:** a trial merge of 8534b2b8 with current main is clean, ruff and check_imports clean, and 7441 passed with
  3 failed. **The 3 failures are red on main too** (I reproduced them on a clean `origin/main`):
  - `tests/risk/test_manager.py` (2);
  - `tests/risk/test_stress_factor.py::test_the_repository_seed_row_is_read_by_c2_and_c4`.

  Cause: A14c's first Actions run (df9bfaff) appended the 16 Oct factor row (2.1, applied), and these tests read the
  live `stress_factor.csv` assuming the 14 Oct seed row is the latest. They are not O1's. They are main's, and the
  owner of C2d's tests must fix them: the tests should use their own planted factor file, not the live one.
- **The builder's stash slip:** checked. The commit has both parents, and the tree checks out as above.

## Addendum 18: head edb4e2b6

**PASS, O1 may merge once main is green.** It is 8534b2b8 plus one commit, which names E2d's step as
`RUN_LOG_TRADE_MARKS_STEP` in `fno/constants_operations.py` (the fixed-strings rule) and uses it in `DESK_RUN_STEPS` and
the desk plan. There is no behaviour change. Full suite on edb4e2b6: 7410 passed and 3 failed, the 3 risk tests that
are red on main itself (addendum 17).

## Addendum 19: O1 criterion 9, the real days (claims at story/o1-criterion-9 3de993be)
**Verdict: criterion 9 MET, except "the card in #fno-desk", which stays OPEN until T1's card goes live.** I checked
the run logs and the commit list on main myself.

| Part | Result | Evidence |
|---|---|---|
| Every step recorded, once, in `DAILY_RUN_STEPS` order | MET | `journal/runs/2026-10-19.json` and `2026-10-21.json` hold all 16 steps (`quotes` … `candles`); 20 Oct is `skipped` ("not a session day") |
| Every record committed; NIFTY first | MET | 19 Oct (IST): `3 pm quotes nifty` 14:57:57, `nse` 14:58:01, `indices` 15:05:34. Then `book1` (decision `bd11a8de`, committed 14:58:45), `decisions` at 15:12, the snapshot `nifty_20261019_151500` valid, and fills, exits, trade_marks, reviews, quotes_done, card and candles, each step its own commit |
| A16's marks beside the 3 pm capture | MET (checked as a risk) | A16's 14:45, 15:00 and 15:15 marks on 19 Oct are all `good`, and quotes_done says "every part ok", so the two Groww users did not cost the capture anything that day (one day: some evidence) |
| The card in #fno-desk | **OPEN** | `daily.live_from.card` is null, so the step is `not_live` and no card was posted. The owner sets the date; the part closes on the first live card day |
| Not-live steps | as designed | margin_check, weather, forecasts_v4 and card are `not_live` (no `live_from` date). Book 1 decided, with no trade (no `paper` strategy) |

**My Monday check, "NIFTY and NSE started at about 14:38".** It cannot be read directly: the log holds no start time
per part, and `quotes`' reason "started nifty, nse" has been misleading since 7b08108c, because the parts now start
later, at 14:38. The indirect evidence holds: attempt `nifty_20261019_145500` shows the recording waited for its
window, and nothing printed "too early". The builder will fix the wording in the next O1 change; it should then record
each part's start time.

**Note for the owner:** S1's "one live day" is met by the run itself, but the desk has not traded yet. Every Book 1
decision so far is no-trade, because no strategy has `paper` status.
