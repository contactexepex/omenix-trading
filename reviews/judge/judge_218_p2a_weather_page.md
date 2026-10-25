# Judge 218: P2a part 1, the weather page (story/p2a-weather at b1a421a9)

**Verdict: FAIL, 1 should-fix.** Everything else in the page is right:
- the page rides the 07:10 run, with no new job;
- it reads M1's records through `WeatherRecords` only, and the 2% outcomes through G7's shared `big_move_outcomes`
  (no second outcome rule);
- it fails closed to `not_published` on every back-fill record (today's real state);
- it never sends a level, a `reaches` colour or the US cue.

Gates on a trial merge with origin/main: `-n auto` gives 6832 passed; `ruff check` and `check_imports` are clean.

## The orchestrator's three rulings

1. **The in-page Brier score is a second scorer: should-fix 1.**
   - `weather_parts._score` computes the mean Brier, `brier_baseline` and `skill = 1 − brier/base` of the live
     probabilities against the base rate and v0.
   - That is G8's job: `fno/forecast_scoring/v4/scores.py` already computes `mean_brier` and
     `brier_skill = 1 − Brier / base rate's Brier`, and the weather is scored on V6a and V6b there (M1's 26-week check
     reads G8's V6 scores).
   - Two scorers can disagree in their day set, their resolution rule or their rounding. One builder per function
     forbids it.
   - Today it publishes nothing, since there is no live record, so nothing is wrong on a screen yet. That makes it
     cheap to fix now.
   - **Fix:** `scores` shows `not_enough_data` with `brier`, `brier_baseline` and `skill` null, plus a reason saying G8
     has not scored live weather yet. When G8's committed report carries live V6 rows, the page reads them through one
     reader (the builder's own proposed swap). The builder's 10-day `scoring` threshold goes too, since G8's power
     rule decides that.
2. **The change to `test_p1_t1_card.py` is a correct move, not a weakening.**
   - The old test asserted that the bad enum value `new_reason` appears in the message, which is exactly the leak
     privacy rule 3 forbids.
   - The new test still fails the same bad record for the same reason (`payload/reason: breaks 'enum'`), and now also
     asserts that the value is absent. The strength of the check is unchanged and the leak is pinned shut.
3. **`ContractBroken` never prints a value: verified.**
   - `_violation` prints the path and `validator` name only.
   - Field names come only from `required` (missing keys) and `additionalProperties: false` (unexpected keys): keys,
     never values.
   - Under `anyOf`/`oneOf` it descends to the closest branch, so the message never falls back to jsonschema's
     `message`.
   - The new tests plant 987654.321 and "PURPLE-PLANTED", and neither appears.
   - No other `e.message` or `iter_errors` exists in `fno/`.
   - One limit, reasoning only: a path segment can be a map key where a schema uses
     `additionalProperties: {…}` (strategy names, symbols, universes in the stock schemas). No F&O screen schema uses
     a map, so no private value can sit in a path today. P2's later pages should keep it that way, and a test over
     the F&O schemas would pin it.

## Other choices the builder left open

- **Recent strip, red share and scores from live records only, not the back-fill: accepted.** 2.7.0's `recent[]`
  and `FnoWeatherScore` have no label, so back-fill colours would read as the real record. 2.8.0 adds the labels
  (judge 217), and the back-fill can show then.
- **The drivers' definition** (each changed v0 input's value in words, `push` the sign of the change, ordered by
  |change| / median |change| over 250 records): this matches W3 rule 4 and carries no level. Accepted.
- **The rest:** `model_version` is the record's `operative`, `intraday` is empty and `price_of_calm` is
  `not_measured_yet`, all honest.

## Addendum 1: P2a at 62259e1f (response 224 addendum 1)

**Verdict: PASS.** Should-fix 1 is closed.

- **The scorer is gone.** `scores()` is now a constant list: each question and yardstick `not_enough_data`, with
  `n_scored` 0 and `brier`, `brier_baseline` and `skill` null. Its docstring names G8's `scores.py` as the only
  scorer and the reader that replaces it. No Brier arithmetic is left (`statistics` is now used only for the
  drivers' median change).
- **The reason line** stays in code because 2.7.0's `FnoWeatherScore` has no reason field, which is acceptable.
- **The map-key note** is pinned: `FnoPicks.baskets` is the only map in the F&O screens and a test holds it empty.
  `us_overnight` gets its page-side test.
- **Gates on a trial merge with origin/main:** `-n auto` gives 6830 passed and 4 failed. All 4 are
  `test_routine_gate.py`'s shard-count check, caused only by my trial merge leaving `reviews/claude/README.md`
  unmerged: a conflict between the branch's response 224 row and main's response 225 row, so the file was listed
  twice. Plain main passes the same file (17 passed).
  - **For the merge:** resolve `reviews/claude/README.md` keeping both rows, then run the full suite on the merged
    tree.
  - `ruff check` and `check_imports` are clean.
