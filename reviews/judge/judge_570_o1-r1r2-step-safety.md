# Judge 570: O1's DRY2 fixes R1 and R2, story/o1-r1r2-step-safety

- **Judge:** E (session_01HkXMVPDEqVsmJZtghFrGzM), lane 1 (the money path), round 1 of 2
- **Head judged:** e8dc9498, which already contains main
- **Claims:** docs/stories/O1-daily-run.md, "Fix after DRY2: the indices' own early limit and one failed step
  never ends the day"
- **Verdict: PASS. Merge go,** before Mon 26 Oct 14:05 IST.

## Gates
- pytest -n auto: 15115 passed, 0 failed.
- ruff check, ruff format --check, check_imports, check_records: clean.

## R1: the indices wait for their own early limit (code read, plants)
- The indices part's `not_before` is now `INDEX_EARLIEST_START`. It is computed from A4c's own window by
  the same rule as NIFTY's (14:44 today).
- `start_due` starts a part only when three things hold: it is unstarted, the part it waits for has ended,
  and its own time has come. `service` ends by calling `start_due`, so the old path that started a waiting
  part regardless of its time is gone. `next_start` counts a waiting part once its leader has ended, so the
  run's waits wake for it.
- Plants:
  - R1a (no early limit for the indices): caught.
  - R1b (a waiting part ignores its limit): caught.
  - R1c (`next_start` skips waiting parts): caught.

## R2: one failed step never ends the day
- `_run_step` catches any other `Exception` in an in-process step. It logs the step failed as "Type: first
  line", sends the alert, and the run goes on. `CommitFailed` and `GitFailed` are re-raised and still stop
  the run through `_guarded`.
- Only in-process steps change: versions, pack, decisions, snapshot, fills, exits, marks and the in-process
  day steps. The child-process steps, such as `book1`, were already non-fatal through `Alerted`.
- The deliberate refusals stay where they were: `OrdersRefused` and `AccountWriteRefused` are caught per
  book or trade inside `fill`. No step's stop signal is swallowed, because `RunStopped` comes only from
  `_guarded`.
- `fills` is refused when snapshot or decisions failed. Exits and marks still run, so risk-reducing exits
  happen. A failed exits step makes every book unreviewed the next day, so no book opens anything new.
- Plants:
  - R2a (catch narrowed): caught.
  - R2b (`NEEDS` dropped): caught.
  - R2c (the failed-exits rule dropped): caught.
  - R2d (commit and git failures swallowed): caught, 8 failed.
  - R2e (git failures swallowed): caught.
  - R2f (no alert): caught.
- Before R2, a pack or snapshot exception stopped the whole run before its exits. Now the exits run. That
  is the safer direction for open positions.

## Minor (not blocking)
1. **R2b2 survives:** `NEEDS` without "decisions" passes every test.
   - It is close to harmless: a failed decisions result holds only `status` and `reason`, so `fill` finds
     no book's `run_id` and fills nothing.
   - Pin it with one test, so the refusal does not rest on that accident.
2. **A partial fill reads as nothing filled.** `fill` writes each trade to the account as it goes. An error
   after some trades leaves them in the account, which exits then review correctly, while the run log and
   the alert say "step fills FAILED" with no trades listed.
   - Suggest the fills alert adds "trades written before the error stay in the account; check it", so the
     owner is not misled.

## Plants: 10 planted, 9 caught, 1 survived (R2b2, minor)

## Addendum 1

- **Head:** f0bb2aa9, round 2, answering judge 567 and the orchestrator.
- **Verdict: PASS (my half). Merge only together with T1d (item 2 below).**
- **Gates (merged as 8e1ae083):** pytest -n auto: 15120 passed, 0 failed. ruff check, ruff format --check,
  check_imports and check_records: clean. These finished after the handover note was written.
- **Done:**
  - Code delta read: fills is refused when an input step has not run or failed; `problem_steps` and
    `book_results` live in run_log.py; the scoreboard reads a failed decisions step as no books.
  - Plants on tests/daily, tests/timetable, tests/desk, tests/scoreboard and tests/cards (592 tests):
    - M1 (missing-input check dropped): caught.
    - M2 (scoreboard decisions without `book_results`): caught.
    - R2b2 (`NEEDS` without decisions): survives again. It fails closed anyway: no run_ids, so nothing
      is filled.
    - M3 (scoreboard exits without `book_results`): survives, but it is equivalent. A failed result looked
      up by book gives `{}` either way.
