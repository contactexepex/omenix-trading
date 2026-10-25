# Judge 638: GW1, Groww's rate limits never exceeded (story/gw1-groww-rate-guard at 01477b7cf), judge I

**FAIL, lane 1.** Round 1 of 2. Judge I (1 of 2; K is the other, not consulted), own session
(session_01CHtddAzFcEdQh4HFiz3mqU), 25 Oct 2026. Judged: GW1's own commits 9761da9cc, 5d5d054ae, 6ddc597b8 and
01477b7cf; f1a94bbeb only merges main. Owner, 25 Oct: never over Groww's limit "in any reason or in any situation".

## Checks

| Check | Verdict | My evidence |
|---|---|---|
| P1 sign-in back-off | MET | `GrowwSignIn`: failure remembered, 5/10/20/30 min, at most 6 a token day, every call in between refused unsent, one alert (class name only) sent outside the lock. G1, G2, G11, G15 caught |
| P2 read-only | MET | `api` is `ReadOnlyGroww` over the guard (orders refused); raw client only through `feed_client()` for the feed probe. G10/H8 caught |
| P3 one 429 detector | MET | the installed SDK: `GrowwAPIRateLimitException.__init__` passes code `"429"` to `GrowwAPIException`, so `is_rate_limit` (`.code == "429"`) catches both forms; Groww's text dropped. G3, G14 caught |
| P4 60 s pause | MET | `RateLimitPause` shared by the provider's threads; A4's attempt stops at its first 429. G4 caught |
| Frozen v4 files | MET | none of FREEZE_v4.md's 232 paths is in GW1's diff (my script); `v4.start` 14:32 is pinned by the new test (my H5 plant, "14:31", caught) |
| Recorded values | MET, with a note | A wait happens only before an attempt's first call; later calls are refused, never delayed, so send times are true. `started_at` stays the attempt's start (15:15:00 for E3) while its first quote is asked at 15:17:00 (note) |
| Rates, any two takers (question 1) | PARTLY | Limit (a) is closed at 6ddc597b8: 4 + 1 and 1 + 1 a second. Measured paces: NIFTY 3 pm about 1.2/s (180 contracts in 155 s, 23 Oct sidecar); A4c 2.5/s paced (`indices.py:25`), ending by 15:06 (12 sidecars of 19-23 Oct). The guarantee still rests on A16 ending inside 120 s (finding 2) |
| New timings (question 3) | PARTLY | A4c from 15:02:00 still ends well before its 15:13 end. NIFTY retries: a 15:00 attempt ends incomplete and the next starts 15:02:00. E3: finding 1 |
| Readers outside `get_provider` (question 4) | MET | pre-open ends by 09:11, before the first mark at 09:15 (`marks()`); A16b at 15:33 is after 15:32:00; A16 and the feed probe build their own (no quiet window, by design) |

## Findings

1. **Should-fix (money path, strong evidence): E3's capture now ends 3-25 s before C3 refuses it, and the story's
   statement about `fills_by` is wrong.**
   - "`desk.fills_by` (15:20) limits only a rerun" is false. The capture window is `execution_snapshot`..`fills_by`
     (`fno/desk/execution_capture.py:78`), and C3's `SnapshotInWindow` refuses any snapshot whose `finished_at` is
     after its end (`fno/checks/snapshot_checks.py:30`).
   - The four committed captures took 2m57s (19 Oct), 2m48s (21 Oct), 2m46s (22 Oct) and 2m35s (23 Oct). Asking from
     15:17:00, they end at 15:19:57, 15:19:48, 15:19:46 and 15:19:35. Before GW1 the margin was over 2 minutes.
   - One slow round, one 60 s 429 pause, or the recorder's own retry puts it past 15:20. C3 then marks the prices
     unverified: no new trade that day, and exits not taken from it (`fno/desk/exits.py:12`).
   - Fix expected: correct the text, and restore a margin that holds the longest recorded capture plus one 60 s
     pause. Options: move `desk.fills_by`, or `desk.execution_snapshot`, or end A16's 15:15 mark sooner. These are
     lane-1 config and desk timing, so the orchestrator or the owner decides; a test pins the margin.
