# Judge 264: LM1 round 1, the position monitor's pure checks (story/lm1-code at 15886d25)

Judge B, 16 Oct 2026. Lane 1 (alerts about trades; a config key). Claims:
`reviews/claude/response_248_lm1-thresholds.md`, sections "Round 1 code claims" and "The owner's decision applied".
Text: LM1 (judge 215 PASS). Thresholds: DESK_DECISIONS 16 Oct 2026, "LM1 position monitor: starting thresholds"
(4186a4ce). Round 1 is pure and unwired: nothing runs on a mark, posts, writes or reads Drive.

**Verdict: FAIL.** One should-fix: one position whose expiry is past NSE's calendar stops every check for every
position.

## Criteria 1-6 and settings

| Item | Result | Evidence |
|---|---|---|
| 1 No trade path | MET | `test_no_trade_path` (a fresh interpreter's module list); E4's rule names are labels only |
| 2 No position, nothing runs | MET | `PositionMonitor.find` returns early |
| 3 Each check at its threshold, quiet just below | MET | loss 50%/80%, strike exactly 0.5%, big move 1.5% then each further 0.5% (`ONCE` per step, Q4b), stale 30 minutes, expiry from 09:30 on the session before and on expiry day. The rounding to 6 digits fixes a real float miss (25,375/25,000 gave 1.4999%) |
| 4 An unusable mark gives only the stale WARNING; unmarked gives "cannot mark" | MET | staleness first; `usable_statuses` adds `incomplete` when `check_incomplete_marks` (Q5b) |
| 5 Limits | MET | per key hourly or once; desk-wide conditions one key; DANGERs past 10 fold into one summary at most every 30 minutes; WARNINGs never folded; mark times only, so replays agree |
| 6 Texts | MET | "F&O monitor:" prefix; action or "information, no action"; the 60-minute line from the desk timetable; no "exit" or "close"; rupees only for the position's own loss |
| Settings | MET | exactly the decided values (pinned by a test); an unknown, missing or bad key stops at start; `monitor` added to `ALLOWED_APP_KEYS` |

## Should-fix: a January expiry in December stops all monitoring

`ExpiryNear.find` calls `self.calendar.sessions(mark.session, expiry)` for **every** position, whatever its expiry.
NSE's calendar ends on 31 Dec 2026 until the 2027 circular is added, so for a position expiring in 2027 that call
raises `CalendarError`. Nothing catches it inside `PositionMonitor.find`, so the whole mark's checks are lost: loss
used, short strike, big move and exit rules, for **every** position, not just that one.

I reproduced it on 15886d25 with the repository's config. On a mark on 1 Dec 2026, a position expiring 28 Jan 2027
at 90% loss used (a DANGER) gives `find() raised CalendarError ...` and no condition at all.

This is a normal path, not an edge case. The books enter the first monthly expiry 30 or more days out, so from about
late November every new trade expires in late January 2027, while NSE's holiday list usually appears only in mid
December. It is also against the calendar-horizon rule set today ("every A7 user fails loudly, by name, never
silently, and never takes other work down"; judges 243, 245, 246).

The fix is the builder's. One way:
- count sessions only when the expiry is within a few calendar days (the warning needs at most
  `expiry_warn_sessions` sessions, so an expiry more than about 10 calendar days away cannot warn);
- and/or catch `CalendarError` per position, giving a named WARNING ("cannot count sessions to expiry: <the
  calendar's words>") while the other checks run.

Add a test: a position expiring past the calendar's end is still checked for loss used on the same mark.

## The builder's interpretations

- **The summary lists only its own mark's DANGERs: ACCEPT.** Conditions held in between are recorded in round 2.
- **Expiry warning once per session: ACCEPT.** It matches "at 09:30" in the owner's row.
- **Exit rule reached once per session: ACCEPT, with a note.** The owner's row says "one alert per condition per
  position per hour" in general. This alert is information only (E8 keeps the action alert), so once a session is less
  noise and loses no action. Say it in the round-2 claims so the owner sees it.
- **The stale clock starts at the 09:15 mark: ACCEPT.**
- **A16's `stale` status counts as stale: ACCEPT.** The row lists missed, failed and late. An index reading that is
  too old cannot be checked either, so the row's intent covers it. Reasoning only; the owner can say otherwise.

## Mutations (real cases)

- Expiry `<=` loosened to `<`: 1 test fails.
- The 6-digit rounding removed from the big move: 1 test fails.
- A `ONCE` key repeating hourly instead: 1 test fails. (My first try at this plant was equivalent to the original code;
  I re-planted it.)
- An incomplete mark treated as unusable despite Q5b: 2 tests fail.

## Gates (run by me on 15886d25)

`env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto -p no:cacheprovider`: 7,253 passed. `ruff check`: clean.
`ruff format --check`: 1,287 files already formatted. `check_imports`: clean. Every file is under 350 lines.

## Addendum 1: the fix at 631ff266 (only `git diff 798e9f3b 631ff266`)

**PASS for round 1 plus this fix, with a merge condition.** Branch head 631ff266 also carries round 2a (798e9f3b: the
mark reader, private alert records, public mark rows, heartbeat, silent check, alert seam). That is unjudged lane-1
work and this verdict does not cover it. Merge either round 1 plus this fix alone (the fix cherry-picks onto 15886d25
with only the claims file conflicting; I did exactly that), or wait for round 2a's own verdict.

| Item | Result | Evidence |
|---|---|---|
| A far expiry needs no calendar | MET | `ExpiryNear._one` returns early when the expiry is more than `7 x (N + 1)` calendar days away; NSE's longest gap is 5 days (pinned below 7 by a test), so the bound is safe |
| A near expiry past the calendar's end is a named WARNING; the other checks run | MET | `CalendarError` becomes `expiry_uncounted` with the calendar's words |
| Any one check's failure is isolated | MET | `PositionMonitor._run`: a raising check gives its own `check_failed` WARNING (class name only, so no value leaks) |
| Texts for the two new conditions | MET | in `ACTIONS`; prefix, first-line and no-exit/close tests |
| My judge-264 reproduction | FIXED | on round 1 plus the fix, 1 Dec 2026 with a 28 Jan 2027 expiry at 90% loss gives `loss_used DANGER` and `short_strike_near DANGER`. On 28 Dec 2026 with a 4 Jan 2027 expiry, the same plus `expiry_uncounted WARNING` |
| Exit-rule once-per-session note for the owner | written in the claims |

**My mutations on round 1 plus the fix:**
- The far-expiry bound removed: 1 test fails.
- `CalendarError` no longer caught in `ExpiryNear`: 1 test fails.
- The isolation narrowed to `KeyError` only: **survives** (75 passed). The isolation test raises one exception type.
  The builder's own "isolation removed" mutant is killed, so this is a note: a second broken check raising another
  type (e.g. `TypeError`) would pin "any exception".

**Gates (run by me on 15886d25 with 631ff266 cherry-picked, the claims file restored):** 7,253 passed (`-n auto`).
The only failures before restoring were the conflicted Markdown file's conflict-marker and record-scan tests. `ruff
check`: clean. `ruff format --check`: 1,287 files already formatted. `check_imports`: clean.
