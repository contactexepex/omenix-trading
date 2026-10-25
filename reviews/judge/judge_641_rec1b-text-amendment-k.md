# Judge 641: REC1b text amendment, `story/rec1b-daily-record` at 6460a4ce3 (on 1daf19e1; round 1 of 2, judge K, one judge)

**FAIL, lane 1** (the recommendation record; a #fno-desk post), text only. 2 should-fix, 2 minor. Judged by reading.

The amendment `1daf19e1..6460a4ce3` touches `docs/stories/REC1-recommender.md` alone (+57/-14). Doc-reading tests
on 6460a4ce3, Slack token set: 922 passed, 14 xfailed. The three channels have no post from 00:21 UTC on.

## Checks (the orchestrator's five)

| Asked | Verdict | Own evidence |
|---|---|---|
| Timing independent of market hours | MET for `recommend`; **not** for its school input (SF2) | `DAILY_RUN_STEPS` on the branch: `... card, price_distribution, premium_ranges, school, ...`. The new step goes after `school` and before `candles` (the only later wait, 15:33), so it never waits. The text says it reads sealed records only and is never refused after 15:30 |
| Can an unavailable source look complete | **YES** (SF1) | see below |
| Schema change safe with no record | MET | `fno/recommend/` is not on main (`git ls-tree origin/main`: none), and `config.yaml` has no `recommend` live key, so no record can exist. Adding the required `candidate_sources` before the first write keeps version 1 honest |
| The #fno-desk line leaks nothing | MET (see m2) | the sample holds answers, reason codes, counts, the receipt path and a 12-character hash prefix; criterion 10 scans the line against the record's private fields |
| Card byte-identical | MET | `git diff origin/main 6460a4ce3 -- fno/cards` is empty; `fno/cards/wiring.py` has left REC1b's file list; the card runs before `recommend` and reads nothing of it; criterion 10's golden file covers the step on and off |

## Findings

1. **Should fix: "complete" is not defined, and today's school step is `ok` while it ran nothing.**
   - With `school.enabled: false`, which is the value in `config.yaml` on this branch, `school run` prints "school off" and exits 0. The step is then `ok`, with reason `school:OFF` (`fno/daily/reason_codes.py:103-108`).
   - The text says a source is `complete`, or `unavailable` "with the source step's status (for example not_live, failed, refused, frozen)". Read by status, an `ok` school step that did not run is complete, with no candidates. That is the empty complete list the ruling forbids. The same holds for `school:NOT_A_SESSION`.
   - **Fix (text):** define `complete` positively: the step is `ok` and the source's own record shows it ran.
     - The school: `SessionRun.status == ""`, and its sealed decisions are read and hash-checked.
     - `desk:book1`: Book 1's decision record is present and hash-checked.
     - Anything else is `unavailable`, with the step status and its reason code. That covers `ok` with `school:OFF`, `not_built`, `exercised`, and a step missing from the run log.
     - Add the plant "school off read as complete".
2. **Should fix (text): the stated timing implies the school is refused.**
   - The school step is `StartsBy(..., SCHOOL_STARTS_BY)`, and `SCHOOL_STARTS_BY = 15:25` (`fno/daily/wiring.py:37`, `school:TOO_LATE`).
   - Section 1 puts the record at 15:27-15:30, after the school's 77 s, so the school would start at about 15:26 or later. That is after its own start limit.
   - With GW1 moving the desk's fills later (judge I's finding), the school source would be `unavailable (refused)` on most days. The record would handle that correctly, but the ruling's purpose would be lost.
   - **Fix:** state the dependency, and correct the estimate. The orchestrator should settle GW1's new `fills_by` against `SCHOOL_STARTS_BY` before REC1b's code is written. REC1b's own code need not change.

## Minor

- **m1:** "an unavailable source that holds a rung-3 version" must say where that is read from: the version's rung records, never the source that could not be read.
- **m2:** the line and the card answer side by side in #fno-desk (card: "NO TRADE (no_approved_strategy)"; line: "Paper: NO TRADE (no_established_version)"), and later they can differ (a `PAPER_TRADE` line beside a NO TRADE card). Say in the line which one it is. Also say whether `ELIGIBLE_FOR_YOUR_OWN_REVIEW` names the version in the line. A version ID is not an internal, but the text should state it.

## For round 2

All four are text only: the definition of `complete` (with its plant), the timing line, and two sentences.

## Addendum 1: T1g read alongside (main at 8ebb0c3f4, judge K)

**Not yet in agreement: the footer is fixed, two lines are not.**
- **Fixed:** T1g's closing `**Depends:**` (`docs/stories/T-cards.md:1528`) now reads "the card-side REC1 step (deferred, 25 Oct; REC1b posts its own #fno-desk line instead)", which matches the REC1b amendment.
- **Still old (line 1341):** T1g's header still says "Depends on: REC1b (the recommendation record and `RecommendationStatus`), T1e, T1f".
- **Still old (line 1358):** its context still says "REC1b replaces T1's `RegistryStatus` with `RecommendationStatus` inside `RuledStatus`".
- **Fix (lane 3 for the owner of T1g; no judge needed for the wording):** both lines name the deferred card-side REC1 step, as the footer does. The two texts then agree. Nothing else in T1g depends on REC1b's card change.

## Addendum 2: round 2 (the last), the text commits a0b8ea661 and ed8dc6180 (judge K)

**PASS, lane 1, text only.** 1 minor. I read only the text change, `git diff 6460a4ce3 ed8dc6180 --
docs/stories/REC1-recommender.md`; the code commits e94a51fa0, c3fbf5e12 and 9d7a6b180 were not judged here. Doc-reading tests on ed8dc6180, Slack token set: 922 passed, 14 xfailed. No post in the
three channels from 00:26 UTC on.

| Finding | Verdict | Evidence (read) |
|---|---|---|
| SF1: `complete` undefined | fixed | defined positively: for `school`, `SessionRun.status == ""` and every sealed decision hash-checked; for `desk:book1`, its decision record present and hash-checked. `ok` with `school:OFF` or `NOT_A_SESSION`, `TOO_LATE` and every other status is `unavailable` with status and reason code, and "an `ok` status alone never makes a source complete". There is a new plant for "school off read as complete" |
| SF2: the timing | fixed (m3) | the chain is written out, under the school's own `SCHOOL_STARTS_BY` 15:25. A refused school is `unavailable`. The check that the school still starts before 15:25 after GW1 is named and given to the orchestrator |
| m1: where rung 3 is read | fixed | from the version's own rung records, never the unread source |
| m2: the line beside the card | fixed | "Recommender (not the card)"; the two can differ; `ELIGIBLE` names the version, "for your own review, never a buy" |
| `frozen` removed | correct | O1's statuses are `ok`, `failed`, `refused`, `not_live`, `exercised` and `not_built` (`fno/constants_operations.py`); there is no `frozen` |

**m3 (minor, needs no new round):** "the school step ... starts about 15:19-15:23 (21-23 Oct)" was measured with the old
capture end. On 23 Oct the run log shows `fills` at 15:17:51 and `quotes_done` at 15:18:28 (`journal/runs/2026-10-23.json`).
With E3 now asking from 15:17 and ending about 15:20, the same steps start about 2.5 min later, so the school starts
about 15:21:30-15:25:30. The top of that range is at its 15:25 limit. The orchestrator's confirmation with GW1's
builder is the right check. When it is done, the measured start belongs in the text.
