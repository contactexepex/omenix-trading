# Judge 651: F1t code, the AI books' trading runner, round 1 (judge 1 of 2)

Branch `story/f1t-code` at `cab730a85` (draft PR #157); text: `docs/stories/F1t-ai-trading-runner.md` revision 2.
**FAIL**, lane 1 (it decides paper trades): 2 should-fix, 3 minor. Trial merge with main `d04d46705`, no conflict.

## Criteria (the orchestrator's six points and the criteria behind them)

| Item | Verdict | Evidence |
|---|---|---|
| (1) sealed, on-time receipt | MET | `outcome.py` `judge`: commitment seen at the receipt deadline, no other book's early reveal, own reveal not early and seen at the reveal deadline, then seal, shape and model checks; plants (any receipt, exposed, early or late reveal, unverified model, instructions source, `not_fired` entry) all caught |
| (1) judge port, NoJudge fails Book 2 closed | MET | `no_judge.py:29` blocks Book 2 only; `collect.py:136` gives `judge_failed`; `run_check.py:226` refuses a chosen trade under a block; 3 plants caught |
| (1) C4 and fills only through E3 | MET | `book_dispatch.py`: per-book orders and exits, none wired means refused; e2e `test_a_c4_failure_is_promoted_as_a_record_but_never_filled` |
| (1) strategy label | PARTLY | rule right (`run_check.py:203-208`); the mixed case is untested (minor 3) |
| (2) a rehearsal never fires | PARTLY | both steps return `refused` before the observer or any trigger (`steps.py:114,147`); the wiring's guard is untested and triggers are still built (should-fix 2) |
| (3) no v4-frozen file changed | MET | `freeze_check.check` on the trial merge: "v4 freeze: intact", no drift line; the changed files that FREEZE_v4.md names are "named, not hashed" (config.yaml, budget/report.py, config.py, constants_operations.py, daily/wiring.py); the config change adds only `book2_hybrid`, `book3_ai` (null) and `ai_books`, none of them a v4 setting |
| (4) `fno/desk/packs.py`, `remote_observer.py` | MET for the code | an AI book's build failure is refused alone with the type only (`packs.py:58-63`), after Book 1's pack; its missing pack then gives `not_fired` (`fire.py:81-83`); the observer only runs `git ls-remote` with a 20 s bound and writes failed readings; Book 1 left unchanged is not tested (minor 4) |
| (5) the 10 s gap | PARTLY | an AI run committed after 15:12 is late by E3's committer-time rule (`committed_decisions.py:46`); but a slow collection makes Book 1 late too (should-fix 1) |
| (6) D6 components equal their files | NOT MET | no test; minor 5 |
| Gates | MET | trial merge, token kept: 16,950 passed, 13 xfailed, 0 failed; ruff, format, `check_imports`, `check_records` clean |

## Findings

1. **Should-fix: nothing bounds `ai_collect`, so a slow AI book costs Book 1 its day.** `late_at` (`collect.py:99`)
   only refuses a book *reached* at or after 15:12. A promotion started at 15:11:5x (the last reading may come at
   15:11:50) runs as long as the decider, the run check and the git snapshots take. E3's `decisions` step runs after
   it and fails **every** book closed when it starts more than 30 s late (`daily_steps.py:96-99`). Reproduced on E3's
   real daily run with the branch's own e2e harness, the decider slowed by 95 s: `decisions` gives `book1_rules`
   "collected at 15:12:36, after the deadline 15:12:00: no decision can be shown to be on time". At 50 s Book 2 is
   still on time; at 60 s Book 2 alone is late, as designed. This breaks criterion 9 ("leaves ... Book 1's records
   byte-identical"). Fix: a hard end for the step, a known margin before 15:12. Start no promotion after a cutoff, and
   give the decider a time limit, so whatever is unfinished is `late`. Test: a slow decider while Book 1 has a
   committed run, and Book 1 is still collected on time.
2. **Should-fix: the only guard that stops a rehearsal firing a real routine is untested where it is wired.** Plant
   `rehearsing = lambda: False` in `wiring.py:160`: 1,121 related tests pass. The rehearsal test injects
   `lambda: True` into the steps directly. Criterion 18 asks that `ai_fire` "builds no `RoutineTrigger` ... (tests,
   the trigger factory a spy)", but `build_ai_steps` builds both `RoutineFireTrigger`s, with their tokens, inside a
   rehearsal too (`wiring.py:151`). Fix: build no trigger when `rehearsal()` is set, and add a wiring test with the
   real mode and a spy factory (no build, no call).
3. **Minor: the strategy label's mixed case is untested.** Plant `all` changed to `any` in `run_check.py:208`: 1,121
   passed. A run with a `research` and a `paper` trade would read "strategy passed". Expected: a two-trade test.
4. **Minor: "Book 1's failure still stops the step" is untested.** Plant: Book 1 added to the isolated books
   (`pack_wiring.py`): 1,121 passed. Expected: a Book 1 build failure test.
5. **Minor ((6), judge 633's minor): no test checks a D6 component against its file.** One byte appended to
   `book3/constitution-v1.yaml` on the trial merge: the full suite still passed (16,950). Expected: every active
   `journal/versions.csv` row's file components equal the files' SHA-256.

## Plants

26 planted, one at a time, restored each time. 21 caught. 5 survived: findings 2-5, and `strategy_status` check removed,
which is near-equivalent (a missing status is still refused, through `strategy_label`'s KeyError; only an empty
string would be promoted, labelled "strategy not yet passed").

## Notes

- A leftover `firing` entry is judged on its receipts, as the text says. Trigger errors keep only `FireFailed`'s own
  wording or an exception type, never the token.
- **Round 1's head moved (still round 1):** at `a1ed229a4` (judge F's D6 test plus a merge of main) the F1t code is
  byte-identical to `cab730a85`: findings 1-4 stand (rehearsal plant still survives, 667 passed). Minor 5 is closed:
  both components are checked by equality, and byte edits of either file or a disabled check are caught.

## Addendum 1: round 2 at `7850269ed` (code `1f14e057c`; the last round)

**FAIL**, lane 1, judge 1 of 2: 1 should-fix. Every round-1 finding is fixed, but the new time limit can be swallowed.

| Round-1 finding | Verdict | Evidence |
|---|---|---|
| SF1. `ai_collect` unbounded | FIXED, with should-fix A below | `time_limit.py`: a SIGALRM timer of min(60 s, time left before 15:12 less 10 s); a stopped decider's writes are put back and the book is `late`; a run finished at or after 15:12 is undone and `late`. The e2e test has Book 1 committed at 15:11:40 and Book 2 asleep; Book 1 is collected, Book 2 is late |
| SF2. Rehearsal guard | FIXED | no trigger is built under `rehearsal()` (`wiring.py:151-152`); plants "triggers built" and "steps not told" caught |
| m3. Mixed label | FIXED | plant `all` to `any` caught (2 failed) |
| m4. Book 1 isolated | FIXED | plant caught (1 failed) |
| m5. D6 hash | FIXED | at `a1ed229a4` (note above) |

The orchestrator's SIGALRM questions:
- Main thread: yes. `fno/daily`, `fno/desk` and `fno/rehearsal` start no thread around the steps (E8's daemon read
  thread aside), and nothing else in `fno` uses SIGALRM or `ITIMER_REAL`, so no outer timer can be cancelled.
- Leaks into later steps: no. The timer is cleared and the handler restored in `finally`; plants removing either
  are caught.
- Subprocesses: `subprocess.run` kills its child when the alarm interrupts it. My run, a 3 s `sleep` under a 0.5 s
  limit, was stopped at 0.5 s.

**Should-fix A: `DecisionTimedOut` is an `Exception`, so any `except Exception` in a decider swallows the alarm.**
The timer fires once. My run, a decider retrying slow work under `except Exception`, inside `time_limit(0.5)`: it
caught `DecisionTimedOut`, carried on, and returned "decided" after 2.5 s. A real decider does this.
`story/f6-on-f1t` `fno/book3/decider.py` uses `Book3Proposer`, whose `_guards` wraps parsing in `except Exception`
(`fno/book3/proposals.py:71`): an alarm there becomes a proposal refused as "unreadable: DecisionTimedOut", and
the decider goes on unbounded. Two outcomes follow:
1. A decider that then finishes inside the 10 s reserve is promoted with a decision the timer distorted.
2. One that runs on brings back round 1's failure: E3 starts late and every book, Book 1 included, loses the day.

Fix: derive `DecisionTimedOut` from `BaseException` (as `KeyboardInterrupt` is). Add a test with a decider that
catches `Exception` around slow work and is still stopped.

**Plants:** 11 on `7850269ed`, all caught (my 4 round-1 survivors among them).
**Gates:** trial merge with main `626b778bb`, token kept: 17,175 passed, 13 xfailed, 0 failed; ruff, format,
`check_imports`, `check_records` clean.
**Note:** an alarm landing between the block's end and `setitimer(0)` raises inside `finally` and leaves the previous
handler unrestored. Harmless today (no other SIGALRM user); restore the handler first if one is ever added.

## Addendum 2: round 3, the owner's narrow re-check (`f0cad75ce..eb89b9e87`)

**PASS**, lane 1, judge 1 of 2: should-fix A is closed; 1 minor. The diff touches only `fno/ai_trading/time_limit.py`,
its tests and F1t's Claims.

- **Should-fix A, closed.** `DecisionTimedOut` is now a `BaseException`. The promoter catches it by name inside its
  `try`, so it cannot reach the collector's `except Exception`. My round-2 probe, a decider retrying under
  `except Exception` with `time_limit(0.5)`, is now stopped at 0.5 s (round 2: 2.5 s).
  - Plant: back to `Exception` → caught (2 failed).
  - Plant: blank `strategy_status` allowed → caught.
  - The nested restore (`setitimer(0)` first, then the handler restore in its own `finally`) closes my round-2 note.
    A plant un-nesting it survives, as expected: the race cannot be reproduced on purpose in a test.
- **The reason-template test (661.1's note).** Dropping `ai_collect`'s templates is caught.
- **Minor.** Dropping a single row, `ai:OBSERVER_LOST`, survives (383 passed). The test loops over the registry's own
  `AI_STEPS`, so the row leaves the test too. The public log then shows "unlisted": no text leaks, but criterion 17
  asks that an unregistered reason fail a test. Expected: loop over `fno/ai_trading/steps.py`'s templates, not the
  registry.
- **Gates.** Trial merge with main `9914f68da`. `config.yaml` conflicted: main sets `recommend` to 2026-10-26 beside
  F1t's new keys. I resolved it locally by keeping both (never pushed); the branch must merge main the same way
  before it merges. On the resolved merge: 17,964 passed, 13 xfailed, 0 failed; ruff, `check_imports` and
  `check_records` clean. `recommend` is in `LIVE_STEPS`, so `live_ai_books` does not refuse it, and no AI book is
  live on 26 Oct. **Plants:** 6, of which 4 were caught. The 2 survivors are the minor's row and the race-only
  un-nesting.
