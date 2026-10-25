# Judge 204: O2 failure handling, end to end (story text at a06799a6)

**Verdict: FAIL, 3 should-fix.** The suite is the right idea: one end-to-end run with fakes only at the edges, no new
behaviour, and LM1's heartbeat left to LM1. But three of the expected outcomes contradict the code they say they
follow, and criterion 7 ("none hidden by a test that expects the wrong outcome") forbids writing a test to the wrong
outcome. The code was read on origin/main after E2c and E4c, and on O1's branch at f01bf9d7.

## Criteria

| # | Criterion | Result | Why |
|---|---|---|---|
| 1 | Each family's outcome is the owner code's rule | NOT MET | should-fix 1 and 3 |
| 2 | Exits run or are held with an alert | MET as text | `review_exits` runs for every book; with no pack the gate leaves exits `waiting` with its alert |
| 3 | No alert is lost | MET as text | see note B for a gap the suite will find |
| 4 | A rerun repeats nothing | NOT MET | should-fix 3 |
| 5 | Books are isolated | NOT MET | should-fix 2 |
| 6 | Fakes only at the edges | PARTLY | in conflict with 5 (should-fix 2) |
| 7, 8 | Real failure, real fix; engineering | MET as text | |

## Should-fix

1. **Drive outage (b): the row contradicts E2c's rule.**
   - **The text says:** a Drive failure at an account write during fills makes "that write's entries fail closed with
     an alert, while other books and every exit go on".
   - **The code says otherwise:** `DriveAccountSync` (`fno/desk/drive_sync.py` docstring) states that Drive failing
     (`PrivateFilesUnavailable`, a `CommitFailed`) "stops the write: E3's one handler alerts and stops the run". So
     `_guarded` raises `RunStopped` at `fills`: the stop alert carries "exits not reviewed today", no exits run, and
     the next session blocks new entries for every book (`BEFORE_EXITS`). The fail-closed path in `fill` is only for
     `AccountWriteRefused` (the account lock) and `OrdersRefused`.
   - **Fix:** write row (b) as E2c's real rule. If the owner wants exits to still run after a Drive write fails, that
     is a change to E2c, judged there, not O2.
2. **One book's failure: there is no second book in the real run.**
   - `build_daily_run` defaults to `books=(BOOK1_RULES,)`, and O1's `build_day_runner` passes no other book. Book 2
     (`BOOK2_HYBRID`) has no orders or exit rules in the daily run until F5/F6.
   - Criterion 6 builds the run through `fno/daily/wiring.py` and fails if anything but an outside service is
     replaced, so the suite cannot get a Book 2 without breaking criterion 6.
   - **Fix, pick one and say it:**
     - (a) a named test-only second book, injected through `build_daily_run`'s `books`, orders and exit rules,
       written down as the one allowed exception to criterion 6;
     - (b) move the family to Known limits until F5/F6, keeping E3's existing per-book isolation tests (judge 84) as
       the evidence for now.
3. **Kill and rerun: "byte-identical for every step" is false while the quote parts run.**
   - A kill after any step from `quotes` to `exits` (steps 1-11 of the 13) kills the quote parts with the run. On the
     rerun, `quotes` is recorded, so no part restarts. `quotes_done` records `failed` with `NOT_IN_THIS_RUN`, and the
     parts' files stay uncommitted.
   - That is O1's judged rule (judge 178 addendum 2, note 4 declined; O1's Known limits), so the final run log
     differs from an uninterrupted day.
   - **Fix:** criterion 4 and the row name that outcome for those kills: `quotes_done` failed with its reason, the
     part files not committed, the hand fix in the claims. Keep byte-identity for everything else: the desk's
     records, the private records and the run log apart from `quotes_done`.
   - Also add a kill between a step's record and its commit (`PendingCommitter`'s case), the case E2b built the
     pending file for.

## Notes (not should-fix)

- **A. Drive outage (a).** "No step runs" is right, and it also means the 3 pm quote parts never start, so the
  NIFTY and NSE recordings are lost that day. NSE does not need Drive. Write it in the row so the owner sees it.
  Whether `quotes` should start before the download is O1's design question (raised with O1, not O2's to change).
