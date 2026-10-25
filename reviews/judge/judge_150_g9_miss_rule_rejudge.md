# Judge 150: G9 re-judge, missed forecasts in protocol v4 (revision 9)

Independent judge, 15 Oct 2026. Branch `story/g9-miss-rule` at `2521c1e1` (equals `origin/story/g9-miss-rule`);
`git diff origin/main...HEAD` (main `575e7c9c`) touches only G9's 18 files (code, tests, protocol, story, claims,
judge 149). Builder's answer: `reviews/claude/response_148_g9-miss-rule.md`, section "Revision 2". Same method as
judge 149: hand recounts, mutations on a scratch copy (`git archive HEAD`), full suite with FNO_SLACK_BOT_TOKEN unset.

## Verdict: FAIL (0 blocking, 1 should fix, 2 minor)

Every judge 149 finding is fixed, and each fix is proven by a planted break. The builder's extra fix (misses after
the freeze count from the day after it) is right in substance. What fails: that fix has two branches, and only one
of them is tested. If you delete the late-starter branch, all tests still pass (finding S1). It is a one-test fix.

## Judge 149 findings, re-checked

| # | Builder | My check | Result |
|---|---|---|---|
| S1 input failures on days neither file holds | `comparison._with_empty_days` (`comparison.py:97-101`) adds an empty row per outcome day no file holds, only for the miss count | My judge 149 fixture (40 days, day 10 absent from both files) now gives `input_failures=2`, matching my hand count (31, 3, 3, 1, 2). Pairing is unchanged: `compare` still pairs `rows`, and `test_miss_outputs.py` asserts `missing_forecast == 1` and 8 scored. Planted break (removing the call) is caught | Accepted |
| S2 outputs untested | `test_miss_outputs.py`: report text, report JSON, recorded look through `cli._look` with a frozen fake store | I removed `render.py:43`, `render.py:76` and `cli.py:65` one at a time; each is now caught | Accepted |
| S3 claims lack rules 3, 4, 6 | Sections added | Present. The rule-6 sample is the line I produced in judge 149. I checked its "0 null rows after the first forecast" claim against the committed CSVs: first `ok` row at index 250/500/501/504/505, and 0 non-ok rows after it, for all 8 V6 files | Accepted |
| M1 zero-miss branch redundant | Branch and `BIG_DAY_ZERO_MISS_BELOW` dropped; `misses.py:37` is one expression; protocol says the zero rule follows from 10% | `test_misses.py` `BIG_DAY_CASES` (9 days with 0 or 1 miss, and so on) still pass. `test_protocol_text.py:35-37` ties the protocol to the code. Story "Expected design" now says two constants | Accepted |
| M2 2% day defined twice | `regime.is_big_move` (`regime.py:32-34`), used by `window_regime` and `comparison._big_day` | Tests at exactly ±0.02 and ±0.0199. Planted breaks (`>`, no `abs`, `_big_day` bypassing the predicate) are all caught | Accepted |
| M3 Test A reading | Stated in the claims | Matches `stop_rule.py:45-49` | Accepted |
| M4 Out line, freeze numbers | Out names BG1's operational and budget stop; claims note that the freeze record must quote the owner on both 10% numbers | Present (`G-forecasts.md` G9 Scope) | Accepted |

## The builder's extra fix (miss start after the freeze)

- The problem was real. `_counted` (`scoring.py:77-78`) keeps only live rows after the freeze. So under the old code,
  a member that broke straight after the freeze started its miss count at its first later forecast, and the broken
  days counted as nothing. That is the "gain by skipping days" the story forbids.
- The fix: `_miss_start` (`scoring.py:81-87`) is `max(first forecast in any row, back-fill included, freeze + 1 day)`.
  `miss_report(..., start)` counts from it, and `_with_empty_days` supplies the days no file holds.
