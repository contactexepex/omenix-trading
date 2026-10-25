# Judge 451: FL1-1d judge-449 minors (story/fl1-1d3-minors at 7fa68060)

**Verdict: FAIL: 1 should-fix finding.** Minor 2 is done well. The fix for minor 1 makes the evening's USD/INR worse
than before, on every day measured.

## Minor 2 (fewer than 2 evening points): accepted
`evening_points` adds "no notable moves in our data" when a right or unchecked evening has fewer than 2 cues, and never
pads. The 0-point and 1-point tests cover it. Strong evidence: read plus the tests.

## Should-fix 1. Reading A17 at `DECISION` (15:00) hides USD/INR in the evening every day
- The change reads every A17 cue at `DECISION` (15:00 IST) in the evening, with `live_only`. A calendar cue is shown
  only on `current` or `ahead`.
- The day's RBI rate comes from `global-cues.yml`'s "14:11 IST" cron. I listed its scheduled runs with GitHub Actions
  (`actions_list`, schedule events). That run actually started at:
  - 17:53 IST on 17 Oct;
  - 21:20 IST on 19 Oct;
  - 19:20 IST on 20 Oct;
  - 19:35 IST on 21 Oct.

  That is after 15:00 IST every time, and sometimes after the 19:53 evening start too.
- So at 15:00 the day's rate is never committed. The reading is `behind`, and the evening shows USD/INR as "not out
  yet" on every measured day.
- Before this change it showed the previous session's rate with its date. The 438.1 table asks for exactly that: "the
  rate dated D, else the latest on or before the previous session, labelled with its date".
- Fix:
  - in the evening, show the day's rate if A17 has committed it by the edition's run time, not by 15:00;
  - otherwise show the previous session's rate (the `OPEN` reading) labelled "previous session", never "not out yet";
  - add a test with a `behind` evening reading that falls back to the labelled previous rate.

  The other cues (US closes, the US 10-year, Brent) read the same at either cutoff, so only USD/INR needs the
  fallback. Strong evidence: the Actions run log.

I did not run the full suite for this verdict: the finding is in the design, and the diff is 34 lines. The next
submission gets one full run.

## Addendum 1: 6a419dab

**Verdict: PASS (lane 1). The builder may merge: pull, one full run on the merged tree, push.**

**Gates:** on 6a419dab merged with today's `main` (no conflicts), one run:
- 9,361 passed, 16 xfailed;
- `ruff check` clean; 1,755 files formatted;
- imports clean; record scan clean (7,486 files).

**The fix: accepted.** Each cue takes ordered cutoffs per edition: the morning `(OPEN)`, the evening `(20:05, OPEN)`.
The first reading inside its rule wins.
- The evening shows D's RBI rate when A17 has committed it by 20:05.
- Otherwise it shows the morning's previous-session rate, with its date and the words "today's value is not out yet;
  the previous one is shown, with its date".

This matches the 438.1 table. The builder also checked my evidence against A17's own commits of `usdinr_rbi.csv`
(19:37 IST on 21 Oct, 21:23 IST on 19 Oct). Strong evidence.

**Minor (a test gap only).** I planted two mutations in `page_wiring.py`, and both still pass (133 forecast-lab tests):
- the evening's cutoffs reduced to `(EVENING_RUN,)` (fallback dropped);
- the order reversed to `(OPEN, EVENING_RUN)`, so the evening would always show the previous rate.

The Section's own test covers the fallback logic, but not the wiring that feeds it. Add one assertion on
`build_sections`' evening cutoffs: run time first, `OPEN` second.
