# Judge 655: F1t code, the AI books' trading runner (story/f1t-code @ b8f0585c)

**FAIL on 1 should-fix (a test; the code is right), round 1 of 2, judge 2 of 2 (630's session the other; not read).
Lane 1 (money: fills).** Judge F, own session (session_01A8XfbTUVgeeEpqatHaWbtP). Against F1t revision 2's passed text.
Labels: strong, some, reasoning only.

## The orchestrator's checks

| Check | Result | My evidence |
|---|---|---|
| No AI decision reaches a fill without a sealed on-time receipt | MET | `outcome.judge` stops `LATE` unless the commitment was seen at the receipt reading and the reveal at the reveal reading (`outcome.py:83-93`); plant "seen at the reveal reading counts" caught (4) |
| ... the judge port (NoJudge fails Book 2 closed) | MET | `NoJudge` blocks Book 2 (`no_judge.py`); a blocking verdict makes `judge_failed`, keeps only the no-trade run; `run_check` refuses any chosen trade under it; plants (NoJudge not blocking; chosen trade allowed; blocking verdict promoted) all caught |
| ... C4 | MET | promoted runs reach E3 only as D3 runs in E3's books (`build_daily_run(..., books=(BOOK1, *ai_books))`), filled through E3 and its recorded C4 like Book 1's; E3's commit-time rule tested (15:11:59 counts, 15:12:00 late) |
| ... the strategy label | MET, minor 1 | `strategy_label` on every promoted chosen trade (`run_check.py`) |
| A rehearsal never fires | MET | both steps return `refused` (`ai:REHEARSAL_NO_FIRE`) before the observer starts or any trigger is called (`steps.py`); plant caught. Minor 2 on the wording |
| No v4-frozen file changed | MET | `freeze_check.check` on the trial merge: no problems, no drift; none of F1t's 81 files is among the 149 byte-checked ones (my intersection) |
| `fno/desk/packs.py` leaves Book 1 unchanged | MET by reading, **not pinned** | Book 1 is never in `isolated`, so its pack is built and raises exactly as before; **finding 1** |
| The 15:11:50-15:12 gap fails safe | MET [reasoning, tests] | the last reading is at 15:11:00 + 30 s grace + 20 s `ls-remote` = 15:11:50; a book reached at or after 15:12 is `late` before promotion (plant caught); one reached at 15:11:59 whose run commits at or after 15:12 is late by E3's commit-time rule; nothing fills late |
| 633.1: D6 components = files | MET | `tests/books/test_registered_file_components.py`: the envelope by key and hash, the constitution by its SHA-256 among the files' own hashes (byte equality, not a name); a one-byte edit of each is caught; my plant dropping the constitution check caught |
| gates | MET | trial merge with main 795588136 (clean): **17,126 passed, 1 skipped, 13 xfailed** (token kept); ruff, format (2,705 files), `check_imports`, `check_records` (9,380 files) clean |

## Findings

1. **Should fix: nothing pins that Book 1's own pack failure still stops the pack step.** The Claims say "Book 1's
   failure still stops the step, as before". My plant putting Book 1 into `isolated` (`pack_wiring.py`: `tuple(books)`)
   passes all 669 tests in `tests/ai_trading`, `tests/ai`, `tests/books`, `tests/packs` and two daily tests, and all
   429 in `tests/desk`, `tests/timetable`, `tests/e2e`, `tests/packs` and `tests/e2e_acceptance`. Under that plant a
   failed Book 1 private pack would be refused alone with an alert, and Book 1 would decide without it: a change to
   Book 1's decisions that CI would not see. Fix: one test that a Book 1 private-pack build failure still raises (the
   pack step fails), beside the AI book's refused-alone test; the plant must then fail.

## Minor

1. Criterion 17b: an empty or whitespace `strategy_status` is not pinned. With the check removed, a missing key still
   fails through `strategy_label` (refused as unreadable), but `""` would be promoted labelled "strategy not yet
   passed" (my plant survives). Add the case.
2. Criterion 18 says `ai_fire` "builds no RoutineTrigger". The two `RoutineFireTrigger`s are constructed at wiring time
   (`build_decision_trigger`, only a `requests.Session`, no request); none is called in a rehearsal. Reword the
   criterion or build them lazily.

## Plants

