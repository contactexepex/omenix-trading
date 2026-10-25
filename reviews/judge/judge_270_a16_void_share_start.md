# Judge 270: A16 void-share start (story/a16-void-share-start at e647596d)

**Verdict: PASS. Lane 1 (it changes the A16 recorder's trial rule). Merge after A14c's test fix 8016ec6a (judge 269),
which turns main green, and before the v4 freeze byte-checks `fno/intraday/session_rv.py`.**

## Story text first
Owner decision, `docs/DESK_DECISIONS.md` (16 Oct, 4dc17864): day 1 does not count toward the 5% void-RV share. The
count starts at the first session with a recorded previous session. Day 1 stays in the report, labelled "void by
construction", never hidden. WORK_REGISTER: one row, this builder, no overlap. The A16b back-fill report has its own
share, which is outside this decision (see note 2).

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Count starts at the first session whose previous recorded session has a row | MET | `void_share_line`: rows are sorted, and `start` is the first index where `previous_recorded_session` is held |
| 2 | Earlier sessions are not hidden | MET | `; not counted: n before the first session ... (void by construction)` is added whenever n > 0; the RV rows themselves are untouched |
| 3 | A later void still counts and is flagged above 5% | MET | test: 13 void, 14 ok, 15 void, 16 ok gives "1 of 3 (33.3%)" plus the flag and "not counted: 1" |
| 4 | Real 16 Oct state | MET | one void row means "0 of 0 (0.0%); not counted: 1 ...". From 19 Oct, 19 Oct is the first counted session |
| 5 | Gates on a trial merge with main ce8000ce | MET | 7349 passed, 3 failed: the known main-red risk tests (fixed by 8016ec6a, not this change); ruff, check_imports and format clean; files 124 and 169 lines |

## Planted mutations (`fno/intraday/session_rv.py`, all reverted)
| Mutation | Caught |
|---|---|
| Count every row (old rule) | yes, 2 failed |
| Off by one (`rows[start + 1:]`) | yes |
| Rows in reverse order | yes |
| "not counted" note dropped (day 1 would be hidden) | yes |
| `calendar.previous_session` instead of `previous_recorded_session` (does not skip muhurat) | **survived** |

## Notes (not should-fix)
1. The surviving mutant matters only if the trial's second session follows a muhurat evening. `start` is fixed once,
   by 19 Oct (whose previous session, 16 Oct, has a row), so normal running has no path to it. A test with a muhurat
   day between the first two rows would pin it; worth adding next time the file is touched before the freeze.
2. `fno/intraday/backfill_report.py` still counts every row in its own void share, including the series' first
   session, which is void by construction. Over the 2024-26 back-fill that is about 1 of 600 sessions (about 0.2%), so it
   cannot move the 5% verdict. Whether the owner's rule also applies to the back-fill is the owner's call, not a defect
   here.
3. In the test, the `# fmt: skip` dict spans 2 lines, and imports sit inside the test functions. That is style only:
   the file is 169 lines, nowhere near the size limit.

## Addendum 1: 9d91e78f (tests only, one test after e647596d)
**PASS, still lane 1, same merge order. 9d91e78f is now the head to merge.** The new test
`test_the_count_starts_across_a_muhurat_day_from_the_previous_recorded_session` covers 6 Nov (void), the 8 Nov
muhurat, then 9 Nov (ok). Re-planting note 1's surviving mutant (`calendar.previous_session`): 1 failed, so the mutant
is now caught. Restored: tests/intraday 205 passed on a trial merge with main; ruff and format clean. Note 2
(the back-fill report's own share) stays the owner's call.
