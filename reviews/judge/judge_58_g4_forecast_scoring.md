# Judge 58: story G4, forecast scoring and reports

Date: 13 Oct 2026 (UTC). Claims: `reviews/claude/response_66_g4.md` (a2d44ce). Code: `fno/forecast_scoring/`.
Holdout rule kept: I read no 2019-2023 row of the golden file or the back-fill (my script drops back-fill lines dated
before 2024-01-01 by their date text before parsing, as the builder's code does).

## Verdict: PASS

Every criterion is met and I reproduced the "judge verifies" step exactly. Three follow-ups for G5 (below) are not
G4 defects today, because no AI-book record exists yet, but they must land before Books 2 and 3 are scored.

## Per criterion

| # | Criterion | My check | Result |
|---|---|---|---|
| 1 | Brier and log score match hand values; clipping applied | Read `scores.py`: Brier `(p-o)^2`, log score clipped to [0.01, 0.99], 10 fixed bins with 1.0 in the last bin (I checked `calibration_bin(k/10)` for k = 0..10: 0..9, 9, no float slip at 0.3 or 0.7). Test passes | MET |
| 2 | Block bootstrap with the fixed seed reproduces a committed interval exactly | Read `block_bootstrap.py` against protocol section 8 line by line: `SeedSequence([20261013, k])`, starts uniform on `0..n-L` (`integers(0, n-L+1)`), ceil(n/L) blocks in draw order, cut to n, p = (1+#)/(B+1), fewer than 40 dates not tested with p = 1, Holm step-down stops at the first failure. Planted `n-L` for `n-L+1`: caught (1 failed) | MET |
| 3 | Never scored before its target is resolvable | Planted two breaks: closes read 4,000 days past the as-of day (caught), and "pending" relaxed by 30 days (caught). Live records need the capture receipt's hashes; without Drive credentials they stay unverified | MET |
| 4 | Every report says forecasts are secondary to net profit | The committed report's `standing` and `confirmatory_note` say so; all 10 primary rows have `holm_significant: null`, `tested: false`, p = 1 (Books 2 and 3 do not exist) | MET |

**Judge verifies (one book's Brier for one month), done independently** from `warmup_closes.csv`, the NSE session
calendar (weekdays minus holidays plus special sessions, muhurat left out) and the back-fill's 2024+ rows:

| Book 1 | My count | My mean Brier | Report |
|---|---|---|---|
| Q1 up in 20 days, whole period | 669 scored, 19 pending | 0.24413691833020523 | 0.24413691833020523 (669 / 19) |
| Q2 moves 3% in 20 days, whole period | 669 scored, 19 pending | 0.2309899286283313 | 0.2309899286283313 (669 / 19) |
| Q1, March 2025 only | 19 | 0.2012 | (report has no monthly means) |
| Q2, March 2025 only | 19 | 0.2709 | (report has no monthly means) |

The whole-period values agree to every printed digit, so the resolver, the calendar offsets and the pending rule
agree with my independent code.

## Claims vs reality

| Claim | Reality |
|---|---|
| G4 had to live outside `fno/forecast/` because of the v2 freeze | True: the freeze test covers every `.py` there, and `baseline_wiring.py` is byte-checked. A sound reason, not an excuse |
| Report byte-identical on re-run | Not re-run by me (cost); the shape is sorted-key JSON. Not verified |
| Outcomes come from the official closes, same values as the panel's | I used the same closes file, so my match does not test this claim. Not verified |
| Four interpretations | (1) Q5's live outcome from the panel IV30: agree, v1 section 3 defines IV30 from the panel and v2 keeps outcomes. (2) Linear percentiles: acceptable, the protocol is silent and the docstring states it. (3) Closes file: fine. (4) Holdout: the drop-by-date-text matches my own approach |
| `protocol_v2_commit` | `null` in the committed report because no live day exists yet; it is filled when live files exist. Correct, but a reader may think v2 is not frozen; it is (ab2e811) |
| Results table (Book 1 vs base rate) | Not recomputed; descriptive only and labelled so |

## Needed before Books 2 and 3 are scored (G5 follow-ups, not G4 failures today)

1. G4 reads only `research/forecasts/live_v2` live files and the back-fill. The AI books write to
   `research/forecasts/ai_v1/`, so nothing scores them yet, and nothing in G4 honours their audit statuses
   (`model_mismatch`, `exposed`, a transcript breach).
2. G5 criterion 3 (coverage in G4's report) and the owner's isolation label ("sealed same day (not full F1)") are not
   in the report. See judge 62.
3. `COMMON_START = None` is a hand-edited constant. Someone must set it when the AI books' first counted day exists;
   until then the six-month gate cannot start.

## Project rules

Files under 350 lines (largest 131); new package with its own composition root, listed in CLAUDE.md; constants
named; no AI at runtime in the workflow; Slack only to #fno-desk with `FNO_SLACK_BOT_TOKEN`. Full suite at ea4459f: 1,702 passed; ruff and imports clean (my run).
