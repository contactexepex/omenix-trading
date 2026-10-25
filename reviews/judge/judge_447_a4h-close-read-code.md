# Judge 447: A4h, today's index close read after 15:30, code (story/a4h-close-read @ 2098a06d)

Judge F (independent). The story text passed in judge 440 addendum 2. Claims:
`reviews/claude/response_312_a4h-close-read-code.md`. Code commit 9fb8618c; head 2098a06d. Lane 1 (NSE, Drive, O1's
steps). Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 should fix, 1 minor). Everything else meets the story.

What meets the story, checked:
- The stamp rule decides whether a read counts (today, 15:30 or later), and refusals carry no level.
- Regular sessions only. A special session prints `nothing written:`, so O1 records it `refused`.
- Write-once records in O9's store, with the step's own receipts pathspec only.
- The 16:00 recheck records `same` or `differs by X`. With no first read, it becomes the record ("at recheck").
- The confirm records `confirmed` within 0.01 or `differs by X`. A NIFTY 50 or NIFTY BANK difference alerts; a VIX
  difference is recorded only.
- The overdue alert is sent once, through a write-once mark.
- Both steps are last, after `lab_close`, on the real tuple.
- No printed line or alert holds a level; criterion 8 tests 7 formats.
- The deviations are stated, and each is reasonable:
  - 502 lines of code, not about 270;
  - the raw file is the canonical JSON of the parsed answer;
  - the official file comes from Drive, else NSE's archive (as every reader of it gets it);
  - the worst case is about 5.5 minutes;
  - hand runs leave their receipts to the caller.

## Gates (exact head 2098a06d)

| Gate | Result |
|---|---|
| pytest `-n auto` (no Slack token, no growwapi) | **9208 passed**, 16 xfailed, 355 s |
| `ruff check`, `ruff format --check` | clean, 1729 files formatted |
| `tools/check_imports.py`, `tools/check_records.py` | clean (1819 files); record scan clean (7446 files) |

## My plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | the 15:30 stamp time not checked | yes, 1 failed |
| 2 | the tolerance strict (0.01 no longer confirms) | yes, 2 failed |
| 3 | the record's values appended to the read line | yes, 1 failed |
| 4 | the overdue mark ignored (an alert every run) | yes, 1 failed |
| 5 | a VIX difference alerts | yes, 4 failed |
| 6 | a special session read like a regular one | yes, 4 failed |

## Should fix

**SF1. A failure while confirming an earlier day loses today's read, at 15:46 and again at 16:00 [strong: a probe
test].**

`CloseReader.run` calls `self.confirmer.run(day)` first, before the calendar check and before the read
(`reader.py`, line 3 of `run`). `Confirmer._confirm` catches only `BadFile`. Everything else propagates:
- the archive source can raise after its retries (`RawSourceCoolingOff`, network errors; `raw_source.py`
  `_response`);
- the Drive store and cache can raise on `get`;
- a write-once `put` can raise on a conflict.

My probe: day 19 Oct recorded and unconfirmed, the official source raising `requests.ConnectionError`, and a good
NSE answer for 21 Oct at 15:46. Result: **`ConnectionError` raised, nothing printed, and no record for 21 Oct.**
The 16:00 recheck runs the same confirm first and fails the same way. So an outage of NSE's archive, or of Drive
reads, on day d+1 or later costs every later day's provisional close until it clears. That is the evening check's
whole input.

The time limit makes it worse:
- NSE's archive source retries 4 times (`RETRY_WAITS = (5, 15, 45)`, a 60 s timeout each), about 5 minutes per
  unconfirmed day in the worst case, before the read starts;
- the read's own worst case is about 5.5 minutes;
- so one slow confirm can push the step past O1's 600 s `COMMAND_LIMIT_SECONDS`, which kills it.

Fix expected:
- **read first, confirm after.** Today's read must not depend on yesterday's official file;
- catch the confirm's failures per day: one line naming the error class (no message, no level), the day stays
  unconfirmed, and the overdue rule still applies. Decide whether a confirm failure alerts on its own or only
  through the overdue alert, and say which;
- add tests:
  - the official source raising, then today's read still recorded and the exit code still 0;
  - a Drive `get` failure on an earlier record, with the same result;
  - the order: the read's line printed before any confirm line.

## Minor

1. **A hand run's confirm alerts from wherever it runs.** Hand runs leave their receipts to the caller (a stated
   deviation). A hand run that confirms a differing day also sends the alert and writes the `.confirm.json`. That is
   fine, but `CLAUDE.md`'s routine text has no A4h section yet. Say in it, or in the story, that a hand run's receipts
   must be committed (`receipts/data/closes/`), or the next routine run will not see the confirm or overdue files and
   will try to write them again (a write-once conflict).

