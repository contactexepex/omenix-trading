# Judge 555: T1c, the card shows M1's live weather record

**Scope:** story/t1c-card-weather at e30ab3d0 (builder session_0145TfSwzmpk6MBrH92f5h4G), diff eb9cff07..e30ab3d0;
claims in `reviews/claude/response_333_t1c-card-weather-code.md`. Judge I (session_01MvZneCLZqBuiGyNxawdVee). Lane 1.
Round 1 of 2.

**Verdict: PASS.** No should-fix. 3 minors (untested or redundant guards that M1's writer cannot trigger) and 2 text
minors; none blocks.

## The orchestrator's list
| # | Check | Result | Evidence |
|---|---|---|---|
| a | The card reads M1's committed live record by M1's contract | MET | See "(a) Reading M1's record" |
| b | Every case without a scored live reading shows no colour and keeps "No new trades ..." | MET | See "(b) Every unscored case" |
| c | The two amendments to judge 401's text | BOTH ACCEPTED | See "(c) The amendments" |
| d | The reported full-suite failure | NOT REPRODUCED | See "(d) The full-suite failure" |
| e | Money piece, second judge? | NO [reasoning only] | See "(e) One judge" |
| - | Gates on e30ab3d0 merged with main | MET | Full `pytest -n auto` 14,800 passed, 15 xfailed, 0 failed; ruff check and format, check_imports and check_records clean. The largest new file is 171 lines (the test) |

### (a) Reading M1's record
- **The path:** `RecordedWeather` takes it from `WeatherRecords(folder).path(day)`, so it has one source (`wiring.py:58-64`).
- **The bytes:** the card reads the committed bytes through `CommittedRecords`. It does not use `for_day`, which reads the working tree. That is the story's agreed split: an uncommitted record must read as no weather. Parsing is the same `json.loads`.
- **The checks, in order:**
  1. `day` equals the card's day.
  2. `label == LIVE` (M1's own constant).
  3. `status == "scored"`.
  4. `colour` in GREEN, AMBER, RED: M1's `colour` is the operative colour (`fno/weather/day.py:75,83`).
  5. The operative forecaster's chances and the base rates are `ok` and in [0, 1].
- **No driver is read,** so the private US flag stays out.
- **Minor (text):** M1's `records.py` docstring still calls `for_day` "the card's reader". The card is right to read committed bytes; M1's docstring is stale.

### (b) Every unscored case
23 planted, 20 caught. Each plant below removed one protection, and a test failed:
- the day check;
- the label check;
- the colour check;
- the missing-chance check;
- the "No new trades" line dropped from a blocked section;
- the `missing` name dropped;
- the range and upper-bound checks;
- the bool check;
- a bad JSON file raising instead of reading as no record;
- the not-a-dict check;
- the RED line removed, and the RED line added to AMBER;
- `NO_REASON`;
- the record left out of the SHA-256 footer;
- the guard's extra line in `card.py` (a weather source that raises keeps the block);
- whole percents, the base rate read from the operative, the wrong question for p5;
- the absolute path in the wiring.

**Real dry runs** (`card daily --on <d>`, no `--post`, nothing written; `git status` clean):
- 23 Oct: GREEN, chances 2.9% (2.7%) and 12.9% (10.4%), v0 AMBER. The record is listed with SHA-256 482e2676..., which matches `sha256sum`.
- 22 Oct: GREEN, 2.8% (2.7%).
- 14 Oct: "no live reading ... the record is backfill_exploratory", plus the block line.
- 21 Oct, no record: "no reading", the block line, and "Missing: weather record for 2026-10-21".

**The 3 survivors are minors.** None is a defect on the wired path, because M1's `Value` never carries a value with a non-`ok` status (`forecast_v4_rules/baselines.py:29-33`). M1's `_status` is also built from those same values, so a hand-written record would be needed to reach any of these guards:
1. **`status != SCORED` removed:** survives. A not-scored record also has no chances and a "not scored" colour, so the other checks block it with the same reason. Only a record with status "not scored:..." but GREEN and valid chances would show the difference. Fix: one test with such a record.
2. **The entry's `status == "ok"` removed:** survives for the same reason. Fix: one test with a valid value whose status is not ok.
3. **`math.isfinite` removed:** survives, and it is truly equivalent. NaN and ±inf already fail `0 <= value <= 1`. Fix: remove it as redundant (KISS), or keep it and name it as belt and braces.

### (c) The amendments
1. **A back-fill is never today's weather: ACCEPTED.**
   - M1's back-fill stops before the first live record (`first_live`), so a non-live record for a card day is history recomputed later, not a reading known at 14:30.
   - Showing it as the day's colour would be look-ahead. Blocking fails closed and matches the owner's "4 A".
   - Real check: 14 Oct's `backfill_exploratory` blocks.
2. **Chances with one decimal: ACCEPTED** [some evidence].
   - On 23 Oct, 0.02933 and 0.02667 both show as "3%" in whole percents, which hides that the model is above the base rate. One decimal shows 2.9% and 2.7%.
   - [reasoning only] The second decimal is not real precision: the base rate is about 20 of 750 sessions (standard error about 0.6 points), so the owner should not read 2.9 against 2.7 as a meaningful gap. The colour, not the decimals, carries the decision.
   - Display only; no rule reads these strings.
- **Minor (text):**
  - Design item 1 lists "a record that is not `live`" under "Weather: no reading for <d>" with missing "weather record for <d>". The code (and criterion 5) shows "no live reading ..." with missing "live weather record for <d>". Align design item 1 with criterion 5.
  - The story's Status line still says "waiting for the judge (Judge E)".

### (d) The full-suite failure
Not reproduced, and no flaky test found.
- My full run on the merged tree: 14,800 passed, 0 failed.
- 5 more runs of `tests/cards tests/weather tests/e2e_acceptance tests/learning` with `-n auto`: 222 passed every time.
- The only test reading the repository's real git state (`GitHeadRecords` on the committed 14 and 23 Oct records) reads HEAD and writes nothing.
- The builder's failure stays unnamed, so I cannot rule out a flake elsewhere in the suite. It is not in the card or weather area.

### (e) One judge
[reasoning only] Not a money piece under JUDGE.md "Two judges for money pieces" (money, limits, fills, exits, safety laws):
- The card's status is always NO TRADE in v1.
- The "No new trades" line is advice to the owner. Enforcing it at the entry gate is out of this story (its own story).
- Nothing outside `fno/cards/` reads the weather section; only `fno/learning` imports card code, for health.
- The story that makes the desk block on the weather will touch a safety rule and should get two judges.

## Addendum 1: the minors, story/t1c-followups at 8f462a97 (diff against main: 3 files)

**Verdict: PASS** (Judge I).

- **Survivor 1 (the `status` check): FIXED.** `test_a_record_not_marked_scored_is_never_shown_even_with_a_colour_and_full_chances`. My plant (the check removed) now fails 1 test.
- **Survivor 2 (the entry's `status == "ok"`): FIXED.** `test_a_chance_whose_entry_status_is_not_ok_is_never_shown_even_with_a_value`. My plant now fails 1 test.
- **Survivor 3 (`math.isfinite`): REMOVED**, with the reason in a comment. NaN still fails closed (my plant letting NaN through fails 1 test).
- **Minor:** no test holds a chance of `inf`. My plant letting inf through survives (103 passed). The code is right: `0 <= inf <= 1` is false. A test with `float("inf")` would pin it.
- **Text minors: FIXED.**
  - Design item 1 now gives criterion 5's not-live line and missing name.
  - The Status line reads done.
  - M1's `for_day` docstring is M1's and stays with M1's owner.
- **Gates (my run on 8f462a97 merged with main):** full `pytest -n auto -rf` 14,871 passed, 15 xfailed, 0 failed; ruff check and format, check_imports and check_records clean.
