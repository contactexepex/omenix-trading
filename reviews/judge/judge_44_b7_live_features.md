# Judge 44: story B7, live 3 pm feature versions and their validation (plus judge 28 minor 2)

**Verdict: FAIL.** There are 2 should-fix findings and 3 minor findings.
- **What works:** the live features themselves are right. On a snapshot in A4's own file format built from real
  12 Oct 2026 prices, live F1 equals my hand value. The 15:00 cutoff holds to the second, in either time zone. My
  look-ahead breaks are caught.
- **What fails:** the validation and the gate that decide whether a live feature may drive paper trades.
  - The agreement measure counts "no live value" as agreeing with "close condition false". The policies treat those
    as different decisions.
  - The gate cannot apply a strategy's own frozen use rule.

  On my own 20-day case, both together let a feature pass at a reported 90% agreement while the policy's actual
  decisions match on only 80% of days.

**Judge 28 minor 2** (look-back from index-close files only, 94ea756 / 1be845c): **ACCEPTED**, see the last section.

**What I judged**
- **Repository:** trading `main` at 307c182, which contains B7 code c68163a (merged 2c5fdcf).
- **Claims:** `reviews/claude/response_49_2026-10-13-b7-live-features.md`.
- **Story:** `docs/stories/B-research-engine.md`, B7.

## Checks run by the judge

```
$ python -m pytest -q                                  1094 passed
$ python -m pytest -q tests/research_engine tests/research_data      281 passed
$ ruff check fno tests tools                           All checks passed
$ python tools/check_imports.py                        clean: 239 files
$ python -m pytest -q tests/test_code_size.py          240 passed (live_features 105, live_validation 115, quote_snapshots 95,
                                                       live_gate 30, composition.py 312 lines)
$ python -m fno research validate-live F1_live_atm_iv_minus_rv20     (in a scratch copy of the repository)
  days 0, agreement None, validated False   (as claimed: no A4 day is committed yet)
```

### One live value recomputed by hand (the story's "judge verifies")

**No real A4 snapshot is committed yet** (`research/data/quotes/` does not exist), so I could not recompute from a
committed one.

**Instead:**
- I wrote a snapshot in A4's exact format: the recorder's `COLUMNS`, `.meta.json` and `.canonical` files, under
  `QuoteSnapshotRecorder.path`. It holds the real 12 Oct 2026 closes of the 27 Oct 22,300 / 22,350 / 22,400 calls and
  puts as bid and ask at ±0.50, with `last` set to 999 as a trap.
- I read it back through `RecordedSnapshots`.
- I computed live F1 with my own Black-76 and my own realised volatility.

| Step | Hand | Note |
|---|---|---|
| Spot (meta), ATM strike | 22,363.35, 22,350 | nearest strike to spot |
| Mids C, P | 280.30, 243.25 | not `last` (999) |
| Parity forward K + e^(rT)(C − P), T = 15/365, r = 0.065 | 22,387.15 | the real future closed at 22,386.50: parity is within 0.65 points |
| IVs (call, put) | 14.4865%, 14.4865% | equal by construction at that strike |
| Realised: 20 log returns of the closes 10 Sep to 9 Oct plus the 15:00 spot | 13.9661 | the 12 Oct close is not used |
| **Live F1** | **0.5204** | engine **0.520386**; the close version on the same day is 0.5214 |

**The cutoff, probed with the same snapshot:**

| `finished_at` | Live F1 |
|---|---|
| 15:00:00+05:30 | 0.5204 |
| 15:00:01+05:30 | None |
| 09:29:59Z | 0.5204 |
| 09:30:01Z | None |

My snapshot carries closing prices as 15:00 mids, so the small live-versus-close difference here says nothing about
real 15:00 behaviour. Only recorded A4 days can measure that.

### My breaks (each reverted; `git status` clean)

| # | Break | Tests failing |
|---|---|---|
| B1 | Live F1's realised volatility reads the decision day's own close | 5 |
| B2 | A snapshot is used whatever its finish time | 2 |
| B3 | An invalid quote still gives a mid | 2 |
| B4 | Live F2's 250-day VIX median includes the decision day's own close | **0** (minor 1) |
| B5 | The availability test is dropped from the use rule | 1 |