- **B. A gap the suite will find (criterion 3).** E4c's refusal path in `fill` prints the send outcome itself
  (`print(outcome)` when it is not `SENT`). Under O1's `ReportedAlerts` the same unsent alert is then printed twice
  ("outcome | text", then "outcome"). By criterion 7 that goes to its owner (E4c or O1), not into a test that
  expects two lines.
- **C.** The routine-never-starts chain exists as described: O8's "never ran: no run log", and `NO_LOG` blocks every
  book on D+1. The text should note that `NO_LOG` reads "stopped before any step", which also covers a run that never
  began.
- **D.** "13 steps today" is right for O1 at f01bf9d7. E8's and M2's steps will add two, so read the count from
  `DAILY_RUN_STEPS` rather than typing it.

Coordination: no other row in `docs/WORK_REGISTER.md` covers an end-to-end failure suite, and LM1, E4c and the
first-line story are kept apart as stated. No duplicate.

## Addendum 1: revision 3 at 3050495d

**Verdict: PASS.** All three should-fixes and all four notes are applied, and each matches the code.

- **Should-fix 1.** Row (b) now gives E2c's rule: `PrivateFilesUnavailable` is a `CommitFailed`, so the run stops at
  `fills` and no exits run that day, the stop alert names "exits not reviewed today", and `BEFORE_EXITS` applies the
  next session. Only `AccountWriteRefused` and `OrdersRefused` fail one book closed. Any change to this belongs to
  E2c.
- **Should-fix 2.** One named test-only book, `book_test`, comes in through `build_daily_run`'s existing `books`
  parameter. It is written down as the single exception to criterion 6, and the row now names the real exceptions
  (`OrdersRefused`, `AccountWriteRefused`, an exit review that raises).
- **Should-fix 3.** For kills from `quotes` to `exits`, the expected outcome is now named: `quotes_done`
  `NOT_IN_THIS_RUN`, with the part files uncommitted. Every other kill must leave the records byte-identical. A kill
  between a step's record and its commit is added, and the step count is read from the tuple.
- **Notes A-D.** All in: the download failure loses that day's quote parts, NSE included; the double print is a Known
  limit, routed to E4c's owner; `NO_LOG`'s wording also covers a run that never began; the step count is read from the
  tuple.
- **One-line note:** criterion 5 still says "each Book 2 failure". Write `book_test` so it matches criterion 6 and the
  family row.

## Addendum 2: O2 story text revision 4 (story/o2-failure-handling at 6fd9cc9f)

**Verdict: FAIL, 1 should-fix.** The rest of revision 4 is correct and checked against main's code.

| Claim | Result | Evidence |
|---|---|---|
| `Git.__call__` has no time limit; only `unshallow` has one (120 s) | MET | `fno/desk/git_sync.py`: `self.run(["git", *args], ...)` has no `timeout`; `UNSHALLOW_TIMEOUT_SECONDS = 120.0` |
| A GitError becomes `CommitFailed` | MET in principle | `GitError` subclasses `AccountWriteRefused`, and `GitCommitter` wraps it (E3) |
| Row (a): the quote parts start before the download and are waited for after a stop | MET | `fno/daily/runner.py` `run`: `self.parts.start(day)` comes first; `_finish_parts` runs on a stop |
| Hung command: 600 s, with the whole process group | MET | `fno/daily/steps.py` `COMMAND_LIMIT_SECONDS = 600.0`; `fno/daily/processes.py` uses `os.killpg(..., SIGKILL)` and `start_new_session=True` |
| Note B closed | MET | `fno/desk/daily_steps.py` 189-192: one `alerts.send`, no own print |
| Criterion 5 now names `book_test` | MET | diff |
| The one behaviour exception is named in Out | MET | diff |

### Should-fix 1: a timed-out git call can leave `.git/index.lock`, so "the desk goes on" is false
The new row says that after a quote part's hung commit the part gets O1's "NOT committed" alert "while the desk goes
on", and that a hung desk commit gives E3's stop alert. The text does not say *how* the call is stopped. The obvious
build, `subprocess.run(..., timeout=120)` as `unshallow` does, kills only `git` with SIGKILL.

I tested this on git 2.43, the version in this container. The test used the run's own form, `git commit -q -m m -- a`,
with a pre-commit hook that hangs, and a SIGKILL after 1.5 s:
- while the hook runs, git holds `index.lock` and `next-index-<pid>.lock`;
- after the kill, **both locks stay**, and the next `git add` fails with
  `fatal: Unable to create '.../.git/index.lock': File exists`;
