# Judge 156: G9 independent re-judge, missed forecasts in protocol v4, as merged at f3835aba (lane 1)

Judge B, independent of the project thread (judges 149-150 were same-session subagents). Merge f3835aba = 8160e992 +
f3da76bd (8ca91924 plus a docs-only main merge). Story `docs/stories/G-forecasts.md` G9; claims
`reviews/claude/response_148_g9-miss-rule.md`; protocol `research/forecasts/PROTOCOL_v4.md` sections 4-6.

## Gates (run myself)
- `tests/forecast_v4` + `tests/forecast_scoring_v4` at f3835aba: **210 passed** (G9 with G8, as claimed).
- Full suite on current main a9eafc57 (contains f3835aba), FNO_SLACK_BOT_TOKEN unset, full history: **5,861 passed,
  0 failed**. `ruff check fno tests tools` clean, `ruff format --check` clean, `check_imports.py` clean.
- Sizes: largest touched file `comparison.py` 126 lines; all well under 350.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Miss = resolved, non-void, baseline present, no forecast, from the first forecast; neither = input failure, apart; unresolved and void are neither | MET | Hand recount below; `_with_empty_days` makes a day neither file holds an input failure; pairing untouched |
| 2 | > 10% of baseline days or > 10% of baseline 2% days missed (any miss below 10) = "undecided, operations": not judged, never claim or futile; Test A undecided | MET | Boundaries below; `look.member_result` returns NOT_JUDGED before any threshold call; NOT_JUDGED is not futile, so `stop_rule.forecasting_test` cannot say "no" |
| 3 | Every comparison and look prints miss counts; protocol and `terms.py` agree (test) | MET | `render.py` text + JSON, `LookResult.lines`, recorded look payload (`cli.py`); `test_protocol_text.py` ties both 10% numbers |

## Judge checks
- **Hand recount** (my own 9-row case): day 0 baseline only (before start), day 1 first forecast, day 2 miss on a 2%
  day, day 3 neither (input failure), day 4 unresolved, day 5 void, day 6 forecast without baseline, day 7 miss, day 8
  both. Expected and got: observable 4, missed 2, 2% observable 1, 2% missed 1, input failures 1, undecided.
- **Caps:** 10/100 no, 11/100 yes, 1/10 no, 2/10 yes, 0/0 no; 2% days 0/9 no, 1/9 yes, 1/10 no, 2/10 yes. Exhaustive
  check for n = 1..2,000 at m = n//10 and n//10 + 1 equals the integer rule `10m > n` (no float edge error).
  `is_big_move` at +-0.02 true, 0.0199 false.
- **Empty cases:** no rows, and rows with no forecast at all, give 0/0 and are not operations-undecided (such a member
  has no regime and is NOT_JUDGED anyway).
- **Planted mutations (real paths only):** removing the operations check in `look.py` fails
  `test_a_member_with_too_many_misses_is_operations_undecided_and_keeps_test_a_undecided`; dropping the freeze start
  (`first = start or ...`) fails `test_after_the_freeze_misses_count_from_the_day_after_it...`. Builder's own seven
  planted breaks (response 148) cover the rest; not repeated.
- **Look 2 order:** a member closed at look 1 stays closed (`run_look` checks `closed` first), so a later outage cannot
  undo a final claim or "no".

## Claims vs reality
All claims in response 148 match the code and my runs. The disclosed Test A reading (M3: an operations-undecided member
blocks a false "no" only; another member's real claim still gives "yes") is what `stop_rule.py` does.

## Coordination
WORK_REGISTER row G9 is "done (merged f3835aba)"; the v4 note says G6 checks G9 before freezing. No duplicate:
`misses.py` is new, and G8's files gain one field and one check each. `DESCRIPTIVE_ONLY` still holds V7 only; the
owner's "V6 descriptive" row is G6's to apply (disclosed in response 148). Not a G9 finding.

## Findings
No blocking, no should-fix.

Notes (one line each, not blocking):
1. The freeze start ("from the day after the freeze for a forecaster that had already started") is in PROTOCOL_v4
   section 4 and the code, not in the G9 story text, which says only "from the first forecast". The protocol rules;
   align the story text at the next G-story edit.
2. PROTOCOL_v4 section 4 has one line over 120 characters ("such days, missing **any** ..."). Cosmetic.
3. A forecaster that starts only after the freeze counts from its first live forecast, so silent days between the
   freeze and that day are "not started". This matches the story; the G6 freeze record should state it.

**Verdict: PASS for f3835aba** (G9 as merged). Nothing to fix forward.