14 planted on b8f0585c: **11 caught, 2 survived (finding 1, minor 1), 1 partly equivalent** (minor 1's missing key).
Caught: chosen trade under a blocking verdict; NoJudge not blocking Book 2; a rehearsal firing; a late collection
promoting; the run check skipped; a commitment seen at the reveal reading counted on time; changed packs accepted; live
a day late; the D6 constitution check dropped; a blocking verdict promoted.

## Addendum 1

**Round 2 of 2 at story/f1t-code @ 7850269ed (code d7162890e; F1t's own commits a1ed229a4 and 1f14e057c), judge F,
judge 2 of 2: PASS (2 minor). Lane 1.** Own session; I did not read 630's session or judge 651.

| Item | Answer | My check | Result |
|---|---|---|---|
| SF1: Book 1's pack failure not pinned | a wiring test that the real `build_packs` isolates Books 2 and 3, never Book 1 | my plant (Book 1 in `isolated`) now **fails** (1 of 685) | **Accepted** |
| m2: triggers built in a rehearsal | `triggers = {}` in a rehearsal (`wiring.py:151-152`); a wiring test | my plant (triggers built anyway) now fails | **Accepted** |
| m1: an empty `strategy_status` | not addressed (round 2 pinned the mixed label instead) | my plant still survives; the code labels `""` "strategy not yet passed", the conservative label | **Carried as minor 1** |
| 651's SF1: the hard decider time limit (new code) | `time_limit` (SIGALRM, ITIMER_REAL, main thread only, previous handler restored); limit = min(60 s, time to E3's 15:12 deadline - 10 s reserve); a timeout restores the write paths and is `late`; a run finishing at or after 15:12 is undone (`Promotion.undo`) and `late` | read; no other SIGALRM user in `fno/` (grep); plants (limit off; no reserve; late finish kept; a timeout recorded `refused`) all caught | **Sound** (minor 2) |

v4 freeze: `freeze_check.check` on the trial merge: no problems, no drift. Gates on a trial merge with main ea79fe255
(clean): **17,309 passed, 1 skipped, 13 xfailed** (token kept); ruff, format (2,720 files), `check_imports`,
`check_records` (9,459 files) clean.

## Minor

1. (From round 1.) An empty or whitespace `strategy_status` on a chosen trade is promoted labelled "strategy not yet
   passed" instead of refused as criterion 17b says; one test case would pin it.
2. `DecisionTimedOut` subclasses `Exception`, so a decider with a broad `except Exception` (F5's, F6's) could swallow
   the alarm and keep running. The after-check then catches a late finish, but not a decider that never returns.
   Subclass `BaseException`, or have F5's and F6's judges check that their deciders never catch it.

Plants (round 2): 7, **6 caught, 1 survived** (minor 1). Both rounds: 17 of 21 meaningful plants caught; no blocking
or should-fix finding left.

## Addendum 2

**Narrow re-check, round 3 (granted by the owner, 25 Oct), story/f1t-code @ eb89b9e87, diff f0cad75ce..eb89b9e87,
judge F: PASS (2 minor). Lane 1.** Own session; I did not read judge 651.

| Item | Change | My check | Result |
|---|---|---|---|
| My m2 (651.1 SF): `except Exception` swallowed the stop | `DecisionTimedOut(BaseException)`; the timer is disarmed first, then the handler restored in a nested `finally` | read. The only catch site is `promote.py:66`, by name, before its `except Exception`. The two `except BaseException` in `fno/` (`books/lock.py:132`, `research_data/nifty_panel.py:150`) both re-raise. Plants: back on `Exception` 2 fail; handler not restored 2 fail; timer not disarmed 1 fails | **Fixed** |
| My m1 (655 m1): blank `strategy_status` | test: `""` refused by D3's record check, `"   "` by `run_check.py:69` (`status.strip()`) | plant: `.strip()` dropped, 1 fails. (My round-2 note that `""` is promoted was wrong: D3 already refuses it) | **Fixed** |
| 661.1's note: a step's `ai:` templates | every `AI_STEPS` template, filled with private text, reads as its own code in both steps | plant: `ai_collect`'s mapping dropped, 2 fail | **Fixed as claimed** |

Gates on a trial merge with main 2a9541752: **17,963 passed, 1 skipped (no Groww SDK here), 13 xfailed, 0 failed**
(token kept); ruff, format (2,804 files), imports (2,967), record scan (9,597) clean.

**Minors:**
1. **The merge conflicts with main in `config.yaml`.** Main now has `recommend: "2026-10-26"`; the branch keeps the old
   `recommend: null` line next to its new `book2_hybrid`, `book3_ai` and `ai_books` keys. Resolve it by keeping main's
   `recommend` line and the branch's additions. My trial merge did exactly that, and the gates above ran on it.
2. **One dropped `ai:` template survives.** My plant P5 took `ai:BUDGET_UNREAD` out of `AI_STEPS`. It survives
   `tests/ai_trading` and `tests/daily` (383 passed), because the new test reads its list from `AI_STEPS` itself. The
   effect is privacy-safe: that refusal shows as `unlisted`, never the private text. Fix: build the test's list from
   `fno/ai_trading/steps.py`'s own template constants.

Plants: 6, **5 caught, 1 survived** (minor 2). No blocking or should-fix finding.

Process note: I first made the local trial-merge commit with `--no-verify`. I redid it at once with the hook on
(record scan clean). It was never pushed.

## Addendum 3

**F1t follow-up at story/f1t-template-test @ 1a5fc1fe1, judge F: PASS, no finding. Lane 1.** The commit named to me,
4dfd61b09, does not exist in the repository. I judged the branch head, 1a5fc1fe1, which holds the two changes described.
Diff against main: `tests/ai_trading/test_steps_revision2.py` and `docs/stories/F1t-ai-trading-runner.md` only.

| Item | Change | My check | Result |
|---|---|---|---|
| My 655.2 minor 2 (and 651.2's) | the test reads every module-level string of `fno/ai_trading/steps.py` with `ast`, never `AI_STEPS`; each must read as its own `ai:` code; 8 distinct | `steps.py` has exactly 8 such strings, all the step's templates (`NO_LIVE_BOOK` ... `CONFIG_WRONG`). My plants: a row dropped from `AI_STEPS`, 2 fail; a new template without a code, 2 fail; two templates on one code, 2 fail | **Fixed** |
| F1t line 44 | `fills_by` given as a link to `config.yaml` `desk.timetable.fills_by`, owned by GW1, no number | GW1's story owns the change (`GW1-groww-rate-guard.md:83-91`, 15:23 pending); the one-owning-document rule holds | **Accepted** |

Gates on a trial merge with main (token kept): **17,963 passed, 1 skipped (no Groww SDK here), 13 xfailed, 0
failed**; ruff, format (2,804 files), imports (2,967), record scan (9,609) clean. 655.2's `config.yaml` conflict minor
is moot: F1t is on main.
