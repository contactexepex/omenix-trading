# Judge 149: G9, missed forecasts in protocol v4 (revision 9)

Independent judge, 15 Oct 2026. Branch `story/g9-miss-rule` at `8b6e2c24` (equals `origin/story/g9-miss-rule`);
base `origin/main` (5 commits behind, all logs, judge files and a data commit: no overlap). Story text
`docs/stories/G-forecasts.md` G9; claims `reviews/claude/response_148_g9-miss-rule.md`; owner rows of 15 Oct 2026
"Missed forecast days: verdicts on observed days only, with a miss cap" and "Test A stays undecided ..."
(`docs/DESK_DECISIONS.md:163,165`); response 147 item 2. Lane 1 (forecast scoring and the v4 protocol before its
freeze): correct.

## Verdict: FAIL (0 blocking, 3 should fix, 4 minor)

The rule itself is right and matches the owner's decisions: observed days only, misses counted from the first counted
forecast, 10% overall cap, 10% cap on baseline-observable 2% days with no miss below 10 such days, an
operations-undecided member never asks for thresholds, is never a claim and never futile, so Test A cannot become
"no". What fails: the "input failure" count is structurally blind to the commonest failure (a day neither file has a
row for), criterion 3's report and recorded-look outputs are not guarded by any test (three planted removals
survived), and the claims file skips quality rules 3, 4 and 6.

## Per criterion

| # | Criterion | Builder's claim | Judge's evidence | Result |
|---|---|---|---|---|
| 1 | Miss = resolved, non-void day with a baseline and no forecast, from the first forecast; neither = input failure, apart; unresolved and void neither | MET (`test_misses.py` first three tests) | Definitions in `fno/forecast_v4/misses.py:49-62` match. Hand recount of the builder's fixture (`test_misses.py:24`): 30 days, start day 5, so 25 counted; baseline missing on 15, so 24 observable; misses 12, 20 = 2; 2% days 12, 25 = 2, missed 1; input failure 15 = 1. Equals `MissReport(24, 2, 2, 1, 1)`. My own fixture through the real path (`paired_rows` then `compare`, 40 days, start day 4, unresolved 30, void 31 on a 2% day, null-row misses 7 and 15, a no-row miss 16, baseline-only-missing 20, both-null 11, and day 10 absent from both files): hand count 31 observable, 3 missed, 3 big, 1 big missed, input failures 2; code gives 31, 3, 3, 1 and **1**. Day 10 is invisible (finding S1) | PARTLY |
| 2 | >10% of baseline days, or >10% of baseline 2% days (any miss below 10), makes "undecided, operations": not judged, never a claim, never futile; Test A undecided | MET | Boundaries checked: tests at 10/100 and 11/100, 12/125 and 13/125, 9 with 0 or 1, 10 with 1 or 2, 25 with 2 or 3; my own exact-fraction sweep of `m > 0.10 * n` against `Fraction` for n = 1..20,000 at m = n//10 and n//10+1: 0 disagreements (no float edge). `look.py:56-57` returns NOT_JUDGED before any threshold call; `test_look.py` last test: `Recording` source gets no calls, member not judged, not futile, Test A "undecided". `stop_rule.py:47` needs every counted member futile, and NOT_JUDGED is `MemberResult(None, False, False)` (`look.py:29`), so "no" is impossible. Planted removal of `look.py:56-57` caught | MET |
| 3 | Every comparison and look prints the miss counts; protocol text and `terms.py` state the same numbers (test) | MET | Look lines: tested (`test_look.py:63`; planted removal of `look.py:46` caught). Protocol vs terms: tested (`test_protocol_text.py:35-37`; MISS_CAP, BIG_DAY_MISS_CAP to 0.20 and ZERO_BELOW to 5 all caught). Report text line (`render.py:43`), report JSON (`render.py:76`) and the recorded look JSON (`cli.py:65`): each removed in turn, **all 203 tests still pass** (finding S2). Real report run (scratch copy, `python -m fno forecast-v4-scores report --as-of 2026-10-15`) prints e.g. `misses: 0 of 1907 baseline days (0.0%), 0 of 94 2% days; input failures: 0` under each V6 comparison | PARTLY |

