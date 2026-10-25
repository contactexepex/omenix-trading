# Judge 243: C5c margin calendar reason (story/c5c-margin-calendar-reason at 6ac849da)

Judge B, 16 Oct 2026. Lane 1 (decides a trade: C4's margin check). Claims: `reviews/claude/response_105_c5-risk-buckets.md`
"Addendum C5c"; story C5c in `docs/stories/C-code-roles.md`. Main merged into the branch.

**Verdict: PASS.**

## Criteria

| Criterion | Result | Evidence |
|---|---|---|
| A day the calendar cannot answer is refused by name, never as "too old" | MET | `MarginSettings.fresh` no longer swallows the calendar's ValueError; `margin_row` wraps it as `MarginProblem("margin age for {day} cannot be counted: {reason}")`; test: 4 Jan 2027 names 2027, 1 Jan 2026 names 2025 |
| No calendar wired is refused by name | MET | `ValueError(NO_CALENDAR)` when `session_kind is None` with a sessions age; test asserts "cannot be counted: no NSE session calendar" |
| Covered days unchanged (fresh, or "too old") | MET | tests on covered days; Manual profile's calendar-day age path untouched |
| Fails closed, nothing posted, no date invented | MET | `_run` in `validity_limits.py:101` turns `MarginProblem` into a failed `CheckResult` with the reason; no Slack path added; no weekday fallback; the look-back loop cannot run unbounded because `session_kind` raises past the horizon |
| Register row, story text | MET | one C5c row in `docs/WORK_REGISTER.md`; no other row covers C4's margin age |

## Claims vs reality

- "Only C4's margin age changes": true. The other `.fresh` caller, `fno/risk/margins.py:67`, uses C2's `MarginAge`
  (`DaysOld` / `SessionsOld` in `fno/risk/margin_age.py`), a different class this diff does not touch.
- The replaced test (`..._treats_a_day_the_calendar_cannot_answer_as_a_stale_margin`) still asserts the refusal; only
  the reason changed, as the story asks.

## Project rules

350 lines: all touched files under. Message templates are named module constants (`NO_CALENDAR`,
`CALENDAR_CANNOT_TELL`). No new wiring.

## Mutation (real case)

`raise ValueError(NO_CALENDAR)` changed to `return False`: 1 test fails. Caught.

## Unclaimed-bug hunt

None found. Note only (no normal path): C2's `SessionsOld` still reports a calendar gap as its own `RiskInputError`
wording from the calendar, per the builder; not part of this story.

## Gates (run by me on 6ac849da)

`env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto -p no:cacheprovider`: 6,964 passed. `ruff check fno tests
tools`, `ruff format --check`, `python tools/check_imports.py`: clean.
