# Judge 666: REC1d code, the recommender's edition sections, `story/rec1d-sections-code` at 9b576e979 (round 1 of 2, judge K, judge 2 of 2)

**PASS, lane 1.** 1 minor, 1 note. Against the passed text 729a3c815 (judge 664.1). I did not read judge J's verdict.

**Gates.** A trial merge of 9b576e979496dd0fbb5ca5f3e8e546297c49f686 into origin/main 096024142 is clean (b1eb24e18). On it,
with the Slack token set:
- `pytest -n auto`: 17,505 passed, 1 skipped, 13 xfailed, exit 0.
- ruff check and format are clean. `check_imports` (2,895 files), `check_records` (9,495 files) and `check_numbers` are clean.
- **No test posted to Slack** (03:59:16-04:08:56 UTC): #fno-forecast and #fno-intraday are empty. #fno-desk holds only
  the orchestrator's "DRY RUN, 2026-10-21 replay" lines.

## Checks

| Asked | Verdict | Own evidence |
|---|---|---|
| Independent switches | MET | `build_recommend_maker` reads only `daily.live_from.recommend`, and with none returns the maker it was given (`is`). `page_wiring.py` wraps `with_recommend_section(with_school_sections(...))`, and `fno/school/reports/` is untouched. Plants caught: always on; the live date ignored |
| Byte-identical goldens | MET | eight goldens, for four switch pairs × two editions. Both off equals the school's own flag-off golden (`tests/school/reports/golden/<edition>.txt`). School only equals the school maker's output exactly, with no recommender title. Recommender only starts with the plain edition. Both put the school's sections first. Files and alerts are unchanged in every pair |
| Isolation | MET | `RecommendReportMaker.make` calls the inner maker first and catches any exception of `render`, keeping the inner text and adding one alert with the class name. `report_guard` catches a set-up failure the same way (`FailedRecommendMaker`) and imports nothing at load. Plants caught: render's catch narrowed; the guard's catch narrowed |
| Privacy | MET | every line is one of `report_words.py`'s templates, REC1b's answer words or REC1c's check words. A failed check's problem is shown only on a full match with REC1c's problem templates; fields are tokens with no spaces, counts and exception classes; anything else is withheld and the check file named (my 664.1 note, built). The 20:05 run-log status and reason are shown only if they match O1's shapes, else `unknown`. Plants caught: problem unguarded; raw reason |
| No stale check | MET | the morning shows only checks dated the previous NSE session (`made[-1] == previous`). Waiting days are named. Today's record is never standing (`d < today`). Plants caught: older check shown; today standing; the waiting line dropped |

## The three stated deviations

| Deviation | Verdict | Why |
|---|---|---|
| A stub line in `tests/school/reports/test_editions.py` | accepted | the lab's root now calls `with_recommend_section`. The school's wiring test stubs it to identity so that it still tests only the school guard. The recommender's own wiring is tested in `test_report_wiring.py`. One line, no assertion changed |
| "N position(s) still open" for a non-final check dated the previous session | accepted | that check has no answer yet. The open count is what REC1c itself prints for a non-final day, and it shows no total |
| `unknown` for a run-log status or reason not in O1's shape | accepted | it keeps m1's "status and code only" true for older logs whose reason was free text |

## Minor

- **m1:** `DID_NOT_RUN` ("The previous session's check did not run") is also printed when the check did run but failed for that day. `check_run` alerts an `InputFailed` and writes no file before the last check. Say instead "no check of <days> is dated <session>", which is true in both cases.

## Note

- Seen in the orchestrator's 2026-10-21 replay, not caused by this branch: "recommend failed: ... the evidence of `school:WS1@1` could not be read: the version is not rated". REC1b's evidence port does not rate a school version that has decisions on that day. That is for REC1b's owner. On a live day it would make the answer `data_check_failed`.

**Plants:** 9 of mine, 9 caught.

## Addendum 1: the m1 follow-up, 401024874 on `story/rec1d-sections-code` (judge K)

**PASS, lane 1.** No findings. I checked 401024874 only; 1d1f1098c, judge J's m1, is J's to check.

- **The words:** `DID_NOT_RUN` is replaced by `NOT_DATED`, "No check of {days} is dated the previous session
  ({on:%d %b %Y}); still waiting.". It is true whether that evening's check never ran or ran and failed for those days.
  The code comment and the story's item 5 note say why. `DID_NOT_RUN` is no longer used anywhere in `fno/recommend` or
  `tests/recommend`.
- **Tests and goldens:** the two recommender-on morning goldens and `test_a_day_still_waiting_..._is_named` assert the
  new line. The words guard (`test_report_words.py`'s `LINES`) lists `NOT_DATED`, so the line is still checked
  against its template.
- **Run on 401024874:** `pytest -n auto tests/recommend tests/school/reports tests/forecast_lab` gave 669 passed.
  ruff check and format are clean for `fno/recommend` and `tests/recommend`.