## Mutations planted (scratch copy from `git archive HEAD`; repo untouched)

Caught (16): look check removed; overall `>` to `>=`; zero-rule `<` to `<=`; 2% cap `>` to `>=`; 2% cap dropped;
start filter dropped; void kept; unresolved kept; input failures counted as misses; input failures forced to 0;
`_big_day` always false; look miss line removed; verdict text removed; MISS_CAP 0.20; BIG_DAY_MISS_CAP 0.20;
BIG_DAY_ZERO_MISS_BELOW 5.

Survived (5): zero-miss branch removed (`misses.py:38-39`; equivalent code, minor M1); `_big_day` `>=` to `>`
(`comparison.py:100`, minor M2); report text line removed (`render.py:43`), report JSON field removed
(`render.py:76`), recorded look JSON field removed (`cli.py:65`) (should fix S2).

## Findings

**S1 (should fix). Input failures are not counted when neither file has a row for the day.**
`miss_report` only sees `rows`, and `paired_rows` (`comparison.py:63-73`) makes one row per day *either file* holds.
A day the 3 pm capture never ran (no baseline row, no forecaster row) has no row, so it is neither an input failure
nor anything else; the report prints `input failures: 0`. Reproduced above (day 10). Rule forecasters write a
`not_eligible` row every day, so only those days are caught; a whole missed routine day, the most likely operational
failure after the freeze, is not. Criterion 1 and protocol section 4 ("counted apart", "every comparison and every
look prints ... input failures") are therefore not met on the real path. It cannot change a verdict (input failures
never count toward eligibility), but it makes the printed record understate failures. **Fix:** count from the
question's outcome days (`V4OutcomeSource.outcomes` has one entry per forecast day): pass the outcome day set into
`miss_report` and count each resolved, non-void outcome day on or after the first forecast with no row, or with both
values null, as an input failure. Test: a `paired_rows` fixture with a day absent from both files.

**S2 (should fix). Criterion 3's report and recorded-look outputs have no test.** Removing the miss line from the
comparison text (`render.py:43`), the `misses` field from the report JSON (`render.py:76`) or from the recorded look
JSON (`cli.py:65`, the permanent look record) leaves the suite green. Quality rule 4 and 5. **Fix:** assert the miss
line and the JSON `misses` in `tests/forecast_scoring_v4/test_records_and_report.py`, and the `misses` key in a
recorded look payload (a CLI or `_look` test with a frozen fake records store).

**S3 (should fix). Claims file misses quality rules 3, 4 and 6 (`docs/JUDGE.md`, "Quality rules").** No statement of
the independent code-review agents run and what they found (rule 3); no file:line per criterion with the proof that
its test fails when the code is broken (rule 4); no real output sample (rule 6). The sample is easy: the line above
from a real report run. **Fix:** add the three sections to `response_148_g9-miss-rule.md`.

**M1 (minor). The zero-miss branch is implied by the 10% rule.** For fewer than 10 2% days, "more than 10%" already
means any miss (1 > 0.1 n for every n < 10), so `misses.py:38-39` and `BIG_DAY_ZERO_MISS_BELOW` change no result
(planted removal survives, and must). Not wrong, and it mirrors the owner/ChatGPT wording, but the claims' "known
limit" presents the zero rule as an extra strict choice when it is simply what 10% means. **Fix:** either drop the
branch and constant and state in the protocol that the zero rule follows from 10%, or keep them with a one-line "why"
comment; correct the claims line either way.

**M2 (minor). The 2% day is defined twice.** `comparison.py:97-102` re-implements `regime.py:36`
(`abs(r) >= BIG_MOVE`); the `>=` boundary is untested (planted `>` survived). If one copy changes, the miss sub-cap
and the regime's 2% count disagree. **Fix:** one predicate in `regime.py` used by both, plus a test at exactly 0.02.