- **Conditions:**
  1. The full gates are done (above), so no judge work remains on this story.
  2. A merge-order risk: `fno/cards/rule_checks.py:97` iterates the decisions result.
     - On a failed decisions step it would list "status" and "reason" as late books, because
       `"run_id" not in "failed"` is True on strings.
     - The builder says T1d fixes the card's reader and merges together with R2. Do not merge R2 without
       T1d.
- REH1g has not reached me.

## Addendum 2

- **Head:** 2c80be430 (story/o1-r1r2-step-safety-b), a re-check of my round-2 PASS at f0bb2aa9c. Judge E
  (session_01Mt6dcBU5kp2htdPN2KmiZH), lane 1, money path. Rounds are spent, so a finding goes to the owner.
- **Verdict: FAIL, 1 should-fix.** No double was found. The should-fix is a timing gap in the fills retry.
- **Gates (2c80be430 merged with main b0fa95235, code-identical to main 69446b2a2):**
  - ruff check, ruff format --check, check_imports and check_records: clean.
  - pytest -n auto: 15,149 passed, 1 failed. The failure is `test_a_live_holder_keeps_its_lock_after_its_lease_expires`,
    a lock-lease timing test, run while 3 other suites shared 4 CPUs. Alone it passed 3 of 3. The delta touches no
    file under fno/books.

### Criteria
| Item | Result | Evidence |
|---|---|---|
| Retry of a failed fills, exits or marks step, and only those | MET | `done()` and `record()` (run_log.py:41-52); `RETRY: true` survives the public log. I ran `PublicResult` myself: `{'status': 'failed', 'reason': 'raised:TimeoutError', 'retry': True}`. Plants J2, J3, J4, J13 and J14 caught. |
| Nothing doubled | MET | Probe: a write cut between legs, then a retry: 4 fills, opening plus 4 ledger rows, one `opened` event. A ledger fill without its desk row gets stuck (IndexError on every retry), but nothing doubles. A failed account commit stays `CommitFailed` and stops the run (J5 caught). |
| A final step never reruns | MET | A refused step, a command step (no key) and `retry: false` all count as `done`. J3 and J13 caught. |
| Same snapshot on a retry | MET | Only the snapshot step writes capture records (`records_folder` grep), and it is never retried. The gate's window uses the capture's own times (snapshot_checks.py:30). |
| Same-day guard, health line, input problem refuses the fills | MET | J1, J8, J7 and J12 caught. |
| My minor 1 (NEEDS pin) and minor 2 (written count) | MET | J10 and J11 caught. |

### Findings
1. **Should fix: a retried fills step can open new risk hours after the fills window.**
   - The fills plan's moment is `execution_snapshot`, so `waiter.until` on a past time returns at once.
   - Nothing compares the clock with `fills_by` (15:20). `check_point_in_time` refuses only a snapshot that
     finished after now.
   - Probe: fills failed in run 1; a rerun at 21:00 opened t1 at the 15:15 snapshot (`exec_20261014_151500`).
   - In practice every same-day rerun comes after the close. The day lock makes a second run in the same container
     do nothing, and the first run lasts until A4h's 16:00 recheck.
   - So whether a paper entry exists is decided by a person who has seen the move after 15:15. That is a
     hindsight option in the record that decides whether real money is used.
   - The design says "fills and exits finish by `fills_by`" (config.yaml:159).
   - Fix expected: retry the fills only while the clock is within the fills window. After it, the fills stay
     failed with that reason in the alert. Or the owner rules, in their own words, that late fills are accepted, and
     each such fill is flagged.
   - Exits and marks can stay retryable. They are risk-reducing or replace the day's own rows.

### Minor (not blocking)
- **J6 survives:** `written = len(result)` passes every test. A blocked or "not filled" entry would then be
  counted in the alert. Add one case with a blocked book.

### The builder's four open points
1. **Per-book exit errors are never retried:** an acceptable stated limit. It fails closed: `_unreviewed` blocks that
   book the next session, and its due exits wait one day. Also, the per-book `except Exception` in `review_exits`
   catches `CommitFailed` too. That predates this delta. Note only.
2. **Marks and the card are not rerun after a retried fill:** acceptable. Today's equity row is consistent as of
   before the trade. The list should also name the exits: a trade opened in a retry gets no exit review that day.
3. **The selection risk of a manual rerun:** this is finding 1 above, not a stated limit. The same risk already
   exists for a fills rerun after `RunStopped` (decision 47, before this delta). The same bound should cover it.
4. **The shared-scratchpad restore:** no effect on the SHA judged. I judged clean detached worktrees of the pushed
   commits, read the whole fno/ delta (no leftover plant) and ran my own plants. Each was restored with
   `git checkout --` and `git status` came back clean.