## Criteria

| # | Criterion | Builder's claim | Judge's evidence | Result |
|---|---|---|---|---|
| 1 | The B1 harness passes for every live feature with the 15:00 cutoff | met | `test_live_lookahead.py` passes. B1 and B2 are caught. My cutoff probe holds to the second. B4, a real leak, is not caught (minor 1). | MET |
| 2 | 20 fixture days: report numbers equal a hand computation | met | **The arithmetic is right.** I recomputed 8 × 0.5 + 2.5 + 9 × 0.25 + 1.5 = 10.25 over 19 days (mean 0.5395, largest 2.5), agreement 17/20 and availability 19/20. **The measure is wrong for the policies:** finding 1. | PARTLY |
| 3 | A strategy whose live features are not validated cannot reach `paper` (D1 loader check) | partly | **Built and tested:** `require_validated` refuses an unvalidated or missing feature (my run agrees). **Open:** D1 does not exist yet, so nothing calls it, and the gate cannot honour a strategy's frozen rule (finding 2). | PARTLY |
| 4 | Invalid or missing quotes give None, never the last price | met | `LiveQuote.mid` needs a valid, two-sided, uncrossed book and never reads `last`. My trap (`last` 999) was not used. B3 is caught. | MET |

## Claims vs reality

| Builder's claim | Checked | Result |
|---|---|---|
| A4 records no VIX and no future, so live F2 is always None; F1's forward comes from parity | `quote_snapshots.py` reads `meta.get("vix")`, and the recorder writes none. Parity gives 22,387.15 against the real future's 22,386.50 on 12 Oct. | **True** |
| No A4 day is committed, so the command reports 0 days | My run | **True** |
| A capture finished after 15:00 is not used | My probe | **True** |
| Live realised volatility uses the previous 20 sessions' closes plus the 15:00 spot | My hand value | **True** |
| "A number counts as above zero (F1 > 0, as every policy uses it), … None as not met" | `policies.py` has `Positive` and also `NotPositive` ("known and at most zero") and `IsFalse` ("None is not false"). Experiment 1's P4-opposite, P5 and P8-opposite act on `NotPositive(F1)`. | **False as stated:** finding 1 |
| Availability added so a never-computed feature cannot pass | `test_a_live_feature_that_is_never_computed_cannot_pass_vacuously`; B5 is caught | **True**, but only a partial guard (finding 1) |
| Discovery results byte-identical after the judge-28 fix (814a79a5…) | My own run | **True** (below) |

## Findings

### 1. Should fix: agreement treats "no live value" as agreeing with "close condition false"

- **Where:** `live_validation.condition()` maps None to False, and `DayComparison.agrees` compares two booleans.
- **Why it is wrong:** the policies have three states.
  - With `Positive(F1)` and `NotPositive(F1)`, a None value is neither: no trade.
  - A close value ≤ 0 is `NotPositive`: for example, P5 then trades a butterfly.
  - So a day with live None and close −1 is a different decision, but the report counts it as agreement.
- **The availability guard does not close this.** It caps such days at 10%, and those days are counted as agreeing
  on top of the 90% agreement threshold.
