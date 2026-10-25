# Judge 637: GW1 Groww rate guard, `story/gw1-groww-rate-guard` at 5d5d054ae (round 1 of 2, judge K, judge 2 of 2)

**FAIL, lane 1** (an outside service; fills read its captures). 3 should-fix, 3 minor. I did not read judge I's verdict.

**Gates.** A trial merge of 5d5d054ae840306ebb82b87a78b9fe044892b8e6 into origin/main ade79b9d7 is clean (284c1fbfe). On it,
with the Slack token set: `pytest -n auto` 16,615 passed, 1 skipped, 13 xfailed, exit 0. ruff check and format are clean.
`check_imports` (2,767 files), `check_records` (9,297 files) and `check_numbers` are clean. **No test posted to Slack**
(23:36:01-23:46:00 UTC): #fno-intraday is empty. #fno-desk and #fno-forecast hold only "DRY RUN, <day> replay" lines,
which the orchestrator's rehearsals were already posting before my run began (00:51 CEST onwards).

## Checks

| Asked | Verdict | Own evidence |
|---|---|---|
| No frozen v4 file changed | MET | none of the 17 changed files is in `FREEZE_v4.md` on main (I grepped each path in the 484-line table and the list). `slots.py`, `recorder.py` (quotes), `book_fetch.py`, `pacing.py`, `composition.py` and the intraday `wiring.py` are untouched |
| No recorded value falsified | MET for A4's rows | the quiet window waits only in `expiries()`, before the attempt's first call. Every other call is refused unsent, so `request_sent_at` stays true (plant "no refusal check": caught). For E8, see SF3 |
| Read-only, 429 named, pause, sign-in back-off | MET | SDK 1.5 source: `GrowwAPIRateLimitException` sets `code "429"` and `GrowwAPIException` keeps `.code`, so `is_rate_limit` catches both. The sign-in tries come at +0, 5, 15, 35, 65 and 95 min, then none (code read) |
| Does any situation exceed the limits; does (a) break the owner's rule | **YES** | SF1 and SF2 |

## Findings

1. **Should fix: limit (a) breaks the owner's rule, and the 429 stop counts only after a breach.**
   - A16 alone at 5/s is the whole 300 a minute. With one run `won` at 5/s and one run `unclaimed` at 2.5/s, a 48-83 s mark gets about 360-620 calls, over 300 a minute.
   - This is realistic. A16's fires overlap by design ("runs one hour past `--until`", A16-owner-checklist section 7), so two runs meet at every mark of that hour. On 16 Oct, two takers lost 74-87 quotes each to 429s (`claims.py:1-3`).
   - "Until the first 429" is the breach itself. The owner said "in any situation", so the builder's limit (a) is not acceptable unless the owner rules otherwise.
   - **Fix, one of two (the owner picks; my reasoning only):**
     - (i) an `unclaimed` run does not take the mark and records it missed. Cost: the mark is lost when every run's claim fails.
     - (ii) A16 asks at 2.5/s always, and the quiet window grows to about 180 s. A4c then starts about 15:03, E3 about 15:18, and E3 ends past `fills_by` 15:20.
2. **Should fix: a mark taken late runs outside the 90 s quiet window.**
   - A16 may take a mark up to 120 s after it (`takeable_marks`, `ON_TIME_SECONDS = 120`), then asks for 50-83 s more, so until about mark + 203 s.
   - A4c (15:01:30, 2.5/s) or E3 (15:16:30) would then share the second with A16's 5/s: 7.5/s, about 450 a minute.
   - It has not happened yet: all 124 taken slot rows sent within 0.0013 s of the mark. But reruns happen: 23 Oct "restarted at 15:05".
   - **Fix:** A16's recorder (not frozen) takes no mark later than a few seconds after it, so its read always ends inside the window. Or the window covers 120 + 90 s.