**M3 (minor). Test A wording.** The owner row title says Test A "stays undecided while a counted member is
undecided, operations"; the code (and the protocol, `PROTOCOL_v4.md` section 6, "yes" checked first) lets another
member's claim still give "yes". I agree with the code: response 147 item 1 and ChatGPT 112 argue only against a
false "no", and a claim is real evidence. State this reading explicitly in the claims so the owner sees it.

**M4 (minor). Process.** The story text was committed with the code in `46ba38a1`, not pushed alone and checked first
(quality rule 1), and it has no explicit gap list (rule 2). I checked the owner rows and response 147 items 1-2 myself:
every requirement is covered by a criterion except "a failing book is fixed or stopped by a separate operational or
budget stop", which the protocol mentions but the story's Out list does not name (it is BG1's). Also the owner row
says "proposed 10%"; the 2% sub-cap comes from response 147 item 2 (presented as accepted in the owner's final
review, not asked as a question). The v4 freeze record should quote the owner's confirmation of both numbers.
**Fix:** add the Out line naming BG1; note the numbers for the freeze record.

## Claims vs reality

| Claim (response 148) | Check | Holds? |
|---|---|---|
| `misses.py` new and pure, counts from the first forecast, misses, 2% days, input failures | Pure (no I/O); counts verified by hand twice; input failures incomplete (S1) | Partly |
| Three constants 0.10, 0.10, 10 in `terms.py` | `terms.py:72-74`; protocol test ties them | Yes |
| `Comparison.misses`; look not judged, never asks thresholds, never claim or futile, Test A undecided | Verified in code and by my mutations | Yes |
| Miss line in the look, the report text and both JSON outputs | Present in code (`look.py:46`, `render.py:43,76`, `cli.py:65`); only the look line is tested (S2) | Present, untested |
| 2% day uses the same input as the regime (`Outcome.log_return`) | Same input and same `>=`, but duplicated code (M2) | Yes |
| Protocol sections 4, 5, 6 state the rule | `PROTOCOL_v4.md` diff: section 4 bullets, section 5 "not judged at that look", section 6 Test A undecided; text matches code | Yes |
| Criterion 1-3 MET | 2 MET; 1 and 3 PARTLY | No |
| Full suite 5,553 passed on the merged tree | Re-run on the branch: 5,553 passed | Yes |
| ruff, imports clean | Re-run: `ruff check fno tests tools` all passed; `ruff format --check` 1,033 formatted; `check_imports.py` clean | Yes |
| V6 descriptive row not in code; G9 does not depend on it | `DESCRIPTIVE_ONLY` holds V7 only; descriptive check runs before the miss check (`look.py:54-57`) | Yes |
| Zero-miss rule "strict", can never cause a false "no" | Never a false "no": true. "Strict" choice: it is implied by 10% (M1) | Partly |

## Checks run

- `python -m pytest -q tests/forecast_v4 tests/forecast_scoring_v4`: 203 passed.
- `tests/test_code_size.py`: 1,072 passed. Changed files: `misses.py` 62, `look.py` 83, `comparison.py` 119,
  `terms.py` 88, `render.py` 88, tests 59 and 118 lines; all under 350.
- `ruff check fno tests tools`: all passed. `python tools/check_imports.py`: clean.
- Full suite on the branch (FNO_SLACK_BOT_TOKEN unset): 5,553 passed in 11 min 38 s (matches the claim; this branch is 5 commits behind main, none touching code).

## Project rules

- Design: pure counting module behind no new service; constants in `terms.py` (the v4 module's registered-terms file,
  as G6-G8 do); no new composition root needed. SOLID, KISS fine; DRY breach M2; redundant branch M1.
- No secrets, no outside service, no order path. No frozen file touched (`FREEZE_v4.md` does not exist yet; the G1
  and v2 freezes pin `fno/forecast/`, untouched).
- Owner fit: no more than decided (scoreboards and EQ2 left out, as the rows say); no less except S1's count.

## For the builder

Fix S1-S3 (and preferably M1-M2), then send the new SHA for a re-judge.