2. **Should-fix (the owner's rule): nothing ends a claimed A16 mark at its quiet window's end.**
   - The 4 + 1 sum keeps A16 apart from A4, E3 and v4 only while the claimed run finishes inside 120 s. The builder's
     own estimate is 101 s at worst, from 4 days of rows.
   - `_retry_failed` re-asks every failed quote at the same pace, calls may each take up to the 10 s timeout, and
     there is no deadline in `GrowwIntradaySource.take` or the recorder.
   - A longer mark overlaps E3 (about 1.2/s), A4c (2.5/s) or v4: 5.2-6.5 a second, over 300 a minute.
   - Fix expected: a claimed take stops asking at mark + `QUIET_SECONDS` (imported), its unasked quotes recorded as
     failures; a test with a slow fake source. (An unclaimed run at 1/s may run longer: 1 + 2.5 stays under 5.)

## Plants

24, each restored and caught, tree clean after each: G1-G16 on 5d5d054ae (back-off, day cap, 429 translation, pause,
quiet check, wait, window, paces, read-only, alert text, next-year 429, wiring); H1-H8 on 01477b7cf (window 90 s,
unclaimed 2/s, claimed 5/s, no sharing, v4 at 14:31, no quiet check, day cap 60, raw client).

## Gates

- 5d5d054ae merged with main c709f11c3 (FNO_SLACK_BOT_TOKEN kept): pytest -n auto 16616 passed, 0 failed; ruff,
  format, `check_imports` and `check_records` clean. Slack in that window: only labelled rehearsal posts.
- 01477b7cf merged with main cbd3937a4 as 897f93842: ruff clean, 2640 files formatted, `check_imports` clean. The
  focused suites passed; pytest -n auto (token kept) 16634 passed, 13 xfailed, 0 failed (581 s). No Slack post in that
  window on any of the three channels.

## Notes (not findings)

- "Any situation" needs a limiter shared across processes: a hand-run Groww command, or another app on the account,
  shares the budget unseen. For the owner: accept, or no hand-run Groww command 09:15-15:35 IST.
- Nothing found in parts 1-4. If part 1 must be on `main` before Mon 08:22 IST, a head of parts 1-4 alone is quick.

## Addendum 1: round 2 at 33f34e571 (the last round)

**Parts 1-4: PASS. Parts 5-6: FAIL, finding 1 open.** Judge I, own session. Under the two-round rule, the owner
decides parts 5-6.

| Item | Verdict | My evidence |
|---|---|---|
| 638.1 E3 against C3's 15:20 window | NOT FIXED | `config.yaml` is not in the diff (`desk.fills_by` still 15:20). The story still says "`desk.fills_by` (15:20) limits only a rerun" (line 114). E3 still asks from 15:17:00 and ends 15:19:35-15:19:57 on the four recorded durations; any 60 s pause or retry is refused by C3 (`snapshot_checks.py:30`). The orchestrator's decision (move `fills_by` to about 15:23, check every reader, keep the school's start under 15:25) is not in this head |
| 638.2 no end to a claimed mark | FIXED, another way | Pacing is set by the clock: 4/s only until `FAST_LEAD` (1 s) before mark + 120 s, then 1/s (`groww_source._pacer_now`). Every call is paced before its send time is stamped. With only one taker (below), A16 after its window is 1/s, so with any one other reader (2.5/s at most) the total is 3.5/s. J1 (fast pace kept) caught |
| One taker per mark | MET | An unclaimed run takes nothing (`ClaimResult.take` is `outcome == WON`); the claim is retried once after 15 s, and an earlier unpushed commit is pushed with `publish()` before it counts. J2, J5, J6 caught |
| Sign-ins | MET | 3 tries a day per process, back-off 5 then 10 min; worst case 38 × 3 = 114 under 150 (the builder's process count, reasoning). J4 (30 tries) caught |
| Hand readers through `get_provider` | MET | `groww-check` and the feed probe's REST client get the quiet windows. J7 caught |

## Plants (round 2)

9 on 33f34e571: J1, J2, J4, J5, J6 and J7 caught. J9 (the unpushed "nothing to commit" counted as published) is
equivalent, since `publish()` never returns that outcome. Two survived, both minor test gaps; the code is right:
- J3: the pacer's wait moved after the send stamp, so A16's recorded send times would be early by up to 1 s.
- J8: `FAST_LEAD` set to 0, so a fast start could fall just after the window.

## Gates

33f34e571 merged with main d6438bafa as 56877c005: ruff, format, `check_imports` and `check_records` clean. pytest -n
auto (FNO_SLACK_BOT_TOKEN kept): **16796 passed, 13 xfailed, 0 failed** (564 s). No post on #fno-desk in the window.

## Addendum 2: round 3 at f21269ea9 (owner's third round, DESK_DECISIONS line 347)

**FAIL, lane 1: the code is clean on every item; one should-fix finding, in the documents only.** Judge I, own
session, independent of K. Judged: GW1's diff against main (merge base c8b56ce96), 19 files.

| Item | Verdict | My evidence |
|---|---|---|
| 638.1 E3 and `fills_by` | FIXED in code | `fills_by: "15:23"`. Longest capture from 15:17:00 + 2m57s + 60 s pause + 60 s = 15:21:57, inside 15:23. Readers I found: `execution_capture.py:78`, `daily_run.py:256`, `runner._finish_parts`, the timetable's order. The school: 15:22:30 at worst, under `SLOT_LAST_START` 15:25. Both pinned by tests (K7 15:20 and K8 15:21 caught). E3's retry case is stated as not covered |
| 638.2 A16 after its window | FIXED as asked | `_call` waits on the pacer, stamps, then refuses at or after mark + `QUIET_SECONDS` (`QuietWindowEnded`, unasked); the window runs from the mark. `_retry_failed` goes through the same call. K1-K5 caught |
| Pace 4/s before the send stamp | MET | Index, future, chains, candle and quotes are all paced in `_call` (J3's survivor now caught as K5). At most 4 workers' calls are still in flight at window end (10 s timeout): they add no new requests |
| One taker; retry counts a landed push | MET | `take` is `won` only; `publish()` pulls and pushes, `_published` needs `count` 1 or 0. K9, K10, K12, K13, K19, K20 caught. K11 (also accept "nothing new") is equivalent: `publish()` always replaces that result |
| `get_provider` for `groww-check` and the feed probe | MET | K14-K18 caught. Readers that build `GrowwProvider` directly: A16, pre-open (ends 09:11), A16b (15:33), all outside the windows |
| Doc rule (GW1's own files) | MET, one minor | GW1 279 lines, GW1a 84. Parts 1-4 point to GW1a. Minor: "The sign-in cap is per process..." repeats GW1a:49 |

## Finding (round 3)

1. **Should-fix (owner's 25 Oct document rule, DESK_DECISIONS line 346): three lane-1 documents now say what the code
   no longer does.**
   - `research/evaluation/PROTOCOL.md:65` and `:497` say "Fills and exits finished by 15:20" and fills_by `15:20`.
     Line 72 adds: "These are the values in `config.yaml` `desk.timetable` today". That is false at 15:23.
   - `docs/stories/O1-daily-run.md:554-557` is the owning text of the owner's 24 Oct rerun rule. It says "The limit
     is 15:20:00 itself" and quotes the alert as "past fills_by 15:20". The code now refuses only after 15:23:00.
   - `docs/stories/A16-intraday-quote-recorder.md:212` says "about 5 a second". A16 now asks at 4 a second, only
     inside the mark's window, and an unclaimed run takes nothing. Today A16's pace and claim rule are described in
     two documents that disagree.
   - Fix expected (text only, about 5 lines): state 15:23 with the owner's 25 Oct decision. In A16's story, replace
     the pace and claim lines with a link to GW1 rule 6, so one document owns them.

## Plants (round 3)

20 on the trial merge, one at a time, each restored, caches cleared, tree clean: 19 caught, K11 equivalent (above).

## Gates

f21269ea9 merged with main 4ac8b39cf as a scratch merge (never pushed). Results:
- ruff check clean; 2749 files formatted; `check_imports` clean; `check_records` clean (9543 files).
- pytest -n auto with FNO_SLACK_BOT_TOKEN kept: **17614 passed, 13 xfailed, 0 failed** (644 s).
- No post on #fno-desk, #fno-forecast or #fno-intraday in that window.

## Notes (not findings)

- O1 (696 lines), A16 (826 lines) and PROTOCOL.md (511 lines) are each over 500 lines. This was true before GW1; it
  is DOC1's work.
- A14c part 2's `margins stress-broker-check` (daily step from 14:05, read-only Groww) is not on main yet. It must
  build its provider through `get_provider`, or it can meet the 14:15 mark at A16's 4 a second.
- The rate-table test is arithmetic over constants. Its teeth are the orderings test and the window tests.

## Addendum 3: narrow re-check of the text fixes at c182a3aa2 (owner, DESK_DECISIONS line 351)

**PASS, lane 1, with 2 minors.** Judge I, own session, independent of K. Scope: only the c182a3aa2 diff on f21269ea9.
It changes 4 Markdown files and one docstring.

| 638.2 item | Verdict | My evidence |
|---|---|---|
| PROTOCOL.md 15:20 | FIXED | Lines 65 and 498 say 15:23 with the owner's reason. Line 76 now says "before `fills_by` (15:23)". Not frozen: its status line is "DRAFT, not frozen", `research/evaluation/` holds no freeze record, and no freeze file names it. The book-3 constitution names it by path; it hashes only its own bytes |
| O1's rerun limit | FIXED | "The limit is `fills_by` itself: 15:23:00", with 15:23:00 filling and 15:23:01 refused. That matches `daily_run.py:256` with the config at 15:23. The alert text matches the template (`{by:%H:%M}`) |
| A16's pace in two documents | FIXED | A16:212 now links GW1 rule 6; `groww_source.py:30` is `PER_SECOND = 4` as GW1 says |
| Sign-in-cap repeat (minor) | FIXED | It is a link to GW1a `#known-limits`; the heading exists. Round 1's parts 1-4 claims link to GW1a `#claims`, which also exists |
| `groww_quiet_windows.py` docstring | MET | Text only: "4 a second, close to 300 a minute"; no code changed |

Minors (do not block):
- `O1-daily-run.md:596-599` still say "a rerun after 15:20" and "at most 15:20:00 less the snapshot ... about 5
  minutes". These lines fall under the new "15:20 times below are the values when this was built" marker. But the
  hindsight they describe is now about 8 minutes, a fact for the owner; one line would state it.
- `E-paper-desk.md:493` "fills by 15:20" is E3's build-time design text ("proposed" times); a link to the config
  would remove the drift.

## Gates (addendum 3)

c182a3aa2 merged with main as a scratch merge (never pushed), because a `.py` file changed. Results:
- ruff check clean; 2749 files formatted; `check_imports` clean; `check_records` clean (9550 files).
- pytest -n auto with FNO_SLACK_BOT_TOKEN kept: **17614 passed, 13 xfailed, 0 failed** (633 s).
- No post on #fno-desk, #fno-forecast or #fno-intraday in that window.

With 638.2's code verdict (every item MET), GW1 parts 5-6 pass judge I.