3. **Should fix (text): E8's stand-in fill snapshot moves later.**
   - When A16's mark is missing, E8 uses an A4 capture whose `started_at` is in the mark's 2-minute window, for example E3's 15:15 capture (`mark_snapshots.py:90-96`). It drops only quotes asked before the mark.
   - Under GW1, E3's `started_at` stays 15:15, but every quote is asked from 15:16:30 to about 15:19. A "15:15" exit fill is then priced 90-240 s after the mark; before GW1 it was 0-154 s.
   - This is not stated, and the orchestrator's Q1 covered timing "never a recorded value". E8 is not live yet.
   - **Fix:** state it under Known limits and tell E8's owner. Either E8 drops stand-in quotes asked after mark + 120 s, or the owner accepts it.

## Minor

- **m1:** the sign-in worst case counts "about 10 processes" but leaves out A16's several overlapping fires and their reruns, and the daily rerun's children. It is still well under 150 (about 100 by my count), but say so.
- **m2:** `groww-check` and the feed probe's REST client build `GrowwProvider` directly, so they get no quiet windows. Both run by hand, and A16 leaves no headroom. Two lines, neither file frozen.
- **m3:** the unpaced sequential readers (NIFTY's 3 pm capture, `v4`, E3) stay under 10/s only because Groww is slow: 180 contracts in 158 s on 23 Oct 14:55. Add this to Known limits.

## Plants

**Mine: 18, all caught:**
- 429 detection off; a pause of 1 s; the pause check off by 1 s.
- The mark excluded; the window's end included; a quiet window of 60 s.
- The back-off cap at 60 min; a 7th try; no day reset; the boundary moved by 1 s.
- No wait before an attempt; no refusal check; `api` without the allow-list.
- No halving; always half pace.
- Groww's text in the alert; Groww's text in the 429; the next-year 429 swallowed.

## Addendum 1: round 2 (the last), `story/gw1-groww-rate-guard` at 33f34e571 (judge K)

**Parts 1-4: PASS. Parts 5-6: FAIL, 1 blocking. The branch as a whole cannot merge as it stands.** I did not read
judge I's verdict.

**Gates.** A trial merge of 33f34e57183cf270d85dd4141d3a1b6802cf8b34 into origin/main d6438bafa is clean (00cd71685). On it,
with the Slack token set:
- `pytest -n auto`: 16,795 passed, 1 skipped, 13 xfailed, exit 0.
- ruff check and format are clean. `check_imports` (2,782 files), `check_records` (9,325 files) and `check_numbers` are clean.
- No test posted to Slack: all three channels are empty for 00:41:24-00:51:01 UTC.
- No changed `fno/` file is in `FREEZE_v4.md`.

| Round-1 finding | Verdict | Own evidence |
|---|---|---|
| SF1: a won run plus an unclaimed one | fixed | `ClaimResult.take` is `outcome == WON`. An unclaimed run retries once after 15 s, then records `missed` ("claim not pushed ... not taken here"). A claim committed but not pushed now counts only after `publish()` pushes it, and the old `NOTHING_AS` = published hole is closed. A pull conflict keeps the remote copy (`-X theirs`), so its holder is `lost`. No path gives two takers |
| SF2: a late mark outside the window | fixed | A16 asks at 4/s until `FAST_LEAD` (1 s) before mark + 120 s, then at 1/s, and every call is paced before its send time. A mark taken up to 120 s late is at 1/s from its start. After a window, A16 at 1/s plus A4c at 2.5/s plus NIFTY at about 1.2/s is about 4.7/s, under 5/s and 300 a minute |
| SF3: E8's stand-in | stated | in Known limits, with 120-274 s, and in the register's E8 row |
| m1, m2, m3 | fixed | 3 sign-in tries per process; the worst case is 38 × 3 = 114, under 150. `groww-check` and the feed probe go through `get_provider`. The unpaced readers' limit is stated |

**Blocking B1: E3's capture can now end after `fills_by`, and C3 then refuses the day's prices.**
- The story says "`desk.fills_by` (15:20) limits only a rerun". That is not so. C3's `SnapshotInWindow` (`fno/checks/snapshot_checks.py:30`) needs the capture's `finished_at` ≤ `fills_by`, and fails as `prices_unverified` otherwise.
- E3 now asks from 15:17:00. Its five recorded captures took 2:34-3:15 (sidecars of 19, 21, 22 and 23 Oct), so they would end at 15:19:34-15:20:15. That leaves 3-26 s of margin, and 22 Oct's 3:15 fails.
- Your decision (fills_by about 15:23) is not on the head: `config.yaml` still says `fills_by: "15:20"`.
- **Fix:** move `desk.fills_by` in this change (or merge it first), and correct line 114. Check the knock-ons:
  - the rerun rule (`FILLS_LATE`) and `runner.py`'s wait to `fills_by`;
  - the school's `SCHOOL_STARTS_BY` 15:25. With E3 ending about 15:20 the school starts about 15:21, which is fine; a day with an E3 retry is near the limit.

**Minor:**
- **m4:** two of my plants survive: `FAST_LEAD` = 0 (fast starts can be booked up to 1 s past the window), and the fast pace back to 5/s. Neither breaks a limit while the window refuses the others, but both rules lack a test.

**Plants:** 12 of mine, 10 caught:
- unclaimed taken; no claim retry; `publish` skipped;
- always fast; 1/s made 4/s; calls unpaced; window 90 s;
- 4 sign-in tries; `groww-check` and the feed probe built directly.

## Addendum 2: round 3 (granted by the owner, 25 Oct), `story/gw1-round3` at f21269ea9 (judge K)

**FAIL, lane 1: the code passes, the text does not.** 1 should-fix (text only, under the owner's 25 Oct documents
rule), 1 minor. I did not read judge I's verdict.

**Gates.** A trial merge of f21269ea9d21bc3933894d75071c65d70ee17fcc into origin/main 4ac8b39cf is clean (f52251c34). On it,
with the Slack token set:
- `pytest -n auto`: 17,613 passed, 1 skipped, 13 xfailed, exit 0.
- ruff check and format are clean. `check_imports` (2,912 files), `check_records` (9,543 files) and `check_numbers` are clean.
- No test posted to Slack: all three channels are empty for 08:21:47-08:32:33 UTC.

| Item | Verdict | Own evidence |
|---|---|---|
| One taker a mark | MET | `take` is `outcome == WON`. An unclaimed run retries once and then records `missed`. `publish()` counts only a push that landed |
| A16 asks nothing after mark + 120 s | MET | `_call` stamps after the pacer and returns `QuietWindowEnded` unasked at or after the window's end. A late mark is bounded from the mark itself |
| Every A16 call paced at 4/s before its stamp | MET | `self.pacer.wait()` comes first in `_call`, so the chains, future and index are paced too. `PER_SECOND` 4, which is 240 a minute |
| `fills_by` 15:23 and the school | MET | 15:17:00 + 2m57s + 60 s pause + 60 s = 15:22:57 ≤ 15:23; school start 15:22:30 ≤ `SCHOOL_STARTS_BY` 15:25. Both are pinned by tests. C3's window, `FILLS_LATE` and the runner's end wait all read `fills_by`, and the timetable tests now take it from config. E3's retry is stated as not covered, as before GW1 (22 Oct) |
| Overlaps | MET | inside a window: A16 alone at 4/s, and every `get_provider` reader refused. Outside: the readers' orderings are pinned in code (A4c after NIFTY, v4 ends before NIFTY, E3's first call after both). In the window's last second, at most 4 in-flight A16 calls plus one other reader, under 10/s |
| `groww-check` and the feed probe | MET | both are built through `get_provider` |
| Frozen files | MET | none of the changed `fno/` files is in `FREEZE_v4.md` |

