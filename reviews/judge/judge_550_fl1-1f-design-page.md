# Judge 550: FL1-1f design part (the page follows the top block), story/fl1-1f-design-page

- **Judge:** E (session_01HkXMVPDEqVsmJZtghFrGzM), lane 1, round 1 of 2; a delta check, as the orchestrator asked
- **Head judged:** 55ef15fd (548c5fc4 plus the fakes fix), merged with main as 5bcd457c for testing
- **Claims:** docs/stories/FL1-1f-design-page.md
- **Verdict: FAIL.** The page's "why" rows have no test. Everything else reads right.

## Gates
- tests/forecast_lab, tests/school and tests/e2e_acceptance: 3897 passed.
- ruff check and ruff format --check: clean. The designer runs the full suite; the merge run is the one
  full run.
- At 548c5fc4 the same set had 19 failures in tests/school/reports/test_editions.py: the fakes gave every
  index a track, the same cause as judge 538's F1. Fixed at 55ef15fd.

## Finding
**F1 (blocking): the evening's why rows are not pinned on the page.** Three plants pass every test:
- T4: `why_rows` drops `cause_lines`, so the page loses "Missed because (measured)", "no measured cause"
  and every context line;
- T5: the evening passes `with_cues=True`, so each cue is listed twice;
- T6: `unavailable(view)` returns nothing, so a failed or late source reads "no notable moves" instead of
  "not available (<reason>)".

These rows are the owner's item 3 (why, measured facts only, never an invented cause) and the
orchestrator's "never a placeholder". The Slack text pins them (judge 547 Q2 to Q4), but the page does not.
Pin, for the evening page:
- a miss shows its measured cause;
- a miss without one shows "no measured cause";
- a failed source shows "not available (<its reason>)";
- each cue appears once.

## Checked and right
- **Verdict rows:** they use the forecast's own edges, via `edge_words` and `range_words` over q25/q75 and
  q05/q95. T1 (50% edges widened by 10) is caught.
- **Red line:** `verdict_words.no_verdict_words` (what is missing, why, when), never the raw code. T2 is
  caught.
- **Record pill:** `plain.record_words` coloured by `plain.light`, so it shows live only and stays grey
  until 30 live days. T3 (pill always green) is caught. The CSS has every state, `.pill.red` included.
- **Day table and result card:** both show the ranges to the point. The morning's big numbers stay rounded
  outward, as in the text line.
- **No copied words:** the page imports every one from plain.py and verdict_words.py.

## Plants: 6 planted, 3 caught (T1-T3), 3 survived (T4-T6)

## Addendum 1

- **Head checked:** 44666f16, round 2 of 2, a delta check. Since 55ef15fd it adds only one test in
  tests/forecast_lab/test_design_pages.py and the story file.
- **Verdict: PASS. Merge go.**
- **Gates:**
  - tests/forecast_lab, tests/school and tests/e2e_acceptance: 3899 passed;
  - ruff check and ruff format --check: clean;
  - the designer's full suite runs on 44666f16. The merge run is the one full run.
- **F1 fixed:** `test_the_evening_why_rows_carry_the_cause_the_context_and_each_cue_once` pins four things
  on the rendered evening page:
  - a measured miss cause;
  - the no-cause line;
  - "Context: not available (<reason>)";
  - each cue's name exactly once.
- **Plants re-run by me, all caught (1 failed each):** T4 (cause rows dropped), T5 (cues listed twice), T6
  (unavailable sources hidden).
