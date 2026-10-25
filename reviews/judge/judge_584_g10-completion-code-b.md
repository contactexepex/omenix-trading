# Judge 584: G10 completion code (story/g10-completion @ 837bd8c7b), judge B, round 1 of 2

**FAIL (1 blocking, 3 should-fix, 3 minor). Lane 1** (forecast records, Drive, Groww, Slack, the daily run). Base: the
branch's own merge of main (221d2002a, main side b1b2fe371). Story text G10 completion (passed earlier) and its Claims.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| 1 | `v4` part scheduled, live key | MET | `v4_part.py` (times from A4e's window, 14:27 start); `_open`/`_live` `quote_parts.py`; plants live-key-ignored, AfterPart-no-wait caught |
| 2 | commits alone; NIFTY glob narrowed | MET | `apart` flag; real-git pathspec test `test_v4_part.py:131-150`; plants apart-off, wide glob caught (the glob only by `test_day_run.py`'s literals: `test_v4_part.py:148` uses the constant itself) |
| 3 | pack builder | MET | `builder.py` window `start <= t <= end`, clock check; plants `<` at 14:40, clock dropped, late FUT row used: caught |
| 3a | G7b's inputs | PARTLY | imported `first_v4_expiry` (`window_wiring.py:55`), sidecar holds no value, 28 Dec tested (`test_v4_extras.py:78`, `test_cli.py:91`); but the extras run before the required fields: SF2 |
| 4 | release step, D1, D3 | MET | `release_run.py`; plants release-by +60 s, D3 off, no catch-up, release while recording, hung part not stopped: all caught |
| 5 | one label rule | MET | `days.missing_label` used by `_catch_up` and `LiveDayLabels`; plants today-late, missing-unlabelled caught; protocol text test |
| 6 | G8 reads Drive, three readers | MET | `build_day_labels` shared; `DriveRecords` raises on sync problems (plant caught); no `v4_days` left (grep) |
| 7 | 15:10 verdicts | MET | `deadline.py`, `commitments.py`; plants no 15:12 wait, no catch-up, live receipts skipped, unknown time as on time, sealed set widened: caught |
| 8 | G8 applies verdicts | MET | `deadlines.py:55`; plants late row scored, unseen row on time, look passes unchecked: caught |
| 9 | alerts, settings, scan | PARTLY | only `AlertSender` (#fno-desk); key allowed; record scan clean (9,052 files); CLAUDE.md misstates the step order: SF3 |
| 11 | overlap watch | PARTLY | counts only `failures`, not the extras' failures: SF1 |
| 12 | rehearsal | MET | `rehearsal/v4_pack.py`; writes via `rehearsed_drive` (dryrun); plants catch-up in rehearsal, excuse always: caught |
| Gates | exact head 837bd8c7b | MET | ruff, format (2,480), imports (2,609), record scan clean; **15,374 passed, 1 skipped, 15 xfailed** |
| Merge | trial merge with origin/main 2ed42790a | NOT MET | CONFLICT in `fno/daily/quote_parts.py`: B1 |

**Builder's changes to the passed text:** 1 (V4_RELEASE_BY in `release_run.py`) accepted: `git diff origin/main -- fno/forecast_v4/terms.py` is empty, weather hash gate passes. 2 (v4_deadline before `candles`) accepted for the code (`constants_operations.py:73`; A4h's two reads stay last), but see SF3. 3 (14:27) accepted: `_shortly_before`, `test_v4_part.py:78`. 4 (not-live part no part of the day) accepted: `_open`, `test_v4_part.py:94`. 5 (hand release waits to 14:45) accepted: `test_release_rules.py:50-59`. 6 (FUT row Drive only) accepted: sidecar keys are status words only, scan clean. 7 (deadline catch-up from `forecasts_v4`) accepted: consistent with D2, `build_deadline_run`.
**D1/D3 as built:** each one constant, `V4_RELEASE_BY` and `SYSTEM_LATE_FAILS` (`release_run.py:26-29`), read nowhere else; D1's value is also in PROTOCOL_v4 1.6 and its text test, which must move with it (the rule text, rightly). One-place: yes.

## Findings

1. **Blocking: the judged head does not merge with main.** `git merge 837bd8c7b` on origin/main 2ed42790a conflicts in `quote_parts.py`: main's O1 DRY2 (`e8dc9498d`, `7adb2ebc2`: `earliest_start(window_start)` over `earliest_waiting_start`, `INDEX_EARLIEST_START`, `_waited_for`/`_due`, `service()` now calls `start_due()`) against this branch's `earliest_start(window_start, max_early_wait_seconds)`, `_open`, `await_part`. `v4_part._shortly_before` calls the two-argument form. Fix: merge main, resolve so the `v4` part's early limit uses main's shared `earliest_waiting_start`, rerun gates; the resolved scheduler is new lane-1 code and is re-judged in round 2.
2. **Should-fix SF1: the overlap watch misses the v4 job's own extra requests.** `overlap.py:35` sums only `failures`; the extras' `v4_failures` and `future_quote` are ignored. My run: a sidecar with 30 `v4_failures`, a failed future quote and A16's row `good` gives `line() == None`. These are the very requests sent at 14:30:0x beside A16's burst (SF2). Criterion 11 says "any failure in either job". Fix: count `v4_failures` and a non-`recorded` `future_quote`; a test.
3. **Should-fix SF2: the optional extras run ahead of the required fields.** `recorder.py:239` calls `extras.capture` (extra chain, about 90 quotes, the future quote) before NSE's levels (`:244`) and the monthlies' 180 quotes (`:246`). A slow Groww answer per extra quote (timeouts under load) pushes India VIX, the futures and `e`'s ATM pair past 14:40:00, so the day is `system_late` because of fields criterion 3a says never decide it. Fix: call the extras after the monthly fetch and the levels; a test with slow extras keeping the required fields in the window.
4. **Should-fix SF3: CLAUDE.md says the deadline check runs last.** `CLAUDE.md:67`: "A4h's close reads and, last, v4's 15:10 deadline check"; the code runs it before `candles` (Claims change 2). The routine reads this section. Fix the line; the story's step list (`G-forecasts.md:1509`) says the same and needs the same fix.
5. Minor m1: stale story text: "D1 lives in one constant (`terms.V4_RELEASE_BY`)" (`:1759`) and "`terms.py` (one constant)" (`:1791`).
6. Minor m2: release-by is checked before the write (`release_run.py:108`); a slow Drive upload started at 14:44:59 is `A` though written after 14:45:00, against protocol 1.6's "written after 14:45:00". Low risk; say it or check after the write.
7. Minor m3: a live row the check did not see is late (`deadlines.py:55`); safe today (all G7/M1/G7b rows are committed by the same run's checkout), but a forecaster committing from another session would be marked late for rows pushed on time. Note it in the docstring for G7b and G11.

## Plants

28 planted, 28 caught (list in Criteria). None survived; the NIFTY-glob plant is caught only by `test_day_run.py`'s expected strings.

## Notes

No look-ahead found: the catch-up writes only `system_late`, fields outside 14:30:00-14:40:00 are dropped, verdicts use GitHub receipt times. Write-once: `RawFileConflict` named, never overwritten (tests). Tests strip the Drive settings (`tests/conftest.py:118-125`); rehearsal Drive is `dryrun/`.

## Addendum 1: new head 0e5647c7d (docs only on 837bd8c7b), still round 1

**FAIL, unchanged: findings 1-4 stand; minors m1-m3 stand, plus m4.** `git diff --stat 837bd8c7b 0e5647c7d`: two files,
`docs/stories/G-forecasts.md` and `research/forecasts/PROTOCOL_v4.md`, 6 insertions and 6 deletions. All of it is the
D1/D3 status wording ("pending" to "owner decided 24 Oct"). No code or test changed, so the code verdict above holds
for this SHA. The owner's rows are on main: `DESK_DECISIONS.md:324` (D1, "1 - Option A", release by 14:45:00) and
`:325` (D3, "2 - Option A"); both match the code (`V4_RELEASE_BY = time(14, 45)`, `SYSTEM_LATE_FAILS = True`). The
protocol text test passes on the new head (23 passed). The head still conflicts with main (`git merge-tree` exit 1),
so finding 1 stands.
- The builder's leftover 1: `release_run.py:25` and `:28` comments still say "owner pending". This is m4 (minor, stale
  comment): fix it in the next code commit.
- The builder's leftover 2: the decisions bullet still names `terms.V4_RELEASE_BY`. This is my m1, still open; the new
  sentence beside it ("D1 lives in one constant (`terms.V4_RELEASE_BY`)") repeats it.

## Addendum 2: round 2 (the last), exact head 5bde718c1

**PASS. Lane 1.** Every finding is fixed and checked below; there are no blocking or should-fix findings left. I ran
the gates on a trial merge of 5bde718c1 into origin/main 7f37fa7a6. The merge was clean (b1762a0d6). ruff, format
(2,493 files), imports (2,622), record scan (9,067) and number check are all clean. **15,464 passed, 1 skipped, 15
xfailed.** `fno/forecast_v4/terms.py` is still byte-identical to main.

| Judge 584 | Ruling | My evidence |
|---|---|---|
| B1 conflict | FIXED | merge 3782758b8 keeps main's `earliest_start`, `INDEX_EARLIEST_START`, `_waited_for`/`_due`, `service()` calling `start_due()` untouched (`git diff origin/main -- fno/daily/quote_parts.py`: only `_open`/`_live`, `apart`, `await_part`, `waits_for`, `NIFTY_QUOTES`, `HUNG`); my run: nifty 14:38, nse 14:38, indices 14:44 (main's), v4 14:27; plants on the resolved scheduler (no live filter, `apart` off, hung part kept) all caught |
| Deviation: v4 early limit | ACCEPTED | `v4_part._shortly_before` uses A4's one rule `earliest_waiting_moment` (`recorder.py:51`) with the window's own 30-minute wait; main's `earliest_start` hard-codes A4's 20 minutes (`earliest_waiting_start`, `recorder.py:58-62`), wrong for any window whose wait differs. A short-wait window now starts at or after its own limit, never "too early"; my plant (default wait) caught |
| SF1 overlap | FIXED | my round-1 case now gives "31 failure(s) in 1 attempt(s) ... A16's 14:30 mark good"; plants dropping `v4_failures` or the future failure caught |
| SF2 extras order | FIXED | `recorder.py`: extras after the levels and the monthly fetch, only on an attempt with a chain, sidecar keys only from that attempt; plants (extras moved before the levels; an earlier attempt's keys) caught |
| SF3 CLAUDE.md | FIXED | step 2 now runs card, then the deadline check (from 15:12), then the candles, then A4h's reads last; story list `G-forecasts.md:1509` the same; the CLAUDE.md diff against main is G10's lines only; plant "last, v4's deadline" in CLAUDE.md caught |
| m1, m4 stale text | FIXED | no `terms.V4_RELEASE_BY` left in the story; `release_run.py` comments cite the owner's 24 Oct rows |
| m2 release-by | FIXED (residual accepted) | `release.publish(..., in_time)` asks after the pack upload; plant ignoring `in_time` caught. Residual: the small record's own write is not checked (stated). The pre-build check `_built` is now covered by `in_time`: my plant moving it 60 s later survives, because the outcome is the same apart from an orphan pack in Drive that no record names (note, not a finding) |
| m3 other-session rows | ACCEPTED as a stated limit | `commitments.py` and `deadlines.py` docstrings |

**Plants, round 2:** 11 new plants, all caught. I re-ran the 28 round-1 plants on the new head: 27 caught, and the one
survivor is the equivalent `release_by_ge` described above. The orchestrator's merge procedure (quality rule 8) still
applies: one dry run of `v4-pack release` on real data after merge.
