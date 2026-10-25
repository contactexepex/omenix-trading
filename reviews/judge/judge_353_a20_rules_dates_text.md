# Judge 353: A20 point-in-time rules and dates, story text (story/a20-rules-and-dates @ 6487dc7e)

Judge F (independent), quality rule 1 (story check before code). Story `docs/stories/A20-rules-and-dates.md` at
`6487dc7ece4459412298d6fb821e8a6e9de888ec`. The orchestrator sent 3ef27547; I judged the branch head. Labels:
**strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 blocking, 5 should fix, 2 minor)

What is right:
- Step 0 is real, and I reproduced two of its rows.
- The design reuses P6 snapshots, A9's librarian, O9 parts and A6's `known_on`.
- Ports and adapters are named, and the contract master is left out with a good reason.
- Failures go through O10, with no second format.

The text misses quality rule 2 entirely. Several capture paths can lose data or first-seen honesty in the same
situations the owner's 16 Oct rule targets.

## Step-0 claims I re-checked (16 Oct 2026, about 16:50 IST)

| Claim | My check | Result |
|---|---|---|
| The ban list names its trade date, written about 18:12 IST the evening before | `fo_secban.csv`: first line "Securities in Ban For Trade Date 16-OCT-2026:", `Last-Modified: Thu, 15 Oct 2026 12:42:02 GMT` (18:12 IST) | **True** |
| NSE circulars API, 70 items on 15-16 Oct, no cookie | 200, 32.7 KB, `data` holds 70 items; keys include `circDepartment`, `circNumber`, `circFilelink`, `sub`, `cirDate` | **True** |

## Blocking

**B1. No gap list (quality rule 2).** `docs/JUDGE.md`, "Quality rules", 2: every story lists each requirement of its
design paragraph as covered by a named criterion, or as out of scope with the reason, and "a requirement in neither
list is a blocking finding". The text has no such list. Two requirements it already drops have no reason given:
- the gap audit's Part A3 #5 asks for election dates and index-heavyweight results dates; "Out" names "state
  elections and company results dates" with no reason;
- the owner's 16 Oct rule ("every failure alerted and recorded") has no criterion for the alert path (see SF1).

Fix expected: a gap-list table as in A19, mapping each design and audit line to a criterion or to "Out" with its
reason.

## Should fix

**SF1. The criteria miss quality rules 5, 6 and 8, and criterion 5 cannot be tested as written.**
- No boundaries: 30 days ahead exactly, 29 and 31; the ban list for exactly today, the previous and the next
  session; 12 CPI rows, 11 and 13.
- No real output sample (rule 6), and no first live run in the claims (rule 8, which the "Judge verifies" paragraph
  expects).
- "The workflows run on schedule" (criterion 5) is not testable.
- The failure path, the `failure()` line plus listing in O10's `capture-watch.yml`, has no criterion.

Fix expected: each criterion with good, bad, boundary and empty cases; a workflow criterion read by a test (crons,
alert step condition, commit paths, capture-watch list); a real-run criterion as A19's criterion 13.

