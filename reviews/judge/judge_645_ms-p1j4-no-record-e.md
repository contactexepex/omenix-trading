# Judge 645: MS-P1j4, the school's sections on a day with no record, and the 08:50 plan (story/ms-p1j4-no-record @ 75f7c584a; code d28c279f3), judge E

**FAIL (round 1 of 2; 1 should-fix). Lane 1** (Slack reports and the evaluation record shown; judge 1 of 2). Judge E,
own session; judge F's verdict not read. Text and code judged together.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| 1 no record, said so | MET | `HowDidTodayGoSection.render`: no `DecisionRecord` gives `_no_record`, a red banner with "No school record for <day>: <why>." and the footer. My R1 (branch removed): 8 failed. R2 (banner amber): 4 failed |
| 2 the why | MET | `SealedDayInputs.school_step` reads the committed run log's `school` step (status and public code only). R3 (another step read): caught. R4 (a read error swallowed into "no step"): caught |
| 3 counts never empty | MET | R8 (the "none" line removed): caught |
| 4 08:50 no plan | MET | R7 (always `NO_PLAN`): caught |
| 5 a recorded day unchanged | MET as written, and that is finding 1 |
| 6 own roads | MET | `slot.only(driver.card.roads)`. R5 (every open road again): 3 failed |
| 7 named failure | MET | `Isolated` keeps only the error class, never a message (`fleet/isolate.py:1-21`), so the "Not planned" line cannot carry one by construction. The plan is made once per session |
| Gates | MET | Trial merge c7e268605 with origin/main d6438bafa: ruff clean, format clean (2,648 files), imports clean (2,777 files), record scan clean (9,319 files). Full suite with the token kept: **16,758 passed, 13 xfailed, 0 failed** |

## Findings

1. **Should fix: a run that sealed its decisions and then stopped still reads as a quiet day.**
   - `SchoolFleet.run` seals the decisions, then makes the fills, settles and counts (`_finish`). An
     `AccountUnreadable` or `DashcamStuck` raised there returns `stopped: ...` with the decisions file already sealed
     (`runner.py:80-86`). The step is then `failed (school:STOPPED)`.
   - Criterion 5 renders any day with a sealed decisions file "exactly as before, whatever the run log says". I
     rendered that day with g's fakes: one sealed trade decision, no outcome or counts, the step `failed
     (school:STOPPED)`. It reads "Banner: AMBER, paper only / Trades closed: none / Counts (eligible / fillable /
     executed): none / Refusals and closures: none / Fleet total, rule drivers only: Rs +0", with no word of the failed
     step.
   - That is the dishonest empty case this story exists to remove, on the "ran and failed" path the orchestrator
     asked about. The stop alert reaches #fno-desk, but the report itself hides it [strong: rendered].
   - Fix: on a recorded day whose committed `school` step is not `ok`, add one line in the same words, "the daily
     run's school step was <status> (<code>): this record may be incomplete", and make the banner RED. A test: a sealed
     decisions file plus a `failed (school:STOPPED)` step shows the line and RED, never a bare "Rs +0". Criterion 5
     then reads "unchanged when the step is ok or missing (a manual run)".

## Answers to the orchestrator's two questions

- **Can a day the school did not run read as quiet?** No: no decisions file is always "No school record ..." in red,
  with the step's status and code, or "recorded no school step".
- **Can a day it ran and failed read as quiet?** Yes, if the failure came after the decisions seal (finding 1). Before
  the seal, no.
- **Does the 08:50 plan leak anything private?** No:
  - each plan line is driver, road, structure code and worst loss in rupees: MS-P1g's judged format, no strike or
    price (the real sample: SC, worst loss Rs 2,271 to Rs 9,373);
  - the failed-driver line holds the driver id, the failure and the error class only.

## Plants

8 planted. 7 caught: R1, R2, R3, R4, R5, R7, R8. R6 (a message in the failed-driver line) is moot by construction,
since `Isolated` stores no message. Each was run alone on `tests/school/reports` and `tests/school/fleet` (218 tests)
and restored after.

## Addendum 1

Round 2 of 2, at `f6af52752` (code `ff5846845`, main merged in at `eefeb96b5`). Verdict: **PASS**.

### Finding 1 (should-fix): fixed, my own evidence

`HowDidTodayGoSection._incomplete` now reads the step and `finished` (outcomes and drift both sealed at 15:00).
I rendered each case with `tests/school/reports/fakes.Day`:

| step | finished | banner and line |
|---|---|---|
| failed (school:STOPPED) | no | RED, "School run incomplete ...: the daily run's school step was failed (school:STOPPED); fills and outcomes not recorded." |
| failed (school:STOPPED) | yes | RED, "...; this record may be incomplete." |
| none | no | RED, "... recorded no school step; fills and outcomes not recorded." |
| ok | yes | AMBER, unchanged |
| none (a manual run) | yes | AMBER, unchanged |

My round 1 case (decisions sealed, then a stop in `_finish`) is now RED with the reason, never a quiet "Rs +0".
`FleetRunner._finish` seals OUTCOMES and DRIFT unconditionally (even when empty), so a normal finished day is
never flagged (the test `test_the_reader_s_finish_is_the_outcomes_and_drift_seals_even_empty` pins this).

### The builder's claim: a stopped run cannot feed the 08:50 plan: MET

`PreviousSlotToday._make` calls `plan_slot(previous, catalogue, snapshots, gate)`; `_proposals` adds
`RecordedSpotHistory(QUOTES_FOLDER).spots(...)` and passes `()` as the open positions. From `build_road_services`,
the catalogue and the snapshots are the recorded quote captures (`CaptureReader`, Drive-only quote store) plus
NSE's archived listings and lots. Nothing reads the dashcam, the books or the run log. A small correction to the
claim: the plan also reads the recorded 15:00 spot history, which is still capture data, not the school's record.

### Plants (each alone on tests/school/reports and tests/school/fleet, 226 tests, restored after)

6 planted, 6 caught:
- Q1, the RED becomes AMBER: 6 failed.
- Q2, `finished` is ignored: 2 failed.
- Q3, a not-ok step counts as ok: 2 failed.
- Q4, the two messages are swapped: 6 failed.
- Q5, the warning line is dropped: 6 failed.
- Q6, `finished` uses `any` instead of `all`: 1 failed.

### Gates (trial merge of f6af52752 with origin/main d12c4bcd2, FNO_SLACK_BOT_TOKEN kept)

- ruff check clean, ruff format --check clean (2,651 files), check_imports clean, check_records clean (9,330 files).
- pytest: 16,792 passed, 13 xfailed, 1 failed:
  - The failure is `tests/test_routine_setup.py::test_setup_repeats_over_system_packages_when_the_plain_install_fails`.
  - It is not this branch's: the branch touches neither that test nor `tools/routine_setup.sh`.
  - It passed 7 of 7 alone, then 3 of 3 under `-n auto` (one of those runs took 39 s against about 2 s, so it is
    load-sensitive).
  - Noted for the orchestrator, not counted against this story.

No blocking or should-fix finding is left.
