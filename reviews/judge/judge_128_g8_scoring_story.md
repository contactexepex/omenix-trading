# Judge 128: G8 story text (protocol v4 scoring, comparisons and the two looks), rule 1

**Verdict on b987988dcff0415cfb6316487f9ec43c8a8641a6 (`story/g8-scoring`, response 126): PASS.** No findings.

Applied: `docs/JUDGE.md` rule 1; the owner's 15 Oct rule (real cases only); the "signal, trade or stop?" rule. G8's look
feeds Test A, a stop decision, so I checked every rule it names against protocol v4 sections 4-6 and the calibration
file.

| Point | Result | Evidence |
|---|---|---|
| Calls `fno/forecast_v4` and never re-implements it | Yes | Every rule is named as a call: pairs, loss, `calibrated_p`, `futility_p`, `judgeable`, the bootstraps, `judge_family`, `window_regime`, `forecasting_test`, `power_report`, `terms`. |
| Threshold tools and their arguments | Correct | `tools/v4_claim_thresholds.claim_threshold(question, n, rate, ...)` takes the look's rate and divides by 15 itself (its docstring says "rate / 15"), so passing the look rate is right. `tools/v4_futility_study.futility_threshold(question, n)` and `tools/v4_brier_bands.operative_thresholds(question, n, band)` exist with those signatures. |
| Claim on the scored set, futility on the gate set | Matches the protocol | Section 5.3 sets claims on the scored set; `PROTOCOL_v4_calibration.md` section 2 defines F+D "on the gate set". Each threshold is called at its own set's n. For Brier questions the two sets are the same. |
| Both gates at every look; the crash cut (decision 69) | Correct, boundaries right | The owner's item E row (`DESK_DECISIONS.md`, 15 Oct: option 2, more than 10% 2% days gives no verdict) is real. `big_days / n > 0.10` is strict: at n = 125, 12 days (9.6%) are judged and 13 (10.4%) are not; at n = 250, 25 (exactly 10%) are judged and 26 are not. Criterion 4 tests all of these and the 4/5-day gate. A not-judged member gets p = 1 and stays open, never "no", as 5.7 says. Putting `crash_dominated` beside `judgeable` in `confirmatory.py` freezes it with the protocol. The section 11 E line is correctly named as a dependency of the G6 freeze commit. |
| The family, V7, Test A | Match 5.6-5.8 and 6 | 15 members from `terms.FAMILY`, all printed with look, rate and timestamp. V7 is fixed at p = 1. A member closed at look 1 is not judged at look 2. With no registered slot, Test A is "undecided", never "no". Seeds: k is the member's 1-based place; reported comparisons are numbered after 15, as 5.2 says. |
| Outcomes from G7's `series.py` | Consistent with G7 at 992440f | One place per rule. V1 reads A16's `rv/` rows, where status `ok` is an outcome and `void` is void (A16 writes exactly `ok`/`void`). A16b's `rv-candle/` is never read. V7 reads `vix_closes()`, which G7 now provides. |
| The naming item | Settled | G8 looks forecasters up by `fno/constants.py` ids. G7's revision uses the same ids (`ewma_094`). No primary baseline uses EWMA. |
| Before the freeze | Safe | Every output is EXPLORATORY and `look` writes no record. After the freeze, a record is written once and never overwritten (criterion 8). V4, V5 and Test B are out of scope with reasons. |
| Real fixtures | Yes | The 2024 skip cases (20 Jan special, 1 Nov muhurat) are real rows of `warmup_closes.csv`, as I checked for judge 127. |