**SF2. Refusing a ban list "from the future" throws away a real, published list, and the schedule invites it
[strong for NSE's timing].** From about 18:12 IST, NSE overwrites `fo_secban.csv` with the next session's list
(`Last-Modified` 18:12 IST on 15 Oct, for trade date 16 Oct). The design runs at 07:45 with a retry at 11:15, and
refuses a list for a later session.

GitHub starts this repository's morning crons 4 h 40 min to 5 h 01 min late (judge 351, real runs). Some slots never
start at all: participant-oi-watch has 3 runs from about 48 slots (judge 350). On a day when both slots land after
18:12, or neither starts, today's list is already gone. The next day's list, which is real and correctly dated, is
then refused.

Fix expected:
- File any list whose named trade date is the next session under that date, with its first-seen time.
- Add an evening slot after 18:30 IST. It captures the list about 14 hours before it applies, which is also more
  useful for pre-open checks.
- Say what "stale" then means: no list for today's session by the session's start, judged by the A7 calendar.

**SF3. A circular whose file fails is held back from the list, so its first-seen time is falsified and a broken link
alerts every hour.** Design 2 says "a circular whose file fails is not listed, so the next run tries again". So:
- its `first_seen_at` becomes the run in which the file finally downloads, not when the list showed it;
- a link that never works (NSE does publish broken links) keeps the circular out of the record for ever;
- with hourly runs and a `failure()` line per failed run, that means about 15 alerts a day.

Fix expected: list the circular at first sight with a file status (`saved`, `pending`, `failed`). Retry pending files
on later runs. Alert once when a file starts failing and once when it recovers or after N days. Add a test with a
link that fails twice, then works.

**SF4. The NSE window "yesterday to today" loses circulars when GitHub drops a day of runs [some: GitHub's measured
drop rate; the loss follows from the design].** Hourly crons 08:00-22:00 are exactly the kind GitHub drops
(participant-oi-watch: 3 runs in about 48 slots). If no run starts for one full day, the next run asks only
yesterday and today, so the day before is never read. "A missed run loses nothing but timing precision" holds only
for one missed day.

Fix expected: ask from the date of the last successful run (read from the parts), capped (for example 30 days), with
a test planting a 3-day gap.

**SF5. A valid but empty answer passes as "no new circulars", and staleness ignores the calendar for circulars
[some].** The "Judge verifies" paragraph says "nothing new can never hide a failed fetch", but no criterion makes it
true for a well-formed empty answer: `{"data": []}` from NSE, or an unchanged SEBI page for weeks. NSE posted 70
items in two days. Zero circulars over a whole NSE session day, with a run after 18:00 IST, is almost surely a
broken source.

Fix expected: a calendar-based stale rule. No NSE circular for a session day by the last run of that day means
stale, judged by the A7 calendar; SEBI gets a measured longer limit. Add tests on a session day, a holiday and a
weekend.

## Minor

1. An outage of an hourly source posts one line per failed run, up to about 15 a day. Prefer one line when it starts
   failing and one when it recovers, as A19's scope 8.
2. Lot sizes are saved daily under today even when unchanged. That is harmless, but say whether an identical copy is
   stored again or only recorded as "unchanged" (O9 write-once with receipts).

## Rules

Lane 1. Sources: official NSE, SEBI, MOSPI and Fed pages, no login. BLS's 403 is raised as an open question with
options, not worked around. Good. Design: ports for each feed, a strategy for relevance, wiring files named. Not
over-engineered. `pypdf` is a reasonable free dependency; the rejected rule-based alternative is rightly rejected
("a rule, not an announcement we saw").

## Addendum 1: re-judge at 5a51abe9 (story at e50ca714 plus response 266)

**Verdict: PASS for the A20 story text.** Code for A20a, A20b and A20c may follow this text, each judged on its own.

| Finding | Builder's answer (response 266) | My check | Result |
|---|---|---|---|
| B1: no gap list | 12-row gap list; elections and results dates are Out, with reasons (election results already in A6; results dates in A12's daily board-meetings list) | read; each design and audit line maps to a criterion or to Out | **Accepted** |
| SF1: boundaries, real run, workflow criterion | 16 criteria with named boundaries (today / next session across a weekend / previous / two ahead; 45 vs 46 days; 30 vs 29 days; 11, 12 and 13 CPI rows); criterion 13 reads the YAML; criterion 16 is the real output and first live run | read | **Accepted** |
| SF2: next-session ban list refused | filed under its own trade date when that date is today's or the next session; 18:45 IST slot added; stale = no copy for today's session by the end of a trading-day run | Matches NSE's 18:12 write (my `Last-Modified` check in round 1) | **Accepted** |
| SF3: circular held back on a file failure | listed at first sight with a `file` status; retries write a new row carrying the first `first_seen_at`; `abandoned` after 3 days | read; criterion 8 covers fail, fail, works | **Accepted** |
| SF4: "yesterday to today" | **partly**: a fixed 14-day window on every run instead of "since the last success" | I re-ran the 14-day query (2-16 Oct): HTTP 200, **320 items** (143.6 KB), the builder's figure. No stored state, and outages over 14 days are caught by the calendar stale rule and by O8. The reason is sound (KISS) | **Pushback accepted** |
| SF5: empty answer = nothing new | stale = no NSE circular dated the previous session (A7); SEBI 45 days; `{"data": []}` is judged by stale, while a bad answer is `FeedFailed` | My 14-day sample: every session day 5-16 Oct had 24-45 circulars; the holiday (2 Oct) and the weekends had none, so judging the *previous session* is right. I did not re-check the builder's 196 of 196 for 2026 | **Accepted** |
| Minor 1: hourly alert spam | episode keys in `research/ops/alerts/circulars_open.txt` (O8b's pattern), keys only; one "recovered" line | read | **Accepted** |
| Minor 2: lot-size copies | stored daily (about 48 KB) as the daily proof, since NSE gives no date | reasonable | **Accepted** |

Two notes for the code rounds:
- Design 2 says "NSE and SEBI also publish on holidays". My sample shows no NSE circular on 2 Oct (a holiday) or on
  weekends. Hourly runs on closed days are harmless, but correct the sentence.
- Criterion 13's alert condition `failure() && steps.<id>.outputs.posted != 'true'` must still post after a failed
  commit (judge 351's implicit-`success()` lesson). O10's watcher, from 0db3f682, is the backstop.