- `_miss_start` cases I ran myself:

  | Case | Result |
  |---|---|
  | Started before a 10 Jan freeze (back-fill row) | 11 Jan |
  | Late starter, first forecast 20 Jan | 20 Jan |
  | Only null rows | None |
  | No freeze | None |

  All are as the protocol says.
- Builder's test `test_after_the_freeze_misses_count...`, recounted by hand:
  - The freeze is 2 Jan, so the counted days are 3-10 Jan: 8 observable.
  - Missed on 3-5 Jan: 3.
  - 2% days: 7 and 8 Jan are 2% days; 3 Jan (1.99%) is not. So 2 observable, 0 missed.
  - 3/8 > 10%, so the member is undecided. Matches the test.
- **Owner fit (reasoning only).** The owner row says misses are "counted from the slot's first counted forecast". For
  a member that had already started, the fix counts from the day after the freeze instead. I accept it: the row's
  purpose (keep warm-up days out of the misses) still holds, and a member running before the freeze has no warm-up
  left. It can only make a member "undecided, operations", never a claim or a false "no". It is disclosed in
  protocol section 4, so the owner sees it at the freeze.

## Mutations (25 planted, 23 caught)

Caught:
- Empty days removed; empty days given a baseline.
- `is_big_move` `>`; no `abs`; `_big_day` bypassing the predicate.
- Miss start: ignored in `miss_report`; not passed from scoring; set to the freeze day; computed from counted rows
  only.
- Caps: 2% cap removed; overall `>=`; 2% `>=`; MISS_CAP 0.20; BIG_DAY_MISS_CAP 0.20.
- Look check removed; look line removed; report line removed; report JSON removed; recorded look JSON removed.
- Counting: void kept; unresolved kept; input failures forced to 0; start filter dropped.

Survived:
1. `scoring.py:87` `max(min(given), after + 1 day)` changed to `after + 1 day` (finding S1).
2. `_with_empty_days` drops the void flag (`comparison.py:101`; minor M1).

## Findings

