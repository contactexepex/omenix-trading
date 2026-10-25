# Judge 26: story B1, feature library (F1-F3 and the look-ahead harness)

**Verdict: PASS.** All 6 criteria are MET. There are no blocking or should-fix findings and 2 minor findings. The
first minor finding must be fixed before B6 adds features that rely on the harness alone.

My hand values agree with the app:
- F1 recomputed by hand for one real day the builder did not use (14 Jul 2025): **3.2168**, the app also 3.2168.
- The builder's calculator day: 4.4335.
- F2 and F3 checked by hand for 14 Jul 2025.

I read the look-ahead harness and ran it. I also tested it with deliberate breaks: it catches real leaks, but it
trusts each feature's own declared cutoff (minor finding 1).

**What I judged**
- **Repository:** trading `main` at bc93cbb, which contains B1 commits 6430d45 (merged as fa80701) and 30c0cfb.
- **Claims:** `reviews/claude/response_44_2026-10-13-b1-feature-library.md`.
- **Story:** `docs/stories/B-research-engine.md`, B1.

## Checks run by the judge

```
$ python -m pytest -q                          713 passed
$ ruff check fno tests tools                   All checks passed!
$ python tools/check_imports.py                clean
```

### F1 by hand, 14 Jul 2025 (expiry 28 Aug 2025, 45 days, T = 45/365 = 0.123288)

My script reads the raw panel CSV and imports nothing from `fno`. It uses its own Black-76
(`e^(-rT)[F·N(d1) − K·N(d2)]`, put by parity) and its own bisection between 1% and 200%.

| Input | Value |
|---|---|
| Nifty 50 close | 25,082.30, so ATM is 25100 |
| Same-expiry future close | 25,268.80 (volume 11,462) |
| Rate | 0.065 |
| 25100 CE | close 511.65 (volume 1,888): IV **12.0781** |
| 25100 PE | close 326.95 (volume 2,789): IV **11.5787** |
| ATM IV (mean) | **11.8284** |
| Realised: 21 closes, 16 Jun to 14 Jul 2025 (RMS of 20 log returns × √252, not demeaned) | **8.6116** |
| **F1** | **3.2168** |

The app (`build_features` through the composition root) gives **3.2168149612740713**.

**F2 for the same day, by hand:** the VIX close of 11.98 against the median of the previous 250 valid closes,
14.37, gives **False**. The app also gives False.

**F3 for the same day:** the window runs after the entry day (15 Jul) up to the exit day (7 Aug). The RBI decision
of 6 Aug 2025 was rescheduled on 6 Jun 2025 (events.csv row 53), so it was known on the decision day. That gives
**True**; the app also gives True.

### The builder's calculator day and IV claim, by the same script

| Day | My values | Builder's claim |
|---|---|---|
| 16 Sep 2026 | IVs 12.5628 / 12.3166; realised 8.0062; F1 **4.4335** | 4.43 |
| 12 Oct 2026, ATM 22350, Oct expiry | Black-76 call / put 14.5055 / 14.4695 | 14.51 / 14.47 |
| 12 Oct 2026, ATM 22350, Nov expiry | Black-76 call / put 14.3932 / 14.5082 | 14.39 / 14.51 |

### The look-ahead harness: read, run, and five breaks

What I read in `tests/research_engine/lookahead_harness.py`:
- For every session whose data becomes available after the cutoff, it scales or removes the closes and VIX,
  reprices every option and future row, removes one leg in ten, makes legs untraded and adds strikes.
- It moves every event not yet knowable at the cutoff and adds four invented events.
- It refuses to pass when nothing follows the cutoff.
- The 20-day test uses real values only: F1 and F2 are never `None`.

Breaks to the feature code (all reverted; `git status` clean):

| # | Break | Tests failing | Which tests |
|---|---|---|---|
| MA | F1's realised volatility reads the next sessions' closes | 4 | the look-ahead test and the real-day hand values |
| MB | The same leak, **plus F1 declaring `known_at` = decision day + 7** | 3 | **only** `test_features_equal_the_hand_calculation_on_three_real_days`. **The look-ahead test passes.** |
| MC | F2's median includes the decision day | 2 | hand values |
| MD | ATM tie goes to the higher strike | 2 | |
| ME | An untraded ATM leg uses its settlement price | **0** | the fixture's settlement is 0.0, so the solver fails anyway |
| ME2 | Volume ignored (any close used) | 2 | `test_f1_is_none_for_a_missing_or_untraded_atm_leg` |