- **My case** (the builder's `validate` and real `Positive` / `NotPositive`; close −1.0 on all 20 days):
  - live None on 2 days, +0.5 on 2 days, −1.0 on 16 days;
  - report: agreement **0.90**, availability **0.90**, **validated True**;
  - P5's actual decisions match on **16 of 20 = 0.80**.
- **Expected:**
  - Agreement compares the policy's decision state: above zero, at most zero, or unknown for a number; true, false,
    or unknown for a flag. None then counts as disagreeing unless the close value is also None.
  - A test with a live None against a close ≤ 0 that counts as a disagreement.
  - Availability can stay as a separate guard.

### 2. Should fix: the gate cannot apply the strategy's frozen use rule and trusts a flag

- **Where:** `require_validated(strategy, live_features, validated: Mapping[str, bool])` and
  `validated_from_reports` read only each report's `validated` flag. That flag is computed with the default
  `LiveUseRule` (20 days, 90%, 90%) when the report is written.
- **Why it is wrong:**
  - The story says the use rule is "frozen per strategy in its playbook file", and the owner may set a stricter one.
  - With this API, a strategy frozen at 95% passes on a report validated at 90%. My run: `require_validated` allowed
    it at agreement 0.90.
  - A hand-edited `"validated": true` also passes. The report carries its numbers, but the gate never re-checks them.
- **Why it matters now:** D1 will call this function as built.
- **Expected:**
  - The gate takes the strategy's frozen `LiveUseRule` and re-evaluates each report's numbers (`days`, `agreement`,
    `live_available`) against it. It refuses when a report is missing, or when its numbers fail that rule.
  - A test: a 90% report against a 95% strategy rule is refused; a forged flag with failing numbers is refused.

### Minor findings

1. **The harness cannot see a leak in live F2's history.**
   - With B4 (today's VIX close counted in the 250-day median), all 169 research-engine tests pass. In the fixture,
     one changed value cannot move a 250-value median across the snapshot's 14.0. It is the same blind spot for any
     median or threshold feature.
   - **Expected:** one direct test that the history ends at the previous session, for example a fixture where today's
     close alone flips the median, or an assertion on the dates read.
2. **Live F1 depends on the concrete `Black76`** (`model: Black76 | None`, with `model or Black76()` built inside the
   class).
   - CLAUDE.md wires concrete classes only in composition roots, and the parity forward is specific to Black-76
     anyway.
   - **Expected:** type it against `ImpliedVolModel` and drop the default, since the composition root already passes
     the rate.
3. **Some days may have no usable capture: availability risk (reasoning only).**
   - A4's first attempt starts at 14:55, and its first run of the day reads about 6 NSE files (about 15 s, response
     39) before about 180 sequential Groww quote calls (2 monthlies, strikes within ±5% of spot).
   - Any attempt that finishes after 15:00, including every retry after an incomplete first attempt, gives live
     None for that day.
   - That is the correct look-ahead choice, but it may make the 90% availability rule hard to meet.
   - **Expected:** report `finished_at` per day in the validation output. Once A4 has real days, measure the capture
     duration before the owner relies on the rule.

### Not B7 defects (routed to the orchestrator)

- **India VIX and the near-month future at capture:** A4 must record both. Until it does, live F2 cannot be validated,
  so any strategy using F2 cannot reach paper. That is fail closed, which is the right default.
- **The real validation needs 20 or more committed A4 days and a panel rebuilt past them.** B7's live features stay
  unproven on real 15:00 data until then.

## Project rules

- **No real orders.** No secrets in files. Read-only on snapshots.
- **Files:** all within 350 lines, but `composition.py` is at 312, so the next addition should split it by area (as
  judge 43 said).
- **Constants:** feature names are in `fno/constants.py`, and the cutoff is `DESK_DECISION_TIME` in the composition
  root.
- **Design:** see minor 2 (a concrete dependency). Otherwise small, single-purpose units behind `Feature`.

## Judge 28 minor 2: look-back from index-close files only (94ea756, merged 1be845c): ACCEPTED

- **No earlier options file is opened.** I ran experiment 1's discovery period through `build_experiment_runner`
  and wrote the results to my scratch folder. I logged every panel file it opened: futures and options for **2024,
  2025 and 2026 only**. The 2023 options file is no longer opened.
- **The results are byte-identical.** My `results_discovery.json` has SHA-256 `814a79a56db4…3353c98b`, equal to the
  committed file and the builder's claim.
- **The new closes are right.**
  - **Against NSE:** I fetched NSE's own index-close files for 7 rows of `warmup_closes.csv` (6 at random from
    2019-2026, plus 12 Oct 2026). NIFTY and India VIX equal the file on all 7. The SHA-256 equals the file on 6.
  - **The exception, 12 Oct 2026:** NSE's file today has a **different SHA-256 with the same values**. NSE rewrote
    that file after it was saved. That is A11's subject (revisions of NSE files), not a defect here.
  - **Against the panel:** the file equals the panel's NIFTY and VIX on 1,928 of 1,929 panel sessions from 2019 on.
    The exception is **30 Mar 2021**, where the panel holds no close but the file has NSE's 14,845.10. That is a gap
    in the panel, outside the discovery period and outside this fix, noted for A3 and for the challenge run.