**SF1 (should fix, text): three statements no longer match the code.**
- `docs/stories/GW1-groww-rate-guard.md:13` says "A16 alone paces at 5 a second (`groww_source.py:26`)". It now paces at 4 (`groww_source.py:30`).
- `fno/providers/groww_quiet_windows.py:3`'s docstring says "A16 asks at 5 a second, which is 300 a minute". It is 4.
- Story line 160 says "Groww's limit is 5 a second". Groww's limits are 10 a second and 300 a minute; 5 a second is the minute cap averaged. Say so.
- Two one-line text fixes and one docstring; no code behaviour changes.

**m1 (documents rule: no part described twice):** the story's round-1 Claims (lines about 245-275) still describe parts 1-4, the sign-in sample output and its mutations, which GW1a's document owns. Replace them with a link to GW1a.

**Document lengths:** `GW1-groww-rate-guard.md` has 279 lines and `GW1a-groww-guard-core.md` 84, both under 500. The parts 1-4 rule text links to GW1a (lines 22 and 40).

**Plants:** 14 of mine, 14 caught:
- asking after the window; 5/s; stamp before the wait;
- unclaimed taken; publish skipped; window 90 s;
- `get_provider` without the windows; no wait; `fills_by` back to 15:20;
- `groww-check` and the feed probe built directly.
- Three of them first "survived" only because my own plant script left out `test_groww_quiet_windows.py`; all three are caught with it included.

