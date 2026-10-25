# Judge 355: A21 rates and same-day announcements, story text (story/a21-rates-first-seen @ 304589fa)

Judge F (independent), quality rule 1. Story `docs/stories/A21-rates-first-seen.md` at `304589fa` (replaces
70352175; the only change is the settled open points). Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 blocking, 4 should fix)

Part 1 (rates) is well aimed:
- RBI's own pages;
- a check across two RBI sources;
- no back-fill with false first-seen times;
- no consumer default changed.

Every number in the text is true; I checked them live (below). The text has no gap list, and Part 2's schedule cannot
deliver what Part 2 is for.

## Live checks (16 Oct 2026, about 17:30 IST)

| Claim | My read | Result |
|---|---|---|
| RBI release prid=63803: Oct 14, 2026, 2026-2027/1325, YTMs 5.7281 / 6.2896 / 6.4891 | release page: "Date : Oct 14, 2026", cut-off prices 98.5920 / 96.9592 / 93.9220 with those YTMs, "Press Release: 2026-2027/1325" | **True** |
| Home page: Policy Repo Rate 5.50%; 91-day 5.7281% "cut-off at the last auction" | `rbi.org.in/home.aspx`: "Policy Repo Rate : 5.50%", "91 day T-bills : 5.7281%* ... * cut-off at the last auction" | **True** |
| `config.yaml` 6.5%, S6 5.5% placeholder, PROTOCOL.md S6 row | consistent with DESK_DECISIONS 16 Oct ("S6 cash rate: the latest 91-day T-bill yield on the S1 freeze date") | **True** |

## Blocking

**B1. No gap list (quality rule 2, `docs/JUDGE.md`).** As in judge 353: every design and owner requirement must map
to a criterion, or to "Out" with its reason. A missing list is a blocking finding. Examples that need a line:
- the owner's "every failure alerts and is recorded";
- PROTOCOL.md's S6 source rule;
- F2's "first-seen, never a content date";
- the O9 write-once rule;
- A12's boundary.

## Should fix

**SF1. Part 2's schedule cannot deliver a same-day copy before 14:00 on GitHub's cron [strong for GitHub's behaviour
on this repository].** `announcements-live.yml` runs "every 15 minutes, 09:00-14:00 IST". On this repository GitHub
starts 15-minute crons only rarely: participant-oi-watch has 3 runs in about 48 slots (judge 350). It also starts
morning crons 4 h 40 min to 5 h 01 min late (judge 351, every morning scheduled run I checked). So most days would
have no poll inside 09:00-14:00 at all, and F2's cutoff would find nothing.

The stale rule, "no successful poll for 60 minutes inside the window", needs a process that is running to notice the
silence. With no run started, nothing alerts until O8's evening check.

"Lateness can cost coverage but never truth" is honest, but here the coverage loss is the normal case, not the
exception, and the text marks it "reasoning only" although the evidence exists.

