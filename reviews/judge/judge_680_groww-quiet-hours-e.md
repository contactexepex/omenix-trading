# Judge 680: Groww quiet hours rule (story/groww-quiet-hours @ 7dc8b0b11), judge E

**PASS (round 1; 2 minor). Lane 1** (a rule about an outside service; judge 1 of 2). Judge E, own session; the other
judge's verdict not read. Text only: CLAUDE.md "How to work" (+4 lines) and AGENTS.md (a new 5-line section).

## Checks

| # | Check | Result | My evidence |
|---|---|---|---|
| 1 matches the owner's words | MET | `conversations/2026-10-25.md` (57dd796ab) quotes: "no human or AI session should run it during 09:15–15:35 IST", where "it" is the manual Groww commands. The rule says "No hand-run Groww command from 09:15 to 15:35 IST ... only the scheduled routines and their own steps call Groww" |
| 2 matches DESK_DECISIONS 57dd796ab | MET | The row "No hand-run Groww command 09:15-15:35 IST" carries the same scope and names CLAUDE.md "How to work" as the owning text. AGENTS.md gives one paragraph and points to it |
| 3 the stated limits are true | MET | 10 a second and 300 a minute for Live Data, and 150 sign-ins per 24 hours: `research/school/probes/2026-10-22-p0-1-groww-chain.md` lines 18 and 22, `fno/providers/groww_sign_in.py:3` |
| 4 no routine conflict | MET | A16's marks, the 3 pm parts, the daily run's Groww steps and step 2b's one rerun are all run by the scheduled routine itself. The pre-open capture ends about 09:12, and its open check reads NSE, not Groww. The hand fixes in the routine sections are git commands only |
| 5 narrows no lane-1 rule | MET | It only adds a restriction. Read-only Groww, no orders and the secrets rule are untouched |
| Gates | MET | Record scan clean (9,539 files); doc-reading tests 963 passed, 13 xfailed, 0 failed |

## Findings

**Minor 1. "no test ... is run by hand then" can be read as "no pytest in market hours".**
- The suite never calls Groww live: every Groww test uses `tests/groww_sdk_fake.py`, and none needs credentials.
- So the rule means a live Groww test or probe. Read literally, it would stop builders and judges from running the
  gates for six hours of every session day.
- Fix: "no live Groww test, probe, download, backfill or check (the test suite uses a fake Groww and is not
  affected)".

**Minor 2, for the owner to know, not a defect.** A hand rerun of `python -m fno daily run` from 09:15 to 15:35 is
now ruled out: it calls Groww. The 22 Oct recovery, when the orchestrator reran the day by hand from 14:09, would not
be allowed.
- If the scheduled 14:05 run fails outright before its 3 pm parts, that day's quotes are lost, unless the scheduled
  session's own step 2b covers it.
- Name the daily run explicitly as a Groww command, so a session cannot argue that it is not one.

## Addendum 1

Narrow check of e5209d7ca and 16861f8bd (head 16861f8bd). **FAIL: 1 should-fix, 1 minor.**

- **Minor 1, fixed:** "no live Groww test ... (pytest never calls Groww live)".
- **The exception matches the owner's words.** The owner said "if a scheduled command is failed, then a manual run
  should be allowed ... It's not one time, it's always. If daily run fails, we should be able to run them manually",
  and the text says "always allowed ... the same command may be run again by hand at once, in market hours too".
  O1's day lock is consistent with it: "a second run beside a living one does nothing".
- **Should-fix 1: it contradicts CLAUDE.md step 2b, and the rule does not say which wins.**
  - Step 2b (owner, 24 Oct) retries the daily run after a failed exits or marks step "once more at once, once only ...
    never a rerun chosen later".
  - The new exception allows the same command again with no limit, and the DESK_DECISIONS row b070ec499 says "as often
    as needed to avoid losing data".
  - Exits and marks are money steps. A session can now read two rules for the same retry: once, or as often as needed.
  - "It's not one time, it's always" can mean "the exception holds every day", not "unlimited reruns a day". The text
    must not decide that silently.
  - Fix: say how the two combine, for example: "step 2b's once-only rule still holds for a daily run that ended 'a rerun
    today retries it'; this exception covers a command that failed or stopped early, once at once, then the owner
    decides". Or quote the owner if the owner meant to lift 2b's limit. Apply the same wording to the DESK row's
    detail.
- **Minor 2:** the two new CLAUDE.md lines (37 and 38) are 156 and 158 characters long. Rewrap them.
- **Gates at 16861f8bd:** record scan clean (9,539 files); doc-reading tests 963 passed, 13 xfailed, 0 failed.

## Addendum 2

Narrow re-check at `02e5b5e0b` (the owner's 25 Oct answer, DESK_DECISIONS e3bbbdfeb, story O14). **FAIL: 1 should-fix,
now a single clause.**

- **The long-term rule matches the owner's words.** The owner said "an exponential backoff policy with a maximum 5
  retries ... then we highlight and escalate to human or operator". The text says "retried with exponential backoff, at
  most 5 retries, then escalated to a human in #fno-desk (story O14)". Matched in both CLAUDE.md and AGENTS.md.
- **Should-fix 1 (680.1's SF1), still open for the interim.**
  - "Until O14 is live, and after an escalation, the failed routine's own command may be run again by hand" sets no
    count.
  - Step 2b (lines 83-84, unchanged) still says the daily run's exits and marks retry is "once more at once, once only
    ... never a rerun chosen later".
  - The orchestrator says 2b is meant to stand until O14 replaces it, but no line says so. "The command's own rules
    still hold" lists the day lock, the skipped steps and fills, not 2b's limit, which is a routine rule.
  - A session can still read "rerun as needed" for the daily run's exits and marks today.
  - Fix, one clause after "still hold (...)": "and for the daily run, step 2b's once-only rerun until O14 replaces it".
    The same in the AGENTS.md line, and in the DESK row's "Until O14 is live, a human may rerun ..." if it is meant as
    a rule.
- **Minor 2, fixed** in CLAUDE.md (no new line over 120 characters). AGENTS.md line 121 is 122 characters: style only.
- **Gates at 02e5b5e0b:** record scan clean (9,539 files); doc-reading tests 963 passed, 13 xfailed, 0 failed.

## Addendum 3

Narrow check at `f69dd5a4d`. **PASS.**

- **Should-fix 1 fixed.**
  - CLAUDE.md now ends "... a failed fills step never retried), and for the daily run step 2b's once-only rerun holds
    until O14 replaces it".
  - AGENTS.md has the same clause ("for the daily run, step 2b's once-only rerun holds until story O14 replaces it").
  - The interim hand rerun and step 2b now agree: once only for the daily run's exits and marks retry; the failed
    routine's own command otherwise.
- **Accepted:** the DESK row stays a verbatim record of the owner's words, and CLAUDE.md is the owning text. That is
  the rule in CLAUDE.md "Code" (lane 3, append-only).
- **No new line over 120 characters.** The diff against main touches only CLAUDE.md and AGENTS.md.
- **Gates at f69dd5a4d:** record scan clean (9,539 files); doc-reading tests 963 passed, 13 xfailed, 0 failed.

No blocking, should-fix or minor finding is left.