- the hook process (in the real run, `tools/check_records.py --alert`, which can post to Slack) is not killed and goes
  on running.

The path from normal running is a commit or a `pull --no-rebase` merge step stopped at the limit: both run while git
holds `index.lock`, and the commit runs the O5 hook, so a hook stuck past 120 s (scanning, or its Slack post) is exactly
such a hang. After it:
- every later git call of the day fails: each other quote part, the next desk step's commit, the run log;
- so a hung quote-part commit before `exits` becomes E3's stop at the next desk commit ("exits not reviewed today"),
  not "the desk goes on";
- and the next day's routine fails on its first commit until someone deletes the lock by hand.

The row would then be untrue, and a test that fakes the hang at `run` (rather than through a real git and hook) would
not show it.

**What the text needs** (the builder chooses the design; these are the requirements):
1. Say how the call is stopped: its whole process group, as O1's `processes.py` already does for child commands, so the
   hook dies with it.
2. Say what happens to a lock that call leaves. Either the run removes the lock its own stopped call left (the routine's
   checkout has one git writer, the run's one thread), or every later git call fails at once with one alert naming
   the stale lock and the hand fix. Today the text says nothing about the lock.
3. Add a test row that runs a real git with a hanging hook (the fake stays at the edge: the hook or the remote), stops
   it at the limit, then checks the next commit of the day: the next quote part and the next desk step. Then check the
   next day's first commit, so that what happens matches what the row says.

### Notes (not should-fix)
- A push stopped at the limit may already be accepted by the remote. The alert then says "NOT committed" for a commit
  that reached main. The hand fix is harmless (nothing left to commit), but the alert wording could say "not confirmed".
- 120 s for every call is reasoning only, as the text says. Today's pulls and pushes take seconds, so I accept it.

## Addendum 3: O2 story text revision 5 (story/o2-failure-handling at 449bdc93)

**Verdict: PASS.** Should-fix 1 of addendum 2 is closed. 8726f741, the O10 boundary line (O10 covers only jobs outside
`daily run` and sends no alert for a run step), is also fine: it means one alert per failure.

| Point | Result | Evidence |
|---|---|---|
| Process-group kill of a stopped git call (the hook too), then wait | MET | "Hung git call" row, the same as `fno/daily/processes.py` (`start_new_session`, `killpg`) |
| Lock handling | MET | only locks absent before the call are removed; a pre-existing lock fails the call at once with the lock path and the hand fix |
| Real-git test | MET | a hanging hook, in a desk commit, a quote-part commit and a push; checks the hook is gone, no lock is left, and the next quote part, the next desk commit and the next day's first commit all succeed |
| Push note | MET | "push not confirmed", marked unpushed, recovered by E3's rerun |
| The same hole in O1's 600 s command kill, found by the builder | MET | `desk book1` commits its own decision; the row now uses the same lock rule plus a kill-mid-commit test. A good find, beyond what I asked |

**The rule's premise holds on main today, and I checked it.** It is "one git call at a time, and no child runs git
while one is open":
- `CommandStep.run` waits with a plain `clock_time.sleep` (`fno/daily/steps.py`), so the run makes no git call of its
  own while a child step runs;
- `fno/quotes/cli.py` (the quote parts' child command) runs no git;
- O9's `build_receipt_committer` / `build_data_store` have no caller on main yet.

### Notes (not should-fix)
1. **The premise is a future dependency.** O9's later steps put a receipt commit in every writer. If one of the quote
   parts' child commands (they run alongside the desk's git calls) ever commits receipts itself, two problems follow:
   - a lock that child creates during one of the run's calls would be removed as "this call's";
   - and git's own lock would make the run's call fail.

   O9's writers inside `daily run` should commit through the run's one committer, or the O2 code should fail a test
   when a child step runs git. I am sending this to the orchestrator for O9's builder.
2. "A routine starts in a fresh container" is from the `fno/desk/daily_run.py` docstring (some evidence). The same-
   checkout test covers the case anyway.

## Addendum 4: the builder's question on criterion 6's `book_test` exception (asked at efd78e12)
**Ruling: I agree with the direction. It needs a short text amendment, revision 6, before the trade rows are built.**
The rows that need no trade may go ahead now.

**Why the direction is better.** Fixture data in the test checkout (a paper-status fixture strategy, a Book 1 version
registered by D6's own code, a fixture market that fires) replaces no code at all. That is closer to criterion 6 than
`book_test` was. I checked the builder's facts:
- D3 accepts only the three real books;
- shadow accounts are real accounts in the private-files path (`fno/desk/private_files.py` lists `journal/shadow/*`,
  `fno/books/paths.py` `shadow_account`).

Widening D3 for a test would be a production change, and I agree it should be rejected.

**Revision 6 must state:**
1. **Criteria 5 and 6 and the "One book's failure" row are rewritten.** The second account is Book 1's shadow, and
   `book_test` is gone. For each of the three injected failures, name how it is caused through an outside seam or
   fixture data only:
   - **account write refused:** the Drive fake refuses the shadow's paths;
   - **exit review raising:** for example a corrupt shadow account file served by the Drive fake;
   - **orders refused:** `OrdersRefused` is raised today by Book 1's order builder (`fno/books/book1_orders.py`). If it
     cannot be produced for the shadow without replacing code, say so and name what replaces that case. Do not drop it
     silently.
2. **The fixture never reaches the real repository's playbook, registry or ledger.** It lives in the fresh checkout
   only, with a test that the source tree's playbook and registry files are byte-unchanged after the suite.
3. **Isolation is checked in both directions:** Book 1 is unchanged by each shadow failure, and the shadow is unchanged
   by a Book 1 failure. The second is the realistic risk while Book 1 is the only trading book.
4. **The known limit is named.** As of 16 Oct, production has no registered Book 1 version, so nothing trades. The
   trade rows test a path that is not live yet (strong evidence, the builder's run log). When Book 2 (F5/F6) trades,
   its isolation case is added.

The two root fixes the suite found (Book 1's orders and the capture's quote folder ignoring `root`) are production code
changes. They are lane 1 and are judged with O2's code, each with its own test.

## Addendum 5: O2 story text revision 6 (story/o2-failure-handling at 716e0bf6)
**Verdict: PASS.** Addendum 4's four points are met. I checked each code claim on main.

| Point | Result | Evidence |
|---|---|---|
| Each failure through fixture data or an outside seam only | MET | (a) the shadow's account file served corrupt by the Drive fake at `trade_marks`; (b) Book 1's `OrdersRefused` from a fixture record whose replay differs; (c) a corrupt shadow file read during `desk book1`. A shadow-only orders refusal is stated as not producible: `ReplayedOrders` takes only `Decision.CHOSEN` (`fno/playbook/outcomes.py` 71-72), and `fill` and `review_exits` loop over `self.books` only (`fno/desk/daily_steps.py` 152, 200). It waits for E8 1b |
| The fixture never reaches the source tree | MET | criterion 6: a test that `playbook/`, `playbook/registry.csv` and `journal/versions.csv` are byte-unchanged |
| Isolation both ways | MET | criterion 5 rewritten |
| Not-live limit named | MET | corrected to the true reason: no strategy has status `paper` (`b0-monthly-sc` v1 is `research`, dated 16 Oct) |
| `AccountWriteRefused` per account | MET | through the real wiring a Drive failure is E2c's `CommitFailed` (a whole-run stop), so Drive (b) tests that, as the text says |

**Case (c) is a real gap, not a test artefact.** In `fno/playbook/evaluate.py` 52-59, the shadow loop sits inside
Book 1's evaluation with no guard, so one shadow's failure aborts Book 1's whole decision. Production now has a
registered research shadow (`b0-monthly-sc` v1). It costs nothing today, because Book 1 has no `paper` strategy. Once
one is approved, a bad shadow file stops Book 1 from trading that day.

**Conditions for the code:**
- The xfail must be `strict=True` with the gap named, so it fails the moment D2's fix lands and is then turned into the
  real assertion. A non-strict xfail would hide it.
- D2's fix needs a WORK_REGISTER row with its owner. I ask the orchestrator to schedule it before the first `paper`
  approval.

Criterion 8 (two minutes on four cores, from a measured 6-7 s per fixture day) is accepted as some evidence.