- **Full suite:** 1,094 passed.

## Addendum: round 2 (trading 9f39718, merged 0364b22; response 49 addendum)

**Verdict on B7: PASS.**
- Both should-fixes and all 3 minors are fixed, and each is re-checked with my own judge-44 cases.
- The two routed additions (A4 levels, and the 30 Mar 2021 closes) are correct.
- 1 new minor, below.
- Criterion 3 stays as before: the gate is built and tested, and D1 must call it. D1 does not exist yet; that is not
  a defect of B7.

**Checks:**
- `python -m pytest -q` 1,299 passed; ruff and imports clean (288 files); code size passes.
- Discovery re-run: `814a79a5…`, still byte-identical.

| Judge 44 item | Re-check (mine) | Decision |
|---|---|---|
| 1 Agreement on three decision states | My 20-day case (close −1; live None ×2, +0.5 ×2, −1 ×16) now gives agreement **0.80**, not validated (was 0.90, validated) | ACCEPTED |
| 2 Gate applies the strategy's frozen rule and ignores the flag | A 0.95-agreement report: allowed under the default rule, **refused under a 99% rule**. My forged report (`validated` true, agreement 1.0, days 99, availability 1.0 over per-day values giving 0.80): **refused**. | ACCEPTED |
| Minor 1 F2 history leak | My B4 break (today's VIX in the median) now fails 1 test (was 0) | ACCEPTED |
| Minor 2 Concrete Black-76 | Constructor takes `ImpliedVolModel`, with no default; the root passes `Black76()` | ACCEPTED |
| Minor 3 Capture time per day | `captured_at` carried in every comparison (test) | ACCEPTED |

**Live F1 by hand, with the recorded future.**
- I took my A4-format snapshot of real 12 Oct prices and added the levels as the recorder writes them
  (`futures: [{expiry 27 Oct, last 22,386.50}]`, `india_vix` 15.25).
- IVs: 14.5055% (call) and 14.4695% (put), equal to B1's research values (14.51 / 14.47).
- Live F1: **0.5214** by my hand, equal to the engine's 0.521399. It now equals the close version on the same
  prices, as it should once both use the same model and future. The parity forward is gone.

**A4 levels (routed).**
- `market_levels.py` reads NSE's India VIX and NIFTY futures inside each attempt, before `finished_at`. A failing
  endpoint is recorded and never blocks the capture. Built without a level source, A4's golden bytes are unchanged.
- **Not yet proven:** NSE answering these endpoints at 15:00 from the routine's network. The first real 3 pm run will
  show it in `levels_failures`.

**30 Mar 2021 (routed; my judge-44 panel finding).**
- The reader now gives that session NSE's index closes, 14,845.10 and 20.65. I fetched NSE's
  `ind_close_all_30032021.csv` myself, and they are equal. It still has 0 option and 0 future rows.
- **Consequences, for the orchestrator:**
  - **Experiment 1's challenge period:** the cycle decided on **12 Apr 2021** (expiry 27 May 2021) sits inside the
    21 sessions after 30 Mar. Its F1 was previously None (the window broke), and now has a value. That is a data
    correction before the freeze, so it is legitimate, but the freeze record must name this reader rule.
  - **G1:** no golden file exists yet. `research/forecasts` still holds only PROTOCOL.md and FREEZE.md, and
    `fno/forecast` is unchanged since ef5b818. So **no golden value has been computed before this change**. The
    golden IV30/RV20 file must be generated at or after 0364b22, and its record must name that commit. Values from
    30 Mar to about 28 Apr 2021 differ from any computation made before it.
  - Round 2 did not edit any of G1's three hashed files (`git show --stat`), and `test_freeze.py` passes.

**Minor (new): the gate trusts per-day values written into the report.**
- My report with per-day `live` values hand-edited to equal `close` passes, as the gate recomputes from those values.
- It is still much stronger than round 1: no flag or summary is trusted, and an edit is visible in the committed
  report's diff.
- **Expected (reasoning only, before D1 uses it for real):** D1's gate recomputes from the committed A4 snapshots
  and the panel (`run_live_validation`), not from the report file. Or the report records the snapshot SHA-256 values
  it was built from, and the gate checks them.