Fix expected:
- choose a clock that can deliver the window, and say which, with its evidence. For example one run started before
  09:00 that loops until 14:00 (as A19's poller), started by more than one cron plus a dispatch; or a scheduled Claude
  session; A19's judge 352 SF1 platform question applies to a loop on GitHub's runners;
- say what a run that starts after 14:00 does: record a "missed window" row and alert once;
- say which component alerts when no poll ran by, say, 10:00 on a session day.

**SF2. The text does not say how a poll knows what earlier runs already recorded today.** Each GitHub run is a fresh
process. "Each poll keeps every `seq_id` not already recorded today" needs today's earlier parts, read back through
O9's verified Drive cache. Otherwise a second run re-records every item with a later `first_seen_at`, which is the
first-seen falsification F2 forbids.

Fix expected: state the source of the seen set (today's receipted parts through the Drive cache). Add a criterion
with two separate runs (not two polls in one run) where the shared `seq_id`s keep the first run's time, and a
criterion that a failure to load the seen set stops the run loudly rather than re-recording.

**SF3. The disagreement check will likely fire every auction day for no fault [reasoning only].** The 18:40 IST run
"catches each Wednesday's auction results the same day". If RBI updates the home-page box later than the release,
that run sees a new release and an old home-page figure, and the check posts a false disagreement every week.

Fix expected: compare the home page with the release before the newest when the newest is less than N hours old
(for example 24), or alert only when the disagreement survives into the next run. Add a test for each.

**SF4. The criteria miss quality rules 5, 6 and 8, and the NSE client is not named.**
- Boundaries: 8 days since the last auction, exactly, under and over; the 60-minute silence, exactly, under and over.
- A real output sample (rule 6), and a first live run of each part in the claims (rule 8; "Judge verifies" expects
  live parsing).
- Which HTTP client calls `www.nseindia.com/api/corporate-announcements` every 15 minutes. `docs/DATA_SOURCES.md`
  says `PublicData` is outside A9b's retry policy and "a new caller must [catch all it raises] until it comes under
  this policy". Name the client, its pacing and what a 403 or 429 does (one alert per episode, not one per poll).

## Notes (not findings)

- The repo-rate row "as shown by RBI's home page" with no effective date is honest. An MPC change is effective the
  same day, so the first-seen time is enough.
- FBIL is excluded for the commercial-use reason already recorded in A17's README. Consistent.
- Both workflows go through O10's capture-watch (judge 350 add. 1 PASS); the list must include them.

## Addendum 1: re-judge at 94cda4a8 (main merged; A21's own change is the story text)

**Verdict: PASS for the A21 story text** (1 minor to carry into the code). Code may start: rates first, then
announcements, the latter after A16's owner builds `ObserverGroup`.

| Finding | Answer in the text | My check | Result |
|---|---|---|---|
| B1: no gap list | 19-row gap list (owner's rules, the brief, PROTOCOL.md's S6 source rule, F2's first-seen rule, O9, O10, A12's boundary, A16's conditions, quality rules 5, 6 and 8) | read; every line maps to a criterion or to Out with its reason | **Accepted** |
| SF1: the GitHub cron cannot deliver 09:00-14:00 | no announcements workflow. The poll is one member behind A16's `MarkObserver` port, inside A16's routine, the one process alive in the window. `missed_window` and `no_poll_by_1000` alerts; the 20-mark coverage list; a 5 s GET with no retries and a 10 s budget per mark; the routine's network allowance is a known limit | A16's slot files for 16 Oct: 26 files; 09:15, 09:30 and 09:45 `missed` / `not_taken`, 10:00 `good` (request 0.7 s), so 17 of 20 marks in 09:15-14:00 had a running process, as claimed. The text says plainly that nothing in A21 alerts if A16's routine never runs, and names A16's heartbeat check and O8 as the witnesses | **Accepted** |
| SF2: the cross-run seen set | read once per run from today's receipted parts through O9's Drive cache; an unreadable seen set stops the run with one alert and polls nothing; criterion 8 uses two separate runs | read | **Accepted** |
| SF3: false disagreement each auction day | the release before the newest is accepted while the newest is under 24 h old; criterion 7 tests 23:59 and 24:00, and "matches neither" | read | **Accepted** |
| SF4: boundaries, real run, NSE client | criteria 4, 6, 7, 9 and 10 carry at, under and over cases; `PublicData`'s headers only, one GET with a hard 5 s timeout, everything caught and named; one alert per episode plus "recovered"; real sample and live run in the claims | read | **Accepted** |

**Minor (carry into the code):** `first_seen_at` is "the poll's request time". An item NSE disseminates while the
request is in flight would then be dated before we had it. The text's "later than the true sighting ... never earlier"
holds only for the response time. Use the response time, as A19 does, or state that the difference is under the 5 s
timeout and test the cutoff at the response time.

## Addendum 2: head 5ae76881

Only the claims-file number changes (272 → 274, the orchestrator's renumbering) and main is merged. I checked the
story diff from 94cda4a8: one line. Addendum 1's PASS stands at 5ae76881.