## Criteria

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 1 | Changing any panel value after the decision day leaves all three features unchanged (20 random days) | Harness read and run; MA caught. F1-F3 inherit `known_at` = decision day 15:30, so their cutoff is the decision-day close, as the criterion asks. | MET (see minor 1) |
| 2 | Three sample days equal hand values (F1 to 0.01 points) | Tests pass. My own hand F1 for a fourth day matches to 4 decimals, the builder's day matches, and F2 and F3 match. | MET |
| 3 | A missing or untraded ATM leg, a solver failure, or fewer than 21 closes give F1 `None`; fewer than 250 VIX closes give F2 `None` | Tests pass; ME2 caught | MET (see minor 2) |
| 4 | The test also mutates same-day data after the cutoff (15:00 for live versions) | No live feature exists yet (B7). With a 15:00 cutoff the harness changes the decision day's own 15:30 data, and F2 declared as a 15:00 feature is caught on 5 days (test read and passing). | MET |
| 5 | An event announced after the decision day is ignored | Test passes. The harness's announcement-ignoring F3 is caught (the builder's test). | MET |
| 6 | F3 only through `in_window`; ignores 22 May 2020; sees the moved Feb 2022 meeting at 9 Feb | Tests pass; `event_features.py` (20 lines) calls only `in_window` | MET |

## Claims vs reality

- **F1 values, IV comparisons and the calculator day:** reproduced independently (tables above).
- **"The harness changes every input a feature can read":** true for values. It does not add or remove later
  *sessions*: it changes their values but keeps the session list. A feature that counted future sessions would not
  be caught. No such feature exists; I note it for B6.
- **The design choices:**
  - Black-76 with a traded same-expiry future as the forward, and the rate only to discount: sound, and backed by
    the 12 Oct numbers.
  - The mean of the call and put IVs: stated as reasoning only, acceptable.
  - Muhurat sessions left out; the 21 closes must be consecutive across 30 Mar 2021: sound.
  - The rate wired from `config.yaml`, so B5 must hash the whole file: correct, and a useful catch.
- **The builder's limits:**
  - **2019 F2 = `None`:** AGREED, strong evidence. The panel starts on 1 Jan 2019 and A1 lists 245 sessions in 2019,
    under 250, so F2 cannot exist anywhere in 2019. For experiment 1's 2019-23 challenge period this silently turns
    every F2 condition off for a whole year. **The 2018 index-close data story must land before B5's freeze.**
  - **F3 true on 41 of 202 days:** not recounted by me. Plausible from the window length.

## Engineering standards

- **Sizes:** all files small (code 20 to 129 lines; the harness 125).
- **Patterns:** the IV model is a strategy (`ImpliedVolModel`) chosen in the composition root; the panel reader sits
  next to the writer and reuses its column lists (DRY); F3 reuses A6's `in_window` instead of its own filter.
- **Breaches:** none found.

## Findings (minor)

1. **The harness checks against the feature's own declared cutoff, so a feature that declares a late `known_at`
   passes with a leak.**
   - **Evidence:** MB. F1 reading the next sessions' closes and declaring `known_at` = decision day + 7 passes the
     look-ahead test; only the pinned real-day values catch it. Nothing tests that a daily feature's `known_at` is
     the decision-day close.
   - **Why it matters:** B6 will add many features guarded only by this harness.
   - **Expected:** the 20-day test passes `cutoff=` the decision-day close explicitly, or a test asserts every
     daily-close feature's `known_at`. A feature may declare an earlier cutoff (a live one) but never a later one.
2. **"Settlement is never used for features" is not tested directly.** ME (an untraded leg priced at its settlement)
   passes all tests, because the fixture's settlement is 0.0 and the solver fails anyway. Real untraded rows carry a
   positive settlement. Expected: a test with an untraded ATM leg whose settlement is a valid price, giving F1 `None`.