## Addendum 1: re-judge at 606863fe (response 312, section "Judge 447 answered")

**Verdict: PASS. A4h may merge** (pull, full suite on the merged tree, `check_numbers.py`, then push). Both
`live_from` dates stay `null` until go-live.

Gates on 606863fe: **9213 passed**, 16 xfailed; ruff, ruff format (1729), `check_imports.py` and the record scan
(7446) are clean.

| Finding | Answer | My check | Result |
|---|---|---|---|
| SF1: a confirm failure loses today's read | `run` reads first, then confirms. Each day's confirm failure prints one line with the error class only ("message withheld"), stays unconfirmed, and still falls under the overdue rule (one alert at the second session after it). A failure never alerts on its own. Tests: the official source raising and Drive's `get` raising both record today's read with exit 0, the read line first. The recheck is recorded with the archive down and fails loudly with Drive down | My probe from judge 447 now passes: exit 0, today's record written, and the exception text (a planted "secret-url") in no line. Plants: confirm before the read: 2 failed. No overdue after a failure: 1 failed | **Accepted** |
| Minor: hand-run receipts | `closes read --commit` commits and pushes A4h's receipts only (`receipts/data/closes/`) and exits 1 when NOT committed. O1's steps keep their pathspec | Plant: a NOT committed outcome exiting 0: 1 failed. This fixes the root cause (a fresh checkout not seeing an uncommitted receipt) rather than documenting it | **Accepted** |

**Minor (not blocking).** The confirm now runs after the read, so it can no longer lose the read. But a slow
archive still counts against O1's 600 s limit: about 5 minutes per unconfirmed day when NSE's archive is failing,
after a read that can itself take about 5.5 minutes. If the step is stopped at the limit:
- O1 marks it failed and alerts;
- it commits nothing;
- the record is still in Drive, and its receipt stays in the checkout, so the 16:00 recheck's commit (same pathspec)
  carries it.

So the worst case is a false "failed" line, never a lost close [strong for the path: `steps.py`
`STOPPED_AT_LIMIT`]. A deadline for the confirm loop (stop starting new days after, say, 7 minutes into the
command) would remove even that.

## Addendum 2: go-live and the confirm deadline (story/a4h-golive @ a4a1b910, one commit on main 628c6030)

**Verdict: PASS. It may merge.** Both steps go live on 23 Oct 2026, record-only for their first 5 sessions.

Gates on a4a1b910: **9437 passed**, 16 xfailed; ruff, ruff format (1774), `check_imports.py` and the record scan
(7506) are clean.

**The confirm deadline (judge 447 add. 1 minor) [reasoning, checked against the retry policy].**
- `Confirmer` starts no new day once 240 s have passed since the command began. Days not reached print one line
  ("left for the next run (time budget)"), with no alert.
- One day's archive retries take at most about 300 s (`RETRY_WAITS = (5, 15, 45)` and a 60 s timeout per try), so
  the worst case is 240 + 300 = 540 s, inside O1's 600 s limit.
- A read slower than 240 s leaves all confirms to the next run. The read itself is never cut short.
- The builder's test covers two pending days and a 300 s archive. My plant (a 400 s budget) fails it.

**Config.** `daily.live_from.close_read` and `close_recheck` are "2026-10-23", a regular session in A7's calendar.
`test_steps`' live dates are updated.

**Minor (not blocking).** Days are confirmed oldest first, so the next run starts again with the same day. While
NSE's archive keeps failing on one old day, that day takes the only slot in each run (15:46 and 16:00), and newer
days are never reached. Their overdue alerts then wait until the old day clears. The old day's own overdue alert
still fires once, so the owner hears of it. Trying the newest day first, or rotating the start, would let every day
reach its overdue check.

After go-live, the claims must show the first 5 sessions: read, recheck and confirm lines, with no level in them
(quality rule 8).

## Addendum 3: newest first (story/a4h-newest-first @ 2a3d6677, one commit on main 9a0f8bcc)

**Verdict: PASS. It may merge.** The go-live itself is merged (9a0f8bcc, builder's report).

Gates on 2a3d6677: **9481 passed**, 16 xfailed; ruff, ruff format (1789) and `check_imports.py` are clean.

| Finding | Change | My check | Result |
|---|---|---|---|
| Add. 2 minor: an old day the archive keeps failing takes the only slot in every run | The pending days are sorted newest first. Test: 16 and 19 Oct pending with a 300 s archive; 19 Oct is confirmed and 16 Oct waits a run | Plant: back to oldest first: 1 failed | **Accepted** |

Reasoning only: in a long archive outage the newest days now take the slots, so the oldest wait. Their overdue
alerts are late, but the newest days' alerts still fire after two sessions, so the outage is never silent. A new
day arrives each session, so no day is starved for good once the archive recovers.
