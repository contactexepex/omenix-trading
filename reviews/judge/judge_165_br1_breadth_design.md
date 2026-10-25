# Judge 165: BR1 breadth track, design proposal (judge G)

- **Judged:** branch `story/br1-breadth-design` at `f20bf2e4807b6666932ac12da3eb41e842080970` (builder session
  013xqaNTCbSBytKgqpfaYFqZ): `reviews/claude/response_154_breadth-track.md`, `research/2026-10-15-breadth-sizing/`
  (`sizing.py`, `fetch.py`, `README.md`), one README row. Design only, no `fno/` code.
- **Read first:** CLAUDE.md, AGENTS.md, docs/JUDGE.md, DESK_DECISIONS rows 156 ("Keep the design simple"), 182-183
  (v4 frozen as the slow yardstick, the breadth track), WORK_REGISTER (BR1 row: this builder, "judge + ChatGPT +
  owner before any code").
- **Verdict: FAIL** (design text): 1 blocking, 7 should-fix, 5 notes. The core idea is sound and the numbers
  reproduce exactly; the fixes are text changes to response 154 before the owner sees it.

## What I re-ran

1. `fetch.py <scratch> 300` from the Drive raw archive (read-only): "fetched 300 in 338 s" (2025-07-29 to 2026-10-14).
2. `python -I sizing.py <scratch>`: **every line of the README output reproduced exactly** (base rate 0.281, rho_Y
   0.114 / N_eff 8.4, rho_d 0.052 / N_eff 17.5, indices 0.514 / 1.57, sd daily mean 0.0182, lag-1 0.045, returns
   rho 0.291 / N_eff 3.4). Strong evidence.
3. Months table by hand: n = ((z(1-0.05/K) + z(0.8)) x 0.0182 / (s x 0.202))^2 / 21. K = 12: 1% 46.8, 2% 11.7,
   3% 5.2, 5% 1.9 months. Matches. N_eff of 30 at rho 0.052 = 12.0: arithmetic right (but see should-fix 5).
4. My own script (scratchpad, same files, same chain rule) for other forecaster pairs, the top-30 subset and big moves:

```
next-day |log move| > 15% (corporate-action candidates): 28  e.g. KOTAKBANK 2026-01-13 -1.622, PATANJALI 2025-09-10
  -1.102, NESTLEIND 2025-08-07 -0.712, TRENT 2026-06-03 -0.406 ...
pair (baseline vs forecaster)  mean d (t)       rho_d  N_eff  sd daymean  lag1 | months 2%/3%, K=12, a=.05 | a=.02/K
market   vs trail60            -0.0020 (-1.70)  0.052  17.5   0.0182      0.045 | 11.5 / 5.1               | 13.6 / 6.0
cal60    vs trail60            +0.0015 (+3.25)  0.014  51.4   0.0069      0.115 |  1.6 / 0.7               |  1.9 / 0.8
cal60    vs cal20              -0.0024 (-2.40)  0.032  26.9   0.0154      0.112 |  8.0 / 3.5               |  9.4 / 4.2
cal60    vs cal60 x 1.15 tilt  -0.0051 (-3.85)  0.112   8.6   0.0203      0.090 | 13.9 / 6.2               | 16.4 / 7.3
top 30 by option turnover (4 indices + 26 stocks), market vs trail60: rho_d 0.064, N_eff 10.5, 2%/3% 17.7 / 7.9 months
  (tilt pair: N_eff 6.3, 19.3 / 8.6 months); K = 3 instead of 12 (market vs trail60): 2% in 8.4 months
```

`cal60/cal20` = "calibrated market": implied move scaled by the trailing 60 (20) session realised-to-implied ratio,
p = 2(1 - Phi(1/k)); `x 1.15` = a forecaster uniformly more vol-bullish than the baseline (a regime call). d > 0 means
the forecaster beat the baseline.

## Findings

### Blocking

1. **Corporate actions are not in the target.** `Y` uses `|ln(S(t+1)/S(t))|` on unadjusted `UndrlygPric`. In the 300
   sessions, 28 name-days move over 15%, several are splits or bonuses (KOTAKBANK -162% log, PATANJALI -110%,
   NESTLEIND -71%). Each is a guaranteed Y = 1 announced weeks ahead: any forecaster (or AI) that reads NSE's
   corporate-action list scores free "skill", and the baseline is hit by noise. This happens every month across 190
   stocks (strong evidence, our data). Fix: the design states that outcomes use corporate-action-adjusted closes (or
   that ex-dates are excluded by a pre-registered rule, decided before the freeze), and lists the adjustment source.

### Should fix

2. **"About 17.5 independent bets a day" is one pair's number, presented as a property of the universe.** rho of
   score differences depends on how the two forecasters differ: 0.014 to 0.112 above (N_eff 51 to 8.6). The realistic
   case, a volatility forecaster that tilts the same way across names on a given day, gives rho 0.112, N_eff 8.6,
   about the same as the outcomes' own 8.4. The 0.052 comes partly from cancelling: the constant market p minus a
   name-specific trailing frequency has mixed signs across names. Fix: replace the headline with the range and say
   that the realistic floor is about 8-9 effective bets (some evidence). The months table survives roughly (2%:
   8-14 months for the realistic pairs, K = 12), because it uses the measured SD of the daily mean, not N_eff.
3. **The primary baseline is asserted to be "the strongest simple one", but on this window my version of it was
   beaten by the plain 60-session trailing frequency** (cal60 vs trail60, t = +3.25; some evidence, one window, my
   implementation). Also, the Brier gaps between trivial baselines (0.7-2.5%) are the same size as the 1-3% skill
   targeted: a "forecaster" can "beat the primary by 2%" by being another simple baseline. Fix: the primary baseline
   is chosen by a written rule on the exploratory history (2019-2025) before the freeze (the best of the registered
   simple baselines), or a claim must beat every registered simple baseline, each in the Holm family.
4. **The sizing uses alpha 0.05/K, the design uses v4's two-look split.** v4 tests at 0.02 per look (DESK_DECISIONS
   row 121): months rise about 18% (2%: 11.5 to 13.6; 3%: 5.1 to 6.0). Also, v4's operative claim rule is
   `calibrated_p` with worst-case thresholds calibrated on v4's NIFTY members (`fno/forecast_v4/confirmatory.py:91`,
   `tools/v4_claim_thresholds.py`), plus NIFTY-specific judgeability gates (`:124-141`). "Apply directly" is wrong for
   these. Fix: state the alpha per look in the table; say which claim rule BR1 uses (plain Holm on
   `confirmatory_test` p, or its own threshold calibration on BR1's series) and whether any judgeability gate applies.
5. **The AI subset is slower than stated.** Measured on the top 30 by option turnover: rho_d 0.064, N_eff 10.5 (not
   12); the 4 indices in it are one bet. 2% skill takes about 18 months (19 for the tilt pair), 3% about 8-9, against
   11.5 and 5.1 for all 194. Fix: correct "about 12 of 17.5 at a third of the cost" to these numbers, and score the
   rule and hybrid families on the same 30 as well, so the AI family has a like-for-like comparison.
6. **One regime: the re-measure must be a freeze gate, not a listed limit.** On the window's top-decile days 64% of
   names hit Y at once; a crash month (March 2020, 2022) will raise rho and the SD. The proposal lists the limit and
   says "the sizing story must re-measure on 2019-2024", but 2019-2023 has no `UndrlygPric` (its own section 4). Fix:
   BR1a fixes the look dates from the worst yearly SD of the daily mean on 2019-2025 (spot from the near-month
   future where the bhavcopy has none), not from this calm-ish window.
7. **The hybrid family can grow its family in flight.** "Rules proposed by AI, applied by code": if new rules are
   proposed during the confirmatory period, each is a new member and K grows. Fix: one line: the hybrid's rule set is
   frozen at the freeze; a new rule is a new version with a new clock (must-not-do item 3 covers families, not rules).
8. **Simplicity and speed: K = 12 costs time the owner asked to save.** K = 3 (T1 only, EOD only, three families)
   gives 2% in 8.4 months against 11.5 at K = 12 (same pair, a = 0.05). T2 (overlapping 5-day windows tested on
   non-overlapping blocks, a fifth of the days) and the residual target add members at little power. Fix: offer the
   owner "confirmatory = T1, EOD, K = 3; T2, direction and 14:30 reported only" as the recommended option, with the
   K = 12 version as the alternative (row 156: keep the design simple).

### Notes (no fix required)

- Results days: stocks have about 4 a year each, and the straddle spreads the event premium flat over n days. A
  forecaster that knows the results calendar gains legitimately but trivially. Recommend reporting skill on results
  and non-results days separately (reasoning only).
- M1's `VixScaledWeather` needs 500 resolved days (`fno/weather/vix_scaled.py:63`); new F&O entrants join the
  universe after about 48 sessions. The baseline's window must match the universe rule, or new names have no
  baseline.
- `fetch.py` fails ruff (12 findings: joined imports and statements) and hard-codes `/home/user/trading`; research
  script, not in the gated paths, but it breaks the clean-code rule. `sizing.py` is clean.
- The weekday count to expiry (holidays ignored) is fine for sizing, as stated; scoring needs the NSE calendar (A7).
- The routine setup was needed before `fetch.py` could import `google.auth`; worth one line in the README.

## The six questions asked

| # | Question | Judge's finding | Evidence |
|---|---|---|---|
| 1 | Re-run / arithmetic | Reproduced exactly; months arithmetic right for its pair and alpha; headline N_eff pair-dependent (should-fix 2), alpha mismatch (4) | strong (re-run) |
| 2 | Snooping, leakage, the 8 items | Pre-registration, forward-only confirmatory, Holm over the whole family, point-in-time universe with no survivorship: adequate. Missing: corporate actions (blocking 1), baseline chosen by rule (3), hybrid rule freeze (7) | strong (1), some (3), reasoning (7) |
| 3 | One 14-month regime | Yes, likely optimistic for crash months; make the re-measure a freeze gate (6) | some |
| 4 | Reuse G7, G8, M1, S1; S6 | Real: the files exist (`fno/forecast_v4_rules/records.py`, `fno/forecast_v4/confirmatory.py`, `fno/weather/vix_scaled.py`, `fno/fo_bhavcopy.py`); no parallel scorer or parser proposed; only the claim-rule wording is wrong (4). No overlap with S6: BR1 has no random control and no trade scorecards | strong |
| 5 | 30-name AI subset | Reasonable choice, numbers too optimistic (5) | strong (measured) |
| 6 | Simplicity | Five stories and three families are acceptable; the confirmatory family should be smaller (8) | reasoning |

## Claims vs reality

| Claim (response 154) | Reality |
|---|---|
| rho 0.052, N_eff 17.5, indices 1.57 | Reproduced; true for the market-vs-trailing pair only (8.6-51 across pairs) |
| 3% in 5-6 months, 2% in 12-14, 1% 4-5 years | Right at a = 0.05/12 for that pair; +18% at v4's 0.02 per look; 8-14 months for 2% across realistic pairs |
| NIFTY alone 2% needs ~17 years | Arithmetic consistent with its SD (not re-measured per name; not material) |
| Direction targets N_eff 3.4 | Reproduced |
| Data exists now for EOD | True for 2024-01 on (UDiFF with `UndrlygPric`); 2019-2023 lacks stock spot, as stated |
| Calibrated market is the strongest simple baseline | Not shown; my version lost to the trailing frequency on this window (3) |
| 30 names give about 12 of 17.5 | 10.5 measured (5) |
| G8 functions "apply directly" | `confirmatory_test` and `futility_p` yes; the operative `calibrated_p` thresholds are v4-specific (4) |

## Project rules

No `fno/` code, no order path, no secrets, no write to Drive or NSE (the fetch only reads). Work register row exists
for this builder; no duplicate of another session's work. AGENTS.md roles: the statistician's and risk manager's
angles are covered; the trader's point (forecast skill is not money, must-not-do 8) is right and should stay.

## Addendum 1: re-judge of revision 1 at `0719dd7217e524b9d03e310a9ed2930a6d3a48a3` (judge G)

**Verdict: PASS (design text).** Every finding was accepted and each answer checks out on the data. Three notes
remain, none blocking. The proposal can go to ChatGPT and then to the owner.

### What I re-ran

- I fetched the 700 most recent files the same read-only way (692 sessions exist from 2024-01-01), then ran the
  builder's `extract.py` and `sizing.py` at this SHA. My output **matches `results/2024-01-01_2026-10-14.txt` and
  `results/2024-01-01_2024-12-31.txt` byte for byte** (`diff` empty). Strong evidence.
- Strike rule on the named days: KOTAKBANK 14 Jan 2026, TATAMOTORS 14 Oct 2025, TRENT 4 Jun 2026 and VEDL 30 Apr 2026
  each kept 0.0 of their strikes; KAYNES, POLICYBZR and SBIN on 4 Jun 2024 each kept 1.0. Reproduced.
- The 64 moves of 15% or more left after the rule: I checked each against the same-expiry stock future. All 64 have
  the future moving by the same amount (for example IEX -0.351 vs -0.341, POLICYBZR -0.446 vs -0.433). They are real
  moves, not missed adjustments. 27 of them are 4 Jun 2024. Strong evidence.
- Of the 116 excluded days, 27 move less than 1%: NSE's dividend adjustments and the 2 Mar 2024 special session.
  Excluding them costs a few days and adds no bias, because the rule depends only on the contracts listed and not on
  the move.
- **Dividends the strike rule leaves in (my own check).** From NSE's corporate-action list archived in Drive, there
  are 280 dividend ex-days of F&O names from Sep 2025 to Oct 2026 with data. The rule excluded the 21 that NSE
  adjusts. On the 259 left, Y = 1 on 36% of days, against 27% if the dividend is added back (41% vs 22% where the
  yield is at least half the implied move). So unadjusted dividends do bias the target. But they are about 0.5% of
  name-days, so even a forecaster that knows every ex-date gains under 0.2% of the baseline Brier: an upper bound of
  about 0.05 per day x 259 days / about 47,000 name-days. That is far below the 2-3% skill being sized. Note, not a
  finding (strong evidence on the size).

### Each finding

| # | Revision 1's answer | Re-judge |
|---|---|---|
| 1 (blocking) | Strike-continuity rule: exclude a day when fewer than half of the strikes survive | **Accepted.** Catches the four named actions, keeps the real crashes, and leaves no false 15% move (above). The cross-check against NSE's list is a sound second source |
| 2 | Headline on the realistic pair: about 9 effective bets, range 6-42 | **Accepted.** cal60 vs tilt: rho 0.105, N_eff 9.0, SD 0.0198 (reproduced) |
| 3 | Primary chosen by the lowest Brier on 2019-2025; a claim must also not lose to the other two (reported) | **Accepted.** t values reproduced: +1.65 all names, -1.64 on my window after the rule (my +3.25 was before it), +3.31 on the top 30. No clear winner, so a written rule is right |
| 4 | 0.02 per look everywhere; plain Holm on `confirmatory_test`; no `calibrated_p` and no NIFTY gates | **Accepted**, with note A |
| 5 | Top 30: N_eff 6.1 (realistic pair) or 10.5 (mine); 2% in about 22 months; rule and hybrid families also scored on the 30 | **Accepted** (reproduced) |
| 6 | Worst-year freeze gate on 2019-2025, plus an AR(1) inflation (1 + lag1) / (1 - lag1) | **Accepted.** 2024 is the worst year so far: SD 0.0190, lag-1 0.26, 2% in 21.5 months (reproduced). The inflation is the standard large-sample variance factor for an AR(1) mean, and 5-session blocks fit lag-1 up to 0.26 |
| 7 | The hybrid's rule set is frozen at the freeze | **Accepted** (also must-not-do item 3) |
| 8 | K = 3 recommended, K = 12 the alternative (+30%) | **Accepted.** 22.3 / 17.2 = 1.30 |
| notes | Results-day split; 60-session `cal60`; fetch.py rewritten; NSE calendar for scoring; setup line | Accepted, with note C |

The months claims match the results files: 2% in 17.2 months (K = 3, 0.02 per look), 3% in 7.6, top 30 22.0 and 9.8,
indices 81 and 36. The headline "3% in 8-10 months, 2% in 17-22" spans the whole window and the worst year.

### Notes (no fix required before the owner)

- **A.** `forecast_v4.confirmatory.futility_p` needs a `threshold` argument, the v4-calibrated one that revision 1
  says BR1 does not use. BR1a must state BR1's own futility level, for example a plain p_e at or below 0.025 (the
  same as passing a threshold of 0.025).
- **B.** Dividends below NSE's adjustment threshold stay in the target (above). They are immaterial at this size.
  BR1a may add one line: the dividend effect is measured and reported, not adjusted.
- **C.** The claim "`ruff check` clean on all three scripts" is not quite right: `sizing.py:44` raises SIM115
  (`open` without a context manager) under the repository's `ruff.toml`. `fetch.py` and `extract.py` are clean, and
  all three are formatted. This is a research script outside the gated paths.

### Project rules

This is design text and research scripts only: no `fno/` change, no order path, no secrets, Drive read-only. The BR1
row in the work register belongs to this builder, and nothing duplicates G7, G8, M1, S1 or S6.