### Plants: 14 planted, 13 caught, 1 survived (J6, minor). 3 probes run (mid-trade cut, cut inside record_fill, 21:00 rerun).

### T1d merge order
- The trial merge used T1d at 5cbd3c4c7, which already contains 2c80be430, with main merged in.
- tests/daily, timetable, desk, scoreboard and cards: 633 passed.
- At 2c80be430 alone, `fno/cards/rule_checks.py:97` still reads a failed decisions result as books.
- So my condition stands: merge R2 only together with T1d, after T1d's own PASS.

## Addendum 3 (owner's ruling 1A, own session)

- **Head:** ee5711075 (story/o1-r1r2-step-safety-b). Delta judged: `git diff 2c80be430 ee5711075`, the builder's
  commits 067709db0, 5ca1fd0bc, 7fd93779b, d1b29a968. Judge E (session_01Nm6h3E5jXfk77b3AUWU3xE), lane 1, money.
- **Verdict: PASS. The change implements the owner's ruling 1A and closes finding 1.** Merge condition below (T1d).
- **Gates (ee5711075 merged with main b61907a2a):** ruff check, ruff format --check, check_imports, check_records,
  check_numbers: clean. pytest -n auto: 15,233 passed, 1 skipped, 15 xfailed, 0 failed.

### Criteria
| Item | Result | Evidence |
|---|---|---|
| A failed fills step is final, no rerun opens a trade | MET | `RETRIED_ON_RERUN = ("exits", trade_marks)` (daily_run.py:84); logged `retry: false`, so `done`. Plants P1, P12 caught |
| A rerun after a stop (decision 47) starts no fills after fills_by | MET | `_too_late` (daily_run.py:255); 15:20:00 fills, +1 s, +60 s and 23:50 refused, logged `refused` for the day. Plants P2 (`<`), P5, P7 caught |
| The run that took the snapshot is not cut off by its own slow commit | MET | `ran_here` exemption; P3 caught by the 15:22 slow-commit test. Bounded: a run's own snapshot is valid only when its capture started 15:15 and finished by 15:20 (`SnapshotInWindow`, snapshot_checks.py:30, `prices_unverified`), and a late capture is a new one taken now (recorder.py:185). So a 21:00 rerun that takes its own snapshot gets `valid: false`, never a fill |
| Nothing doubled | MET | The 15:20:00 rerun test: book 2's written fills unchanged, book 3 filled once |
| Exits and trade_marks still retried | MET | Unchanged list; `test_a_failed_marking_is_retried_once...` and the exits tests pass |
| Last line "; a rerun today retries it: <steps>", own day only, never for fills | MET | runner.py:63-70, `retried_steps`; P8, P9, P10, P14 caught |
| CLAUDE.md step 2b | MET | Once more, at once, once only; fills never retried; the 14:05 time unchanged (CLAUDE.md step text and stored-prompt line untouched) |
| My minor J6 pinned | MET | `test_the_written_count_leaves_out_a_blocked_book`; P11 (`written = len(result)`) caught |

### Merge condition (blocking for the joint merge, not a ruling defect)
- **T1d trial merge (5cbd3c4c7 + ee5711075 + main):** tests/daily, timetable, desk, scoreboard, cards: 645 passed,
  **1 failed**: `tests/cards/test_problem_steps.py::test_the_runner_s_last_line_and_the_card_name_the_same_steps_for_one_log`,
  `AttributeError: 'types.SimpleNamespace' object has no attribute 'on_its_day'`.
- Cause: `DayRunner` now calls `daily_run.on_its_day(day)` on a run with problems; T1d's fake DailyRun lacks it. The
  real `DailyRun` has it, so production is unaffected, but merging both as they are turns main red.
- Fix expected: give that fake `on_its_day=lambda day: True` (T1d's branch or the merge commit), then re-run those
  five suites. My earlier condition stands: merge R2 only together with T1d.

### Plants: 14 planted, 13 caught, 1 survived (equivalent)
- P13 (`ran_here.add` after the commit) survives. Equivalent in production: a failed commit raises `RunStopped`, the
  process ends, and the rerun starts with an empty `ran_here` either way. Each plant restored with `git checkout --`;
  `git status` clean.

### Notes (not findings)
- A stop inside the fills followed by a rerun by 15:20:00 still fills the books not yet filled. That is the bound the
  orchestrator set and the builder states: at most about 5 minutes of prices seen after the 15:15 snapshot.
- The late refusal's alert is sent before its commit; a failed commit there re-sends it on the next rerun (stated).
