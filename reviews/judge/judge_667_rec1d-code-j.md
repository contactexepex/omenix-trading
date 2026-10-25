# Judge 667: REC1d sections, code, story/rec1d-sections-code at 9b576e979 (judge J, 1 of 2, round 1)

**PASS**, lane 1: no blocking or should-fix finding; 2 minor. Trial merge with main 09602414 (d8ce7b34): 17,505 passed,
1 skipped, 13 xfailed; ruff, format, check_imports (2,895 files), check_records (9,495) and check_numbers clean.

## The orchestrator's checks
| Check | Verdict | My evidence |
|---|---|---|
| Four switch pairs: golden files byte-identical where they must be | MET | `test_each_switch_pair_matches_its_golden...` compares all eight files exactly. `test_with_both_switches_off_the_text_is_the_school_s_flag_off_golden` holds off/off to MS-P1g's own golden. My reading of the goldens: each recommender-off text is an exact prefix of its recommender-on text, in both editions. Plants D1 (always added) and D2 (gated by `school.reports`) are caught |
| Nothing private | MET | Lines come only from `report_words.py`, `post.py` and `check_text.py`. A stored problem is shown only when it fully matches one of REC1c's problem templates, whose fields are digits, exception classes or space-free tokens; otherwise it is withheld and the file named (D6 caught). The run-log status shows O1 words or codes only, else "unknown" (D9 caught). The failure alert names the class only (D4 caught) |
| Per-section isolation | MET | `RecommendReportMaker.make` calls the inner maker outside its `try`, so the school's text, files and alerts are kept as made. A section failure adds one alert (D13 caught); a set-up failure gives the inner edition plus one alert (D14 caught). My D3 survived only because it re-raised the inner error, which is equivalent |
| Standing never today; only previous-session checks, dated; waiting days named | MET | D5 (`<=`), D7 (an older check shown), D8 (waiting not named), D11 (live boundary), D12 (an unread check swallowed) and D15 (the step dropped) are each caught |

## The three deviations
1. **The stub line in `tests/school/reports/test_editions.py`: accepted.** It only replaces the new outer wrapper with
   identity, so the school's test still proves the school guard. The outer wrapper has its own tests.
2. **"<n> position(s) still open": accepted.** Without it, a check that is not final would fall through to
   `answer_text`, which says "abstaining cost nothing" whenever nothing has closed. That would be a false statement.
   D10 is caught.
3. **Status as O1 words or codes, else "unknown": accepted.** Older run logs carry free-text reasons that could hold
   anything. Showing only `[a-z_]+` and `x:Y` codes is the privacy rule, and it costs nothing.

## The rehearsal (asked if possible): not run, and why
`fno rehearse morning|evening --day` posts DRY RUN editions to #fno-forecast and #fno-desk, and with no record on
main (`recommend` is not live) it would first need a replayed 23 Oct desk day. I would not post to the owner's
channels on my own call. Instead, I rendered both sections through the real composition root
(`build_report_ports`: the real receipts, the verified Drive reader, NSE's calendar, the run log), with no Slack:
- Morning, 23 and 26 Oct: "No recommendation recorded yet."
- Evening, 23 and 26 Oct: "No recommendation recorded for 23 Oct 2026." and "... 26 Oct 2026."
The full replay is the orchestrator's call; it would need `recommend` live in its rehearsal config.

## Minor
- **m1 (minor)** The goldens mix dates: the page fake is dated Fri 23 Oct, while the recommender's fixture shows a
  standing record of 30 Oct and a previous session of 30 Oct. The comparison is still exact, but a reader cannot check
  the content against the header. Date the fixture to match.
- **m2 (minor)** `MorningSection._checks` reads the latest check file of every recorded day, every morning, to know
  whether it is final. That grows by about 250 reads a year, as REC1c's run does; one "final" index would serve both.

## Notes
- Slack in the window (1792900864-1792901437): one REH1 rehearsal post in #fno-desk shows REC1b's step on a 21 Oct
  replay failing with "the evidence of school:WS1@1 could not be read: the version is not rated".
  - All 12 school versions were registered on 22 Oct (`journal/versions.csv`), so a replay of a day before that meets
    unregistered versions. This is a replay artefact, not REC1d's, and it cannot happen on a live day after 22 Oct
    (reasoning only).
  - The orchestrator may want rehearsals of REC1b to start on 23 Oct.
- Plants: 14 of 15 effective (D1-D15; D3 is equivalent). Run with PYTHONDONTWRITEBYTECODE=1 in their own worktree.
- I did not coordinate with judge K.

## Addendum 1: follow-up on m1, commit 1d1f1098c (round 1, narrow)
**PASS**, lane 1.
- **The scope.** 1d1f1098c touches only `tests/recommend/test_report_maker.py` and three morning goldens. The `fno/`
  changes in 9b576e979..1d1f1098c are 401024874, judge K's wording follow-up, so I did not judge them.
- **m1 closed.** The maker tests now take `DAY` from the page fake (`tests/school/reports/test_editions.py`) and place
  the standing record one day before it.
  - The Fri 23 Oct morning's standing record is 22 Oct, its previous session is 22 Oct, and the school fixture's plan
    is "22 Oct 15:00", so every golden reads against its own header.
  - The changed school-on goldens are this test's fixture text, not production text.
- **The gates at 1d1f1098c.** `tests/recommend`, `tests/school/reports` and `tests/forecast_lab`: 669 passed; ruff and
  format clean.
- **m2, the "final" index, is deferred** by the orchestrator's ruling: a new record needs its own lane-1 design, and
  the cost today is under 10 reads. The trigger is about 60 recorded days. I accept that.