## Addendum 3: GW1 round 3's text fixes, c182a3aa2 on `story/gw1-round3` (judge K, narrow re-check approved by the owner)

**PASS, lane 1.** 1 note. I checked only the c182a3aa2 diff, on top of f21269ea9 (637.2). I did not read judge I's verdict.

**Gates.** The commit changes a `.py` docstring, so I ran the full gates. A trial merge into origin/main 8861e50d4 (c7258d3a8), Slack token set:
- `pytest -n auto`: 17,613 passed, 1 skipped, 13 xfailed.
- ruff check and format are clean. `check_imports` (2,912 files), `check_records` (9,550 files) and `check_numbers` are clean.
- No test posted to Slack: all three channels are empty for 09:12:45-09:22:55 UTC.

| 637.2 item | Verdict | Evidence (read) |
|---|---|---|
| SF1: line 13 | fixed | "Before GW1, A16 alone paced at 5 a second ... GW1 paces it at 4 (`groww_source.py:30`)". Line 30 is `WORKERS, PER_SECOND = 4, 4` |
| SF1: the `groww_quiet_windows.py` docstring | fixed | "A16 asks at 4 a second ..., close to Groww's 300 a minute Live Data cap (5 a second averaged)". `QUIET_SECONDS`' comment ("83 s at most at 5 a second; about 95 s expected at A16's 4") is true as history |
| SF1: line 160 | fixed | "Groww's Live Data limits are 10 a second and 300 a minute. Over a minute, 300 averages 5 a second, so every row must stay at or under 5 a second" |
| m1: parts 1-4 claims | fixed | the round-1 claims and the sign-in sample are gone, with one link to GW1a's `#claims`. The sign-in cap is a link to GW1a's `#known-limits`. Both anchors exist in GW1a (lines 47 and 68) |
| The other files | true | `O1-daily-run.md`'s limit is `fills_by` itself, 15:23:00 (start at 15:23:00 fills, 15:23:01 refused), and `SnapshotInWindow` is now by `fills_by`. Both match `config.yaml` and `test_fills_final.py`. `PROTOCOL.md` (a draft) says 15:23 with the reason. A16's story links GW1's rule 6 for the pace instead of restating "about 5 a second" |

**Note (documents rule):** this commit touches three documents that are over 500 lines on main: `A16-intraday-quote-recorder.md` (826), `O1-daily-run.md` (697) and `research/evaluation/PROTOCOL.md` (512). The commit adds only a few lines to each, so this is DOC1's item, not GW1's. `GW1-groww-rate-guard.md` is now 253 lines.
