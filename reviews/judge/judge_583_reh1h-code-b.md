# Judge 583: REH1h code, files a routine archives in its own run (story/reh1h-archive-serving @ 9ddfd07fc), judge B

**PASS (round 1 of 2; 2 minor). Lane 1** (serves the record's files into a rehearsal: a wrong rule is a look-ahead).
The text passed as judge 573.1. Code: `recorded_archive.py` (new, 99 lines), `manifest_rows.py` (`A9Row`, `archived`),
`nse_wiring.py`, `guard.py`, `recorded_cues.py` (empty `headers`); nothing outside `fno/rehearsal/`.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| H1 | served at the row's commit | MET | my read-only run of `_pick` on the trial merge at 23 Oct 19:53:30 IST: bhavcopy 19:55:20, participant OI 19:55:29, FII/DII by-session 19:55:39 (no Drive read) |
| H2 | never before the commit; fetch-first after it | MET | `get` sleeps `committed - now` (`recorded_archive.py:55-56`) on the forward-only replay clock; S1 (no wait) and S2 (half wait) each fail 8 tests; S3 (window `>=`), S4 (no day bound), S5 (UTC day), S6 (latest ahead), S15 (earliest behind) caught; FII/DII at 20:55 still the 19:55:39 copy |
| H3 | changed or missing copy refused | MET | SHA-256 check `:62-63`; S8 caught; a Drive read error is a `NotRecorded` line (`:58-61`) |
| H4 | one copy or a refusal; run-day lists | MET | ambiguity `:75-77` (S11 caught); repeat cache (S10 caught); `is_run_dated` keeps a `SnapshotTaker` list to the replay day's own row (S7 caught: the self-review's should-fix holds) |
| H5 | empty and HEAD not recorded | PARTLY | inherited `NotRecordedSession.head`; `url_for` check-back (S9 caught); the morning ban-list case, minor 2 |
| H6 | nothing reaches the real record | MET | `RecordFiles(RAW_AREA)` read-only; the wiring test runs the real `build_librarian` and `build_snapshot_taker` and finds writes only under `dryrun/r1/`; the guard names `RecordedArchiveSession` (`guard.py:43`); S12 (old session back) fails 6 |
| A9Row | the index extension | MET | `committed` is the first field, so `_keep` and `archived` order by commit; S14 (field order swapped) fails 32; `seen_at` unchanged for REH1g |
| Limit | the record must be a full clone | MET | the record is the source checkout (`rehearse.py:40`), which `checkout.py:48-49` unshallows before any step and before the guard; a shallow clone dates every row to one commit and errs late or refuses, never early (my judge 572.1 note) |
| Gates | trial merge with main b44d97810 | MET | ruff clean; format 2,448 files; imports clean (2,577); record scan clean (9,017); **15,213 passed, 1 skipped, 15 xfailed** (the skip: `growwapi` not installed here, `test_feed_tls.py:190`) |
| Rules 2-6 | gap list, self-review, plants, cases, sample | MET | self-review findings 1-3 fixed in e709b472a, as claimed; sample's lines match the code's messages |

## Minor

1. **S16 survives:** treating every snapshot list as run-dated (`is_run_dated` without `not in COVERED_SESSION`)
   fails no test. No test serves a by-session copy whose session differs from the replay day: that is the text's own
   case, a 22 Oct by-session read at 19:40. On the record, my run gets the 01:07:09 row (session 21 Oct). Add that
   test.
2. **H5's "no row reached main that day" for a morning ban-list read is not what the record shows.** It holds on 22
   Oct (that list's row reached main on 21 Oct at 20:00:23). It does not hold on 23 Oct: the 23 Oct list reached main
   at 00:04:12 IST that day, so an 08:38 read is served that copy. That is correct and no look-ahead, but the text and
   the test's premise ("taken on the evening of 22 Oct") describe a different day. Reword H5 to "when no row reached
   main that day" and name both cases. No rehearsed routine makes this read (`rehearsal/routines.py`).

## Plants

16 planted, one at a time on the trial merge, each restored with `git checkout --` and `__pycache__` cleared, each
run alone on `tests/rehearsal` (137 tests): 15 caught (S1-S15). Survived: S16 (minor 1). S13 (a Last-Modified in
`RecordedAnswer.headers`) fails 4.

## Notes

- Hunted and clean: `RecordedAnswer` supplies everything NSE's sources read (`status_code`, `content`, `headers`,
  `raise_for_status`; my grep of `fno/storage/`). An empty SHA-256 in a row fails the check, so it is refused. HEAD
  is never answered.
- REH1h was built by session_01GAACYjcfHWkC3hp33iiMXV; this judge shares no context with it or with judge E.

## Addendum 1

**REH1h code, round 2 (story/reh1h-archive-serving @ 5bd3ed8d2), judge B: PASS. Lane 1.** No finding left.

| Round-1 item | Outcome | My evidence |
|---|---|---|
| m1 S16 survived | **Accepted** | two new tests from the record's times (22 Oct 19:40 by-session read gets the 01:07:09 row of session 21 Oct; 21 Oct 21:00 read gets the 22 Oct ban list committed 20:00:23). My re-plant of S16 fails exactly these two (2 failed, 137 passed) |
| m2 H5's morning ban-list line | **Accepted** | H5 now names both record cases (22 Oct: row on 21 Oct 20:00:23, not recorded; 23 Oct: row at 00:04:12, served), as my round-1 run showed; the old test, with the wrong premise, is replaced by one covering both |

**Nothing else changed.** `git diff 9ddfd07fc 5bd3ed8d2 -- fno/rehearsal` is empty. The branch's own commits since
round 1 are aed4e74e5 (one test file and H5) and 224decb57 (Claims). The two main merges (2f7169bdf, 5bd3ed8d2) have
an empty `--remerge-diff` under `fno` and `tests`, and the branch's diff to main is still the eight files of round 1.

**Gates** (trial merge of 5bd3ed8d2 with origin/main 2ed42790a): ruff clean; format 2,461 files; imports clean
(2,590); record scan clean (9,033); **15,307 passed, 1 skipped, 15 xfailed**. The skip is `growwapi` missing here
(`test_feed_tls.py:190`).

**Plants** (4, each alone on `tests/rehearsal`, restored, `__pycache__` cleared): all caught.
- S16 every snapshot list run-dated: 2 failed.
- S4 replay-day bound dropped: 2 failed.
- S17 no list run-dated: 1 failed.
- S18 a wait of one second more: 8 failed.
