# Judge 582: REH1h code, files a routine archives in its own run (story/reh1h-archive-serving @ 9ddfd07fc), judge E

**FAIL (round 1 of 2; 1 should-fix, 1 minor). Lane 1** (serves the record's files into a rehearsal). Judge E, own
session (session_01Sp5rJyPberRttZaJ4WwW26); judge B's verdict not read. Labels: strong, some, reasoning only.

## Criteria (against the text that passed 575.1, plus 5816e044e's three edits, which I checked: no rule loosened)

| # | Criterion | Result | My evidence |
|---|---|---|---|
| H1 | the day's own files served at their row's commit | MET | Real record (full clone), replay 23 Oct 19:53:30: fo-bhavcopy at 19:55:20, participant OI at 19:55:29, by-session FII/DII at 19:55:39, each at its own dataset's path; P1 (no wait) 8 failed; P16 (Last-Modified) 4 failed |
| H2 | never before the commit; window, day bound, at-or-before | MET | `_pick` serves an ahead row only after `sleep(committed - now)` (`recorded_archive.py:55-56`); a past row has committed <= now. P2 (`>=` at +10 min), P3 (past row preferred), P4 (earliest past), P5 (no day bound), P6 (UTC day for IST) each caught. Ahead preferred, earliest of the ahead rows: `:72-73` |
| H3 | changed, missing or unreadable copy refused | MET | P7 (no SHA), P8 (refused copy remembered), P9 (read error escapes) caught; `UNREAD` is a `NotRecorded` (an `InvalidURL`), so the library says "(not sent)" |
| H4 | one copy or refused; repeat gets the same | MET | P13 (no ambiguity), P18 (no repeat cache), P10 (run-dated rule dropped) caught. Real record: 0 (URL, commit) groups with two SHA-256 |
| H5 | empty and HEAD NOT_RECORDED | PARTLY | P12 (no `url_for` check-back), P15 (HEAD answered) caught. The morning ban-list sentence is not true of the real record (minor 1) |
| H6 | writes only under `dryrun/`; real Drive read only | MET | Wiring test on the real `build_librarian` and `build_snapshot_taker`: `real.writes == ["dryrun/r1/raw/..."]`; P17 (old session wired back) 6 failed; P19 (index keeps the latest row) caught |
| Rule 4 | each branch has a test that fails when broken | NOT MET | the session-filed exception in `is_run_dated` (finding 1) |
| Gates | trial merge 602b365f1 with origin/main | MET | ruff clean; format clean (2,448 files); imports clean (2,577 files); record scan clean (9,017 files); full suite **15,213 passed, 1 skipped, 15 xfailed, 0 failed** (the skip: `growwapi` not installed here, `test_feed_tls.py:190`); new file 99 lines, `manifest_rows.py` 136 |

## Findings

1. **Should fix: nothing tests that a session-filed list may serve a row for another session.** My P11 (`is_run_dated`
   without `source not in COVERED_SESSION`, `recorded_archive.py:94`) passed all 137 rehearsal tests. It treats
   by-session FII/DII, NSDL by-session and the ban list as run-dated, so only a row whose `day` is the replay day can
   be served. On the real record that changes real reads [strong: my script on the full clone gives the picks; P11's effect follows from `:84`]:
   - 22 Oct 19:40, by-session: the design's own example (story and docstring `:10-11`) gets the 21 Oct session's
     copy (committed 22 Oct 01:07:09 IST); under P11 it gets NOT_RECORDED. The 21:00 reads of 14, 15, 16, 17 and 20 Oct
     go the same way.
   - 21 Oct 21:00, ban list: the 22 Oct list (committed 21 Oct 20:00:23) becomes NOT_RECORDED.

   No look-ahead either way (the error is a false NOT_RECORDED), but it is a stated behaviour that a one-line edit
   breaks without any test noticing. Fix: one test with a by-session row whose `day` is the day before the replay day,
   committed on the replay day, that is served. Add one for an evening ban-list row for the next session.

## Minor

1. H5's line "a morning fetch-first read of the ban list: ... no row reached main that day" is not true on 23 Oct.
   The 23 Oct list reached main at 00:04:12 IST that day, so an 08:40 read is served it. The copy is correct (the
   session's own list, committed before the read). Reword: NOT_RECORDED only when the copy reached main the evening
   before. No rehearsed routine reads the ban list (`rehearsal/routines.py`, grep).

## Plants

18 planted, one at a time, on `tests/rehearsal` (137 tests), each restored with `git checkout --` and `__pycache__`
cleared: P1-P10, P12, P13, P15-P19 caught (17); P11 survived (finding 1). All in one worktree, never beside the full
run.

## Notes

- Hunted: `get` waits on the replay clock (`now_ist`); `ReplayClock` only moves forward, so a real sleep never serves
  early. `served` is set only after the SHA check. A shallow record dates every row to one commit; `checkout.py:48-49`
  unshallows the source before a rehearsal (the Claims' stated limit holds).
- The Claims' output sample uses fixture days (9 and 13 Oct). My real-record run above stands in for 23 Oct.

## Addendum 1

**REH1h code, round 2 of 2 (story/reh1h-archive-serving @ 5bd3ed8d2): PASS. Lane 1.** Judge E, own session. Since
9ddfd07fc the branch changes no file in `fno/rehearsal/`: `git diff 9ddfd07fc 5bd3ed8d2 -- fno/rehearsal` is empty.
Only `tests/rehearsal/test_recorded_archive.py` (+3 tests, 1 replaced) and H5's text changed, plus main merged in.

| Round-1 item | Outcome | My evidence |
|---|---|---|
| SF1: no test for the session-filed exception in `is_run_dated` | **Accepted, fixed** | `test_a_by_session_copy_of_the_session_before_committed_on_the_replay_day_is_served` (22 Oct 19:40, the 21 Oct row committed 22 Oct 01:07:09, no wait) and `test_an_evening_ban_list_for_the_next_session_is_served` (21 Oct 21:00, the 22 Oct list committed 21 Oct 20:00:23). Their times match my round-1 run on the full clone. My P11 again: **2 failed, 137 passed** (it survived in round 1) |
| m1: H5's morning ban-list line | **Accepted, fixed** | H5 now says NOT_RECORDED only when the list reached main the evening before. Both record cases match my real-record run: 22 Oct 08:40 gives None (row on 21 Oct 20:00:23); 23 Oct 08:40 is served the 00:04:12 copy. The replaced test checks both halves |

## Gates (trial merge fc15d6b4d with origin/main 2ed42790a; main moved only by lane-3 files beyond the branch)

ruff clean; format clean (2,461 files); imports clean (2,590 files); record scan clean (9,033 files); full suite
**15,307 passed, 1 skipped, 15 xfailed, 0 failed** (7 min 50 s; the skip is `growwapi` not installed here,
`test_feed_tls.py:190`). `tests/rehearsal`: 139 passed.

## Findings

None blocking, none should-fix, no minor left.

## Plants (round 2, each alone on `tests/rehearsal`, restored, `__pycache__` cleared)

3 planted, 3 caught: P11 (session-filed lists treated as run-dated) 2 failed; P5 (no replay-day bound) 2 failed;
P10 (run-dated rule dropped) 1 failed. Round 1's other 16 plants hit code that has not changed since.
