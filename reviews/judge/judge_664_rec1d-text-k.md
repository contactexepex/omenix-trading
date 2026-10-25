# Judge 664: REC1d text amendment, the recommender's sections in the 08:50 and 20:05 editions, `story/rec1d-sections` at ccc71f331 (round 1 of 2, judge K, judge 2 of 2)

**FAIL, lane 1** (forecast-lab editions), text only. 2 should-fix, 1 minor. Judged by reading.

The change against main is `docs/stories/REC1-recommender.md` alone (+39). Doc-reading tests on ccc71f331, Slack token set:
932 passed, 13 xfailed. No post in the three channels from 03:25 UTC on. I did not read judge J's verdict.

## Checks (the orchestrator's five)

| Asked | Verdict | Own evidence |
|---|---|---|
| Independent flags (school's and recommender's) | **NOT MET** (SF1) | item 2: the section shows "only with `school.reports` on, and from `daily.live_from.recommend`" |
| Byte-identical editions when both are off | MET (as text) | item 2: MS-P1g's golden files are unchanged, plus a new test; criterion (a) with the plant "section always added" |
| Per-section isolation | MET (as text) | item 1: each edition is a tuple of sections, each isolated, with its own `failure_alert`, and the others still post; the reports package imports nothing from `fno/recommend/`; criterion (d) with the plant "one shared `try`" |
| No stale check shown as today's | **PARTLY** (SF2) | the standing answer is named with its record's day, and (c) pins `<` against `<=`. The morning's check lines carry no check date, though |
| Nothing private | MET | item 5: only REC1b's line words and REC1c's check text, no record hash; an unreadable record by path and exception class only |

## Findings

1. **Should fix: the recommender's section depends on the school's switch.**
   - `school.reports` is `true` in `config.yaml` today, and it is the school's own switch (MS-P1g: "the sections ... only when `school.reports` is on").
   - Under item 2, turning the school's sections off also hides the recommender's. Showing the recommender's needs the school's on. The flags are not independent.
   - **Fix (text):** gate the recommender's section on its own key alone, `daily.live_from.recommend` or a new `recommend.reports`, never on `school.reports`. Then criterion (a) has three cases, each with its golden file: both off, school only, recommender only.
2. **Should fix: a check line in the morning carries no date, and "last evening" is not defined.**
   - REC1c's check words, `answer_text` and `trades_text` (`check_run.py:32`'s `LINE` without the record part), name the recommendation's day, never the check's `on` date.
   - Item 3 shows "the latest check of each day checked last evening", but does not say what last evening is. If it means "the latest check" of any date, an older check reads as current. If it means only checks dated last evening, then a night when `recommend check` did not run shows nothing, silently. Only a day with no check file at all is named "check missing".
   - **Fix (text):**
     - "Last evening" is the previous NSE session's date.
     - Each check line names its check date ("checked <on>").
     - Only checks with that `on` are shown as last evening's.
     - When no check file is dated last evening while recorded days wait, the section says so in one line: "last evening's check did not run".
     - Add a criterion with a plant: an older check shown without its date.

## Minor

- **m1:** item 4's "naming the run log's `recommend` status when there is one" should say the status and its reason code only (as REC1b's source statuses do), never the step's printed lines.

## For round 2

Both should-fix findings and the minor are text only: one gate, one definition and one line, plus their criteria.

## Addendum 1: round 2 (the last), `story/rec1d-sections` at 729a3c815 (judge K)

**PASS, lane 1, text only.** 1 note. The change since ccc71f331 is Markdown only (`REC1-recommender.md`). I did not
read judge J's verdict.

**Doc-reading tests** on 729a3c815, Slack token set:
- Runs 2 and 3: 932 passed, 13 xfailed.
- Run 1 failed one test, `tests/test_routine_setup.py::test_setup_does_not_repeat_when_the_plain_install_works`. That file passes alone on this head and on main. A Markdown change cannot reach it, so this is a test that fails under parallel load. I report it to the orchestrator; it is not REC1d's.
- No post in the three channels from 03:32 UTC on.

| Finding | Verdict | Evidence (read) |
|---|---|---|
| SF1: the flags are not independent | fixed | the recommender's own `with_recommend_section(maker, config)` in `fno/recommend/report_guard.py` wraps the lab's maker outside the school's, and is gated only by `daily.live_from.recommend`. Off, it returns the maker unchanged. `fno/school/reports/` is not touched. Neither wrapper reads the other's key. Criterion (a) covers all four switch pairs with golden files, and its plants include "gated by `school.reports`" |
| SF2: undated checks and an undefined "last evening" | fixed | "the previous NSE session by the session calendar". Every check line names its check date. Only checks dated that session are shown; an older one never is. Waiting days with no check that session give "the previous session's check did not run" and are named. Criterion (g)'s plant is an older check shown undated |
| m1: the 20:05 status | fixed | status and reason code only, read through a port shaped like `DayInputs.school_step`; criterion (h) |
| Isolation | met | separate wrappers. A failing recommender section gives one alert with the class name and the edition posts without it. Tested both ways; (d)'s plant puts the recommender's `try` around the inner maker |

**Note:** item 7's template guard fixes each line's shape, but a `data_check_failed` check shows its stored `problem`
text. REC1c fills that from `InputFailed` messages, which can name record paths (`<strategy>-v<n>:<expiry>`, a seal path,
`#<road>`): no strike or price, and the same words REC1c already posts to #fno-desk. That is acceptable. The code
round should keep it to those messages.