**S1 (should fix). The late-starter branch of `_miss_start` is untested.**
- Changing `scoring.py:87` to always return the day after the freeze passes all 208 G9 tests.
- With that break, a slot whose first live forecast comes 30 days after the freeze (a new AI slot, say) would get 30
  misses before it ever ran. It would show as "undecided, operations", against the owner row ("counted from the
  slot's first counted forecast") and protocol section 4 ("else from its first forecast").
- Quality rule 5 asks for every case of a criterion.
- **Fix:** add a test with no row before the freeze and a first live forecast several days after it. The miss count
  must start at that forecast (0 misses on the earlier days).

**M1 (minor). The void flag on empty days is untested.** Dropping `o.void` in `_with_empty_days`
(`comparison.py:101`) passes. A void day that neither file holds (for example, a V1 day whose intraday RV is missing)
would then count as an input failure instead of nothing. Report only; no verdict changes. **Fix:** add a void outcome
day to `test_miss_outputs.py` with no rows, and assert it is not an input failure.

**M2 (minor, note only). `tests/books/test_paper_account.py` fails on main.**
- The builder said it fails on main too. I confirmed it on a scratch copy of `origin/main` `575e7c9c`: 1 failed, the
  committed starting state (capital 2,000,000 against the test's 500,000).
- G9 touches no books file, so it is not G9's.
- It must be fixed on main (E1 top-up work) before any merge: CLAUDE.md merges a lane-1 branch only with the full
  suite run on the merged tree.

## Checks run

- `python -m pytest -q tests/forecast_v4 tests/forecast_scoring_v4`: 208 passed.
- `ruff check fno tests tools`: all passed. `ruff format --check`: 1,046 files formatted.
  `python tools/check_imports.py`: clean.
- Sizes: `scoring.py` 101, `comparison.py` 126, `misses.py` 64, `regime.py` 49, `test_miss_outputs.py` 99 lines; all
  under 350.
- Full suite at `2521c1e1` (FNO_SLACK_BOT_TOKEN unset): 5,690 passed, 1 failed (the main-side books test of M2, the same one failing on origin/main), as the builder reported.

## Project rules

- Design: the miss start is computed in the scoring service (which owns the freeze cut) and passed into the pure
  `miss_report`. Cohesive. The one shared 2% predicate fixes judge 149's DRY breach. No new constants outside
  `terms.py`. No secrets, outside services or order paths. No frozen file touched (`FREEZE_v4.md` does not exist).
- Owner fit: as judge 149, plus the freeze-start rule accepted above.

## For the builder

Add the S1 test (and preferably the M1 test), then send the SHA. A re-check of S1 and M1 alone will do.

## Addendum 1: narrow re-check of S1 and M1 (15 Oct 2026)

**Verdict: PASS.** No blocking, should-fix or minor findings left for G9. This addendum covers:

- **The new tests:** commit `988166e2`, the only commit since `2521c1e1` that changes a file outside the judge
  docs. It adds 21 lines to `tests/forecast_scoring_v4/test_miss_outputs.py`.
- **The merges:** `c77163b1` and the branch tip `25ccb17e` are merges of main. Neither touches any G9 file: the
  `git diff 68f42552 25ccb17e` over `fno/forecast_v4`, `fno/forecast_scoring/v4`, both test folders and
  `research/forecasts` is empty.

**S1 (late starter): fixed.**
- What the test checks: `test_a_member_that_starts_after_the_freeze_counts_misses_only_from_its_first_forecast`.
  The freeze is 2 Jan and the forecaster has no rows before 6 Jan.
- Hand recount:
  - Counted days are 6-10 Jan: 5 observable, 0 missed.
  - 2% days are 7 Jan (+0.02) and 8 Jan (-0.02): 2 observable, 0 missed.
  - So the expected result is `MissReport(5, 0, 2, 0, 0)`, which is what the test asserts.
- Breaks I planted on a scratch copy, both caught by this test:
  - `scoring.py:87` changed to always return the day after the freeze (the break that survived in judge 150).
  - `min` used in place of `max`.

**M1 (void day neither file holds): fixed.**
- What the test checks: `test_a_void_day_neither_file_holds_is_not_an_input_failure`, on a resolved void outcome.
- The builder is right to use `Outcome(True, True, ...)`. With a value of None the day is unresolved and the break
  hides.
- Hand recount:
  - Day 5 is void, so it is excluded.
  - Of the other 9 days, all have a baseline: 9 observable, 1 missed (7 Jan).
  - 2% days: 2, of which 1 missed.
  - Input failures: 0.
- Breaks I planted, both caught:
  - `o.void` dropped in `comparison.py:101`.
  - void forced to True.

**M2 (main's books test): resolved by main.**
- The fix `dde9470` is now on `origin/main`, and the branch tip merges it.
- Trial merge in a scratch git worktree: `origin/main` `2355b80b` plus `68f42552`. Its code equals the tip
  `25ccb17e` code, since main's later commit `32361574` adds only logs and judge files.
- Result: **5,787 passed, 0 failed** (FNO_SLACK_BOT_TOKEN unset).
- The only conflict was the `reviews/claude/README.md` index (responses 111 and 148 rows): keep both.
- `origin/main` has since moved to `8160e992`, so the merge itself still needs the usual pull and full suite on the
  merged tree.

**Other checks:**
- `tests/forecast_v4` and `tests/forecast_scoring_v4`: 210 passed.
- `ruff check fno tests tools`: clean; the test file is formatted.
- `python tools/check_imports.py`: clean.
- `test_miss_outputs.py` is 120 lines.

**Still to do outside G9:**
- The v4 freeze record must quote the owner confirming both 10% numbers (judge 149 M4).
- The freeze-start reading (judge 150) is disclosed in protocol section 4.
- The quality-rule-8 end-to-end dry run after the merge is the orchestrator's.