Not checked here: the code (G8's own lane-1 check). For the freeze, the G7 and G8 file hashes go into the record only
after both codes pass.

## Addendum 1 (15 Oct 2026): G8 code at 5c3d6fcdbb513796ac0a64c284a79de4bfa5c9b5

**Verdict: FAIL.** There is one should-fix, plus a gate failure that belongs to G7 (2 of 5,067 tests) and blocks the
merge anyway. The rest of G8's own diff, 1,588 lines over the G7 merge be7f166, matches the story.

**Gates, run by me.** 5,065 passed and 2 failed, both in `tests/forecast/test_freeze_v2.py`: G7's edits to the
v2-frozen `fno/forecast/baseline_wiring.py` and `cli.py`, which the builder and orchestrator already named. G8
cannot merge until G7 moves its wiring. ruff, format and check_imports are clean.

**Should-fix: a registered V7 member crashes the look.**
- `look.member_result` asks the threshold source for every registered member whose window passes the batch and
  2%-day gates. V7 is in the family (three slots, protocol 5.6) and is descriptive-only (`terms.DESCRIPTIVE_ONLY`;
  `judge_family` discards its result).
- But `FrozenToolThresholds` sends V7 to `tools/v4_brier_bands.operative_thresholds`, whose `QUESTIONS` table holds
  V6a and V6b only. My call `FrozenToolThresholds(Path('tools')).thresholds('v7_vix_higher_in_5_sessions', ...)` on
  this SHA raised `KeyError: 'v7_vix_higher_in_5_sessions'`.
- The real path: the freeze's ledger row registers a forecaster for a V7 slot (any book that forecasts V7). Then
  `forecast-v4 look` at the stop review raises before Test A prints, and the stop decision has no look output.
- The test `test_no_registered_member_gives_undecided_and_v7_stays_at_p_1` passes only because it uses a recording
  fake source.
- Expected fix: `member_result` returns NOT_JUDGED for `DESCRIPTIVE_ONLY` questions before any threshold call, and a
  test runs a look with a V7 member through a source that would fail if asked.

**Checked and correct.**
- **Crash cut.** `crash_dominated(event_days, n)` is `event_days > 0.10 n`, beside `judgeable`, with the boundary test.
  `member_result` applies batches, the 5-day gate and the cut before any threshold call.
- **Thresholds.** Claim at the scored n and the look rate (the tool divides by 15 itself); futility at the gate n.
  Brier claims come from the band's per-look entry.
- **Look 2.** It reads look 1's record and closes claims and futile members only; "real but too small" stays open,
  as 5.8 says. The look record is write-once (`LookRecordExists`).
- **Outcomes.** V2/V3 sums of close-proxy `RV_s` over the next h regular sessions; V7 strict `>`. V1's `void` row is
  a void outcome. A horizon past the data has no entry. The regime uses the outcome's first-session VIX and return.
- **V1's primary.** It switches one way via `eligibility.primary_baseline`.
- **Exploratory number.** My own independent rebuild of V6a `v6_ewma_t4` against the 750-day base rate, from the
  committed closes with d-1 inputs, gives Brier skill 0.1449 on 1,908 days. The builder's 0.145 is right.

**Note (not a finding).** A V1 forecast day whose next session has no A16 `rv/` row at all, because the recorder did
not run, stays "unresolved" instead of "void". Both are left out of the scored set; only the counted reason differs.

## The power report question (orchestrator): real, a property of protocol v4, not a G8 call error

- **The arithmetic is right.** `power.required_outcomes` is `n = ceil(((z(1 - 0.03/15) + z(0.80)) x r)^2) = ceil(13.837
  x r^2)`. At r = 60 that is 49,800; at r = 87, 104,700.
- **r ~ 87 is real for V6a.** I rebuilt it myself (`power.noise_ratio` definition: SD of the Brier differences / (0.02
  x the base rate's mean Brier)). On the same 1,908 exploratory days: mean base-rate Brier 0.0475, r = 86.5, n =
  103,648. G8 passes the gate-set differences, the gate-set mean baseline loss and margin 0.02, as protocol section
  7 says.
- **Why.** The minimum effect is 2% of the baseline's Brier. For a 4%-frequency event that is about 0.00095 in Brier
  units, while one day's Brier difference swings by up to about 0.3 on a 2% day. So detecting an improvement of
  exactly the minimum effect needs about 100,000 independent days, about 400 years for V6a.
- **The observed skill does not change that report.** The report sizes for the minimum effect, not for the observed
  14.5%. For scale (reasoning only, same formula at rate/15 with the observed effect): about 1,976 independent
  outcomes, roughly 8 years for V6a. And rule E+D's calibrated thresholds, which replace rate/15 at a real look (V6a
  claim thresholds 2.6e-14 to 2e-5, protocol 11 D), need far more.
- **What it changes (for the owner and the G6 session, before the freeze).**
  - Section 6's table takes option 1 only when the best-powered question's projected settle date is at most 2 years
    away.
  - With V6 at r of about 60-87, and V1/V2's thresholds already "effectively unreachable" (11 D), every power report
    is likely to project beyond 2 years. So the stop review is likely to land on option 2 (code only) whatever the
    forecasts show.
  - That is a property of the registered rules: the 2% minimum effect, Bonferroni at /15 and section 7's formula. It
    is not a code error. Changing it is a protocol decision (G6 is not frozen); I make no recommendation on the
    rule itself.

## Addendum 2 (15 Oct 2026): G8 at de4272e8 (merges G7 58f4329, adds c256ec15)

**Verdict: FAIL.** Addendum 1's should-fix is not addressed. Everything new is correct.

- **Should-fix (open, unchanged).** `look.py` at de4272e still has no `DESCRIPTIVE_ONLY` skip. The new SHA changes
  only `cli.py`, `records.py` and `scoring.py`. I reproduced the crash end to end:
  - a real `run_look` with `FrozenToolThresholds(Path('tools'))`;
  - one registered V7 member, 130 scored outcomes, 9 2% days (passing both gates);
  - the look raised `KeyError: 'v7_vix_higher_in_5_sessions'`.
  - The fix stays as stated in addendum 1.
- **New and correct: c256ec15.**
  - After the freeze, a look counts only live rows of forecast days strictly after the freeze day, for the member
    and for its primary baseline. Back-fill rows and earlier live rows are dropped. That matches protocol 8 ("only
    forecasts made after the freeze count"). Excluding the freeze day itself is the conservative reading.
  - The freeze day is read from a required `Frozen on: YYYY-MM-DD` line. A record without the line is refused
    (`FreezeDateMissing`), so a look cannot silently count everything.
  - This adds a dependency for the G6 freeze commit: `FREEZE_v4.md` must carry that line. Tests cover both.
- **The rename** `forecast-v4-scores` avoids G7's `forecast-v4`. CLAUDE.md and the docstring agree.

I did not re-run the full suite on this SHA (it fails on the open should-fix anyway). I will run it on the fix SHA.

## Addendum 3 (15 Oct 2026): G8 at 1e2ebf81 (fix on top of de4272e)

**Verdict: PASS.** Addendum 1's should-fix is met, and nothing else is open.

- **Fix.** `member_result` returns NOT_JUDGED for `terms.DESCRIPTIVE_ONLY` (V7) before the batch, gate or threshold
  step. The new test runs a look with a registered V7 member through a threshold source that raises if asked: not
  judged, p = 1, Test A undecided.
- **My repro from addendum 2, on this SHA.** A real `run_look` with `FrozenToolThresholds(Path('tools'))` and the
  same V7 member (130 outcomes, 9 2% days) now completes: Test A is "undecided", with no KeyError.
- **Gates, run by me.** 5,074 passed and 0 failed with `FNO_SLACK_BOT_TOKEN` unset (G7 58f4329 is merged in, so
  `test_freeze_v2` is green). ruff, format and check_imports are clean. A trial merge with `origin/main` conflicts
  only in `reviews/claude/README.md` (keep both).
- **Still the freeze's, not G8's.** `FREEZE_v4.md` must carry "Frozen on: YYYY-MM-DD" (addendum 2) and the section
  11 E line. The power-report consequence (addendum 1) is for the owner and the G6 session (response 133).

## Addendum 4 (15 Oct 2026): merge check, G8 merged to `main` as 5e50ba8

**Verdict: merge check complete, matching the PASS.** One correction to the rule 8 record.

- **Parents and content.** `5e50ba8` has parents `f891d9b` (main) and `1e2ebf8`, the SHA I passed, and it is on
  `origin/main`. Every file G8 changed that main did not touch is byte-identical to 1e2ebf8. Only
  `reviews/claude/README.md` changed on both sides:
  - no main line is lost and there are no markers;
  - the one branch line not kept is an older wording of the Response 71 row ("19 of 19"), which main itself had
    already changed. It is not a loss from the merge.
- **Gates on 5e50ba8, run by me.** 5,274 passed with `FNO_SLACK_BOT_TOKEN` unset; ruff and check_imports clean.
- **Rule 8, my own run.** `python -m fno forecast-v4-scores report --as-of 2026-10-15` on main's committed back-fill
  printed the EXPLORATORY line. I deleted the report files afterwards; nothing was committed.
  - The committed back-fill (f891d9b) is byte-identical to my own back-fill run (V6a `v6_ewma_t4` file hash
    `4de7b6e5…`).
- **Correction to the rule 8 record in `conversations/2026-10-15.md`.** The figures quoted as "V6a" (scored 1,900,
  relative improvement 0.1711, p 0.0064, r 61.53, 52,379 outcomes) are **V6b's** lines in the report. V6a's own lines
  are scored 1,908, relative improvement 0.1449, p batch-means 0.0070, r 86.55, 103,648 outcomes, which equal my
  independent rebuild in addendum 1.
  - Both questions read "cannot settle in useful time", so the point for the owner (response 133) is unchanged.
  - The log line should name V6b, or quote V6a's numbers.
- **The back-fill commit f891d9b.** It is exploratory forecast data, all `backfill_exploratory`. Protocol 8 requires
  it to be disclosed in the freeze record. Adding that is the G6 freeze commit's job.

## Addendum 5 (15 Oct 2026): V6b power, the conflict between protocol 11 D (r = 3) and response 133 (r = 60-87)

The orchestrator asked, for the owner's re-decision: which r is right, how many years V6b needs, and whether any v4
member can be claimed within 2 years.

1. **Both use the same formula. The difference is the value of r.**
   - Section 7 defines `r = SD(d) / (margin x mean baseline loss)`.
   - 11 D's "149-206 at r = 3" uses an **assumed** r = 3, the design's generic example for point questions. It was
     never measured for a Brier question.
   - Response 133's r is **measured** on the committed 2017-26 back-fill (`v6_ewma_t4` against the base rate). The
     G8 report on main and my own rebuild agree: V6b r = 61.53 (mean base-rate Brier 0.1424, so the minimum effect is
     0.02 x 0.1424 = 0.0028 Brier units); V6a r = 86.55 (base Brier 0.0475).
   - Why r is that large: one day's Brier difference on a 0/1 outcome swings by up to about 0.3, while 2% of a 0.05-0.14
     Brier is 0.001-0.003. That ratio comes from the outcome being binary and rare, not from this forecaster. So no
     realistic forecaster brings r near 3 (reasoning, backed by the measured SD).
   - **The right r for V6b is about 60** (strong evidence for this forecaster and window; some evidence for future
     forecasters). 11 D's 149-206 does not describe V6b's minimum-effect test.
2. **Years for V6b,** using section 7's formula `n = 13.84 r^2` (plain first step at 0.03/15, normal approximation,
   optimistic) and 252/5 = 50.4 independent outcomes a year:
   - (a) at the protocol's minimum effect: n of about 52,400, **about 1,040 years**;
   - (b) at the skill the forecaster shows on V6b (relative improvement 0.171; the 14.5% is V6a's): r_obs = 7.19, n of
     about 716, **about 14 years**. Under rule E+D's thresholds (11 D's ratio 149-206 / 134), about 16-22 years.
   - For V6a at its own observed 14.5%: n of about 1,975, about 8 years at the plain rate. Under E+D's thresholds
     (2.6e-14 to 2e-5) it is effectively unreachable, as 11 D says.
   - Cross-check with real numbers (exploratory, spent data): nine years of back-fill (1,900 scored days) give V6b a
     batch-means p of 0.0064 and V6a 0.0070. Look 1's plain level is 0.02 / 15 = 0.0013, and the calibrated levels are
     lower still.
3. **No v4 member can realistically be claimed within 2 years** (some evidence plus reasoning).
   - V1: thresholds effectively unreachable (11 D; 1.1e-12 at n = 125), and no live data yet.
   - V2: 8-22 years even at r = 3-5.
   - V6a: unreachable under E+D.
   - V6b: about 14-22 years even if its full observed skill is real.
   - V7: descriptive only.
   - So Test A "yes" is out of reach at the May 2027 review. Test A will almost surely read "undecided". Per section
     6, the table then goes to option 1 or 2 by the power report, and with every report beyond 2 years, to option 2
     (code only).
   - 11 D's sentence "only V6b can be claimed, slowly" rests on r = 3 and should not guide the owner's choice.

Labels: the measured r values and the p-values are strong evidence (computed twice, from committed files). Years are
planning approximations (section 7: "a rough heuristic"). That r stays near 60 for any forecaster is reasoning.
