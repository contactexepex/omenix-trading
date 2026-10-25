# Judge 440: A4h, today's index close read after 15:30, story text (story/a4h-close-read @ c66b896d)

Judge F (independent), quality rule 1. The story is section "## A4h" of `docs/stories/A-data-foundation.md`, plus
one `docs/WORK_REGISTER.md` row. The builder sent 7b57ccf4, 24476d09, d7c3a293 and then c66b896d; I judged
c66b896d. Lane 1 (NSE, Drive, O1's steps, a forecast check's input). Labels: **strong**, **some**, **reasoning
only**.

## Verdict: FAIL (1 blocking, 1 should fix, 3 minor)

What is right:
- The aim is sound: a provisional close the same evening, confirmed later against the official file within 0.01.
- The stamp rule decides whether a read counts, not the clock time.
- Records are write-once in O9's store, and the step commits only its own receipts pathspec.
- Each failure alerts once (O1's `Alerted` wrapper, with no second alert from the command).
- The step runs on regular sessions only, and a special-session day is `refused` through `NOTHING_WRITTEN`. I checked
  that `fno/daily/steps.py:47` turns an exit-0 "nothing written:" line into `refused`.
- Five record-only sessions come before FL1 shows the value.
- The evidence is honest: the official file's first release time is marked unmeasured; VIX's mismatch (15.7 against
  15.68) is shown; and "one day's stamp" is labelled as one day.

## Blocking

**B1. No gap list (quality rule 2, `docs/JUDGE.md`).** As in judges 353, 355 and 431: every owner rule, design rule
and quality rule must map to a criterion, or to "Out" with its reason. A missing list is a blocking finding. Lines
it needs include:
- the owner's evening-check decision (c3231785, bcbbc454);
- O9 write-once;
- O1/O2's step contract;
- O10's "no ok without data";
- rule 281's three kept parts (private storage, no getting around blocks, paced downloads);
- A7's calendar;
- G13b's official-file rule;
- the public-record rule (SF1);
- quality rules 5, 6 and 8.

## Should fix

**SF1. The success line would put NSE's index closes into the public repository [strong: code read and a planted
record].**
- The exit-0 line is `close read <day>: NIFTY 50 22811.35, NIFTY BANK 54976.9, INDIA VIX 15.7 (list) ...`.
- O1's `CommandStep` stores every printed line of a step and its last line as `reason`
  (`fno/daily/steps.py:44-50`). The daily run commits those into `journal/runs/<date>.json`, which is public on
  GitHub.
- No step does this today: the committed run records name files and counts only (for example "BANKNIFTY recorded:
  banknifty_20261021_150100 (220 contracts, complete=True)").
- The record scan does not stop it. I planted that exact line in a `journal/runs/` file and
  `tools/check_records.py` reported it **clean**.
- Rule 281 (1) and the 21 Oct row (285: "nothing restricted is committed") keep source data in private Drive. NSE's
  terms forbid redistribution, and O9 keeps every NSE data file in Drive.

Fix expected:
- the read and confirm lines name indices, statuses, the NSE stamp, the record's path and its SHA-256, never a level;
- derived facts are fine ("confirmed", "differs by 0.02");
- a criterion that runs the command through O1's `outcome` and asserts that no line holds a value from the planted
  answer.

## Minor

1. **The settle question, measured rather than argued.** Before NSE computes the index close from the
   constituents' closing prices, the list may show the last traded value under a stamp of 15:30 [reasoning only:
   nothing measured near 15:40 exists]. The confirm step will catch a difference, but not its cause. For the five
   record-only sessions, record a second read about 20 minutes later (or at the rerun), so a difference reads as
   "the list moved" or "the list never matched". Also, a hand run's "too early" is 15:30 while O1's step starts at
   15:40. Use one constant for both, or say why a 15:30 stamp read at 15:31 is trusted.
2. **A day that is never confirmed.** If O6's file never reaches Drive for a day, that day stays `provisional` with
   no alert. O6 alerts on its own failures, but say which component names "unconfirmed after N sessions", or state
   that it is O6's.
3. **Boundaries (quality rule 5).** Criterion 4 has the tolerance at, under and over. Criterion 1 already has 15:29 and
   15:30. Add a stamp of 15:31, and the tries at 2 and 3 with a fourth never sent.

## Addendum 1: re-judge at 8d3830a1 (d35108ee for judge 440's points; 8d3830a1 the recheck step O1/O2 agreed)

**Verdict: FAIL (1 should fix).** Every judge 440 finding is answered well. The new second step brings one ordering
defect.

| Finding | Answer | My check | Result |
|---|---|---|---|
| B1: no gap list | A 19-row gap list: the owner's decisions, O9, the public-repository rule, O1's step terms, O10's "no ok without data", A7, VIX as the list's value, record-only, O6 unchanged, the interface, the gates | read; each row maps to a criterion or to Out | **Accepted** |
| SF1: levels in O1's public run record | Lines name indices, statuses, the stamp, the Drive path and the SHA-256 only. Criterion 8 plants distinct values and refuses them in any format (`22811.37`, `22,811.37`, `22811.4`) for a read, rerun, recheck, confirm and refusal | read. The rounded and comma forms close the gap my plant showed the record scan has | **Accepted** |
| Minor 1: settle measured; one gate | `close_recheck` at 16:00 (`same` or `differs by X`, write-once) every session, with the reason (the list is gone by the next day). With no first read, it becomes the day's record, "read at recheck", and does not alert a second time. `CLOSE_READ_FROM = 15:40` serves the hand run and O1 | read | **Accepted** |
| Minor 2: a day never confirmed | One alert at the second session after it, sent once through a write-once `<day>.overdue.json`; O6 alerts on its own file | read | **Accepted** |
| Minor 3: boundaries | stamp 15:31 recorded; the 4th try never sent (counted) | read | **Accepted** |

### Should fix

**SF2. The two steps would delay FL1-1's 15:45 report to about 16:00 every day while `lab_close` exists [strong:
`main`'s `DAILY_RUN_STEPS` and `NotBefore`].**
- On `main`, `DAILY_RUN_STEPS` ends with `candles` and then `lab_close`, the 15:45 report to #fno-forecast, commented
  "last".
- The text puts `close_read` "after `candles`" and `close_recheck` after it. It counts on FL1-1d removing `lab_close`
  ("whichever merges second resolves one line").
- FL1-1d has not merged (judge 438 FAIL). Steps run in order, and `NotBefore` waits through the run's waiter
  (`fno/daily/steps.py:129-138`). If A4h merges first, `lab_close` would start only after the 16:00 recheck, so the
  15:45 report would land at about 16:01 or later.

Fix expected:
- say that both steps go after `lab_close` for as long as it exists, so no consumer's time moves;
- criterion 5 checks the order against the real tuple, not only after `candles`;
- add a test that `lab_close`'s position is before `close_read`'s, while it exists.

A one-line text change; I re-judge it at once.

## Addendum 2: re-judge at 2524cbe5

**Verdict: PASS for the A4h story text.** Code may start.

| Finding | Answer | My check | Result |
|---|---|---|---|
| SF2: the steps before `lab_close` would delay FL1-1's 15:45 report | Both steps go last: after `lab_close` while it exists, else after `candles`. `close_read` then starts at about 15:46. Criterion 5 asserts the order on the real tuple, with a test that `lab_close`'s index is below `close_read`'s | diff 8d3830a1..2524cbe5: only these three passages change | **Accepted** |

For the code round, the claims must show:
- criterion 8's planted-value test, in all its formats;
- the real tuple's order;
- the first five sessions' read, recheck and confirm lines, none holding a level (quality rule 8).
