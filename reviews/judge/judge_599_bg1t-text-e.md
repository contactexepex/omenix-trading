# Judge 599: BG1-t story text, Test A's inputs and the freeze date from FREEZE_v4.md (story/bg1t-test-a-inputs @ 4362e2e16), judge E

**FAIL (round 1 of 2, text; 1 should-fix, 2 minor). Lane 1** (the project's stop-or-continue review). Judge E, own
session. Text only: one file, `docs/stories/BG-budget.md`, +88. Judged by reading. Doc-reading tests with the token
kept: 853 passed, 15 xfailed.

## Facts checked

| Claim | Result | My evidence |
|---|---|---|
| Test A's three inputs can never exist | True | `stop_rule_tracker.py:58-60`: no `path`, no `present`, so `exists()` is False |
| `LookRecords.frozen()` / `frozen_on()` | True | `records.py:56-64`, wired with `SCORES_FOLDER` and `FREEZE_FILE` (`v4/wiring.py:29-30,100`) |
| V1's start rule, `V1_START_SESSIONS = 20` | True | PROTOCOL_v4 1.3 (line 57); `capture.py:46,130-134` (live rows with a value) |
| The key's readers | True, complete | `git grep v4_freeze_date origin/main`: `config.yaml:177,198`, `budget/wiring.py:82`, `test_stop_rule_tracker.py:59`, `BG-budget.md:83`, plus review files only. G6's `story/v4-freeze` sets it (`G6-v4-freeze.md:171`), as stated |
| Freeze 25 Oct gives 30 Apr 2027 | True | November-April are six full months; 30 Apr 2027 is a Friday (the weekday fallback) |

## Rulings asked for

| Choice | Ruling |
|---|---|
| G6 input via `frozen()` and `frozen_on()`; a record without its line is not present, with the reason | **Accepted** |
| A16 input: at least 20 live sessions with a value | **Accepted; the open question can be closed now** (minor 1). PROTOCOL_v4 line 197: V1's primary is "HAR daily, then HAR intraday from its first eligible date", so V1 is scored against its primary from its start. The 250 sessions (`HAR_INTRADAY_SESSIONS`) are when the primary switches, not a precondition. Test A's own "fewer than 12 batches is undecided" (section 6) covers a short V1 |
| Removing `budget.stop_rule.v4_freeze_date` with all its readers; a config with the key refused | **Accepted.** One source for the date. `projected_v4_freeze_month` stays under `stop_rule`. The readers list is complete (above) |
| Coordination with G6's freeze (the freeze sets nothing in config; whichever merges second carries the change) | **Accepted.** G6's section 7 / criterion 8 must change through the orchestrator |

## Findings

1. **Should fix: the G8 input names the wrong files.**
   - The Context says "G8's looks are written to `research/forecasts/v4_scores/<day>.json`, with `exploratory` true
     before the freeze", and the design and criterion 2 then test for "a look ... that is not exploratory".
   - In G8's code a look is `look_<name>.json` (`records.py:66-74`, `LookRecords.path`), written once, at the stop
     review itself (`LOOK_STOP_REVIEW = "stop_rule_review"`, `forecast_v4/terms.py:68`).
   - The dated `<day>.json` files are the weekly score reports (`render.py:72`: `"exploratory": not frozen`); today's
     three say `exploratory: true`.
   - Both kinds live in the same folder. A check built on G8's looks makes Test A computable only once the review has
     been run.
   - Fix: name the input as a weekly score report `v4_scores/YYYY-MM-DD.json` with `exploratory` false, dated after
     `frozen_on()`, excluding `look_*.json`. Add a criterion-2 case: a `look_stop_rule_review.json` alone is not the
     input.

## Minor

1. Replace the stated reading's open question ("if Test A meant ... 250 sessions, a gap for the G6/G8 owner") with
   protocol line 197 above. The tracker line can then cite 1.3 and line 197 without a caveat.
2. Design 8.2 says the review date "moves only by a written owner decision" (response 104's gap row: "no override
   key"). After BG1-t the date comes only from the owner-signed freeze record. Name in the gap list that a later owner
   decision moving the review has no input, and is out of scope.

## Plants

None (text round). The named plants cover each `present` check, exploratory reports counted, 19 sessions, a void
row, the old key read, and a record without its date. Add: a look record taken as the G8 input.

## Addendum 1

**BG1-t story text, round 2 of 2 (story/bg1t-test-a-inputs @ df9dee04a): PASS. Lane 1.** Judge E. Against main the
branch changes one file, `docs/stories/BG-budget.md` (+97); the rest is main merged in. Judged by reading.
Doc-reading tests with the token kept: 853 passed, 15 xfailed.

| Round-1 item | Outcome | My evidence |
|---|---|---|
| SF1: the G8 input named G8's looks | **Accepted, fixed** | Context now names both kinds of file with the lines I cited (`render.py:72`, `records.py:66-74`, `terms.py:68`). The input is `v4_scores/YYYY-MM-DD.json` with `"exploratory": false`, dated after `frozen_on()`, never `look_*.json`, with the reason. Criterion 2 adds the B case "a `look_stop_rule_review.json` alone", and the plants add "a look record taken as the G8 input" |
| m1: the 250-session question | Fixed | Closed with protocol line 197 and section 6's 12-batch rule, which the tracker line now cites |
| m2: design 8.2's owner-decision rule | Fixed | In the gap list as out of scope, with its source (response 104) |

## Findings

None blocking, none should-fix, none minor.
