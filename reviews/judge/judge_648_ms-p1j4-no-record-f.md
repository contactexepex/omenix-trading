# Judge 648: MS-P1j4, the school's sections on a day with no school record, story and code (story/ms-p1j4-no-record @ 75f7c584a; code d28c279f3)

**FAIL on 1 should-fix, round 1 of 2, judge 2 of 2 (judge E the other; not read). Lane 1.** Own session
(session_01A8XfbTUVgeeEpqatHaWbtP). Labels: strong, some, reasoning only.

## Criteria

| Check | Result | My evidence |
|---|---|---|
| No sealed decisions → "No school record for <day>: <why>", RED, no rupee, trade or count line | MET | `evening.py:50-51,71-75`; `why` from the committed run log's `school` step (status and public code only, `report_inputs.py:58-60`); plants (path removed; banner GREEN) caught |
| Counts line never empty | MET | `_counts` says "none" (`evening.py:125-129`) |
| 08:50: each driver on its own roads; a failed driver named; "no road open" told apart | MET | `slot.only(driver.card.roads)`; `not_planned` (driver id, failure, error class); `NO_PLAN`; plants (all roads; failure not named; no-plan dropped) caught |
| Nothing private | MET | new lines hold a day, a status, a public reason code, driver ids, failure kinds and error classes; no level, strike or rupee figure |
| **No school-didn't-run day can look quiet** | **NOT MET** | finding 1 |
| gates | MET | trial merge with main b711ed567 (clean): **16,757 passed, 1 skipped, 13 xfailed** (token kept); ruff, format (2,648 files), `check_imports`, `check_records` (9,321 files) clean |

## Findings

1. **Should fix: a day that sealed its decisions but did not finish still looks quiet.** The no-record path fires only
   when no `DecisionRecord` exists. A run that seals and then stops before the finish leaves decisions with no outcomes
   and no counts. The causes are O1's 10-minute limit (`o1:STOPPED_AT_LIMIT`; j3's measured cold run already took
   6 min 13 s), a crash after the seal (j3's gap list) or a Drive failure in the finish. My render of exactly that day
   on the committed code (one trade decision, no outcome, no counts, the step `failed`), via the builder's own
   `evening()` helper, gives:
   `Banner: AMBER, paper only / Trades closed: none / Counts (eligible / fillable / executed): none / Refusals and
   closures: none / Fleet total, rule drivers only: Rs +0`. That is the quiet day this story exists to prevent, and the
   failed step is not shown, by design (`test_a_recorded_day_renders_the_same_whatever_the_run_log_says`). Fix: when
   the session has decisions but no sealed finish (no outcomes/drift seal), or the daily run's school step is not `ok`,
   say so in one line (e.g. "School run incomplete for <day>: the daily run's school step was failed
   (o1:STOPPED_AT_LIMIT); fills and outcomes not recorded"), not GREEN or AMBER-quiet. Test it with a plant.

## Plants

5 planted on 75f7c584a: **5 caught**. No-record path removed; the no-record banner GREEN; drivers planned on all
roads; a failed driver not named; the no-plan message dropped.

## Addendum 1

**Round 2 of 2 at story/ms-p1j4-no-record @ f6af52752 (code ff5846845), judge F, judge 2 of 2: PASS. Lane 1.** Own
session; I did not read judge E.

| Item | Answer | My check | Result |
|---|---|---|---|
| SF1: a sealed but unfinished day looked quiet | `finished` (both of the runner's `FINISHED` kinds sealed) and the step's status; no finish → RED "School run incomplete … fills and outcomes not recorded"; finished but step not ok → RED "… this record may be incomplete"; finished with the step ok or missing → unchanged | my 648 render again on the new code: (unfinished, failed `o1:STOPPED_AT_LIMIT`) → **red**, "School run incomplete for <day>: … fills and outcomes not recorded."; (finished, failed) → red, "may be incomplete"; (finished, ok) and (finished, no step) → amber, unchanged | **Accepted** |
| The claim "both files are sealed even when empty" | | `runner._finish` seals `OUTCOMES` and `DRIFT` unconditionally after the fills; `DashcamStore.seal` writes and publishes the encoded payload for any record tuple, empty included (`dashcam/store.py:30-41`); so a quiet finished day is `finished` and never trips the line | **Confirmed** |
| Nothing private | the new line holds a day, a status and a public code | read | **Confirmed** |

Gates on a trial merge with main d73c75534 (clean): **16,820 passed, 1 skipped, 13 xfailed** (token kept); ruff, format
(2,655 files), `check_imports`, `check_records` (9,338 files) clean.

Plants (round 2), 5, **5 caught**: the incomplete check removed; the finish ignored; the step status ignored; the
incomplete line not red; `finished` as any instead of all. Both rounds: 10 of 10.
