# Judge 591: G7b completion text, W3 decided and W8 proposed, `story/g7b-completion` at 5caa04e0c (round 1 of 2, judge K)

**FAIL, lane 1, text only.** 1 should-fix, 2 minor. I judged the text changes 915f276d9..5caa04e0c by reading; the
code at 915f276d9 is left for the next code slice. Doc-reading tests on 5caa04e0c, run with the Slack token set:
853 passed, 15 xfailed.

## Checks

| Item | Verdict | Own evidence |
|---|---|---|
| W3: both yardsticks as two labelled rows (A `premium_adjusted_implied_intraday`, B `premium_adjusted_implied`); V2/V3 close-proxy series keep B only | MET | the owner's words are on main (c63eb7e0b; DESK_DECISIONS 24 Oct "W3: both yardsticks": "I want both intraday and daily closes"). B only for V2/V3 matches protocol 3.2. Criterion 4's plants (pooled, unlabelled, back-fill overriding a live day) fit |
| W8's numbers | MET | I recomputed them from the committed rows: back-fill / live `RV_s` = 0.962 (19 Oct), 0.997 (21 Oct), 1.009 (22 Oct), mean 0.989. 16 and 23 Oct are void live, and 23 Oct has no A16b row. Live `basis_counts` = `candle_1m_close:25;candle_1m_open:1`. A16b holds 695 sessions from 2024 (685 ok, 10 void) and 1,685 in all |
| Is the evidence enough to *propose* W8? | yes, as "some evidence" | Both series use the same formula on the same 26 marks plus the overnight return. A16b's step 0 found 15-minute and 1-minute closes equal (75 of 75). The 3 live days agree within 4%, and the paired drift line watches every later day. It is not enough to call the two measures equal, and the text does not claim that. The owner decides |
| m3 rewording | MET | Known limits now quotes 585 m3's rule as written ("days whose monthly is in 2027") |
| s1 | MET | the W3 owner row names `fno/forecast_v4_rules/intraday_series.py` |

## Findings

1. **Should fix: W8 says "decision 56 unchanged", but it narrows how decision 56 has been read here.**
   - Decision 56 (response 113): back-filled rows "never count as live forecast inputs".
   - This story's own G7 text (G-forecasts.md, the V1 HAR rule, about line 297 on main) says A16b rows "never count toward 20, 250 or **any live input**".
   - Under W8, a live V1 / part f row of yardstick A gets its scale from a ratio fitted partly on A16b rows. That is a live input built from back-filled rows.
   - The step is defensible: the ratio is a baseline's scale, its points resolve before the refit, and the EOD IV30 proxy is the same "point in time by content" precedent (3.1). A baseline fitted with hindsight would, if anything, make forecasters look worse, not better.
   - But the owner must see the change, not "unchanged". **Fix:** say plainly that W8 reads decision 56 as "never a forecast input, outcome or base rate". Say that a baseline's ratio window may use back-filled rows, labelled `backfill_window`. Give the reason in one line. Note that the G7 "any live input" line gets the same exception, and add this to W8's owner row.

## Minor

- **m1:** "A16b's step 0 found the 15-minute closes equal A16's live levels on 75 of 75 marks" is not what step 0 measured. Step 0 compared 15-minute candle closes with 1-minute candle closes, on 13 Oct, 14 Oct and 1 Sep 2026, before A16 went live on 16 Oct (`A16b-candle-backfill.md:56-59`). A16's live marks are 1-minute closes, so the conclusion carries. But say what was compared, and say that no 2024-25 day (W8's window years) was checked.
- **m2 (suggestion):** W8's text could name what happens if the paired line moves. For example: the owner reviews W8 if its median leaves [0.95, 1.05] over 20 live days. Otherwise the drift is only printed. Optional, the owner's call.

## Plants

None: text round.

## For round 2

The should-fix is a wording fix only: no new data is needed, and the numbers above stand.

## Notes

- Scope: only 915f276d9..5caa04e0c in `docs/stories/G-forecasts.md` (73 lines changed); no code was read for this verdict.
- Pilot-mode rule (69d75ac1c): the doc tests ran with the token set; no test posted to Slack (none of these tests posts).
- W8 is a protocol wording for the owner. My "enough to propose" covers only that the evidence is honestly labelled and adequate for the owner to decide; it is not a ruling that W8 is right.

## Addendum 1: W8 decided by the owner (DESK_DECISIONS fa605291a, "W8 - yes"), same head 5caa04e0c

**FAIL stands, with the should-fix reduced to text consistency.**
- **The substance is decided.** The owner's row states the narrowed reading in its own words: A16b's rows go into the ratio window, labelled `backfill_window`, "never a forecast input, outcome or base rate". So the owner saw and approved what SF1 asked to be shown. Judged as decided, W8's protocol text is clear, carries its labels and drift line, and needs nothing more.
- **What is left (still should-fix, wording only):** the story text now contradicts itself.
  - W8's bullet says "decision 56 unchanged".
  - The G7 V1-HAR rule still says A16b rows never count toward "any live input" (G-forecasts.md, about line 297).
  - A builder or judge following that line would refuse yardstick A's live rows. Fix in round 2:
    - W8's row and bullet cite the owner's row (fa605291a);
    - "unchanged" becomes "decision 56 read as never a forecast input, outcome or base rate (owner, 24 Oct)";
    - the G7 line gets the same exception, "except a baseline's ratio window, W8".
- m1 and m2 are unchanged (minor).

## Addendum 2: round 2, `story/g7b-completion` at 3033da0c9 (judge K)

**PASS, lane 1, text only.** The round-2 delta 5caa04e0c..3033da0c9 touches only `docs/stories/G-forecasts.md` (42
lines); the branch's code is left for the next code slice. Doc-reading tests on 3033da0c9, run with the Slack token
set: 853 passed, 15 xfailed.

| Item | Verdict | Evidence (read) |
|---|---|---|
| SF1, the three edits | fixed | W8's bullet, row and wording cite the owner's row fa605291a; "decision 56 read as never a forecast input, outcome or base rate (owner, 24 Oct)" replaces "unchanged"; the G7 V1-HAR line now ends "except a baseline's ratio window, W8"; a "How decision 56 is read" bullet states the narrowing and its reason plainly. No contradiction is left |
| m1 | fixed | step 0 is now described as 15-minute against 1-minute closes on 13 Oct, 14 Oct and 1 Sep 2026, before A16 went live, with no 2024-25 day checked ("some evidence only for those years") |
| m2 | fixed | trigger: the median over the latest 20 live days outside [0.95, 1.05] gives one alert and an owner row; fewer than 20 paired days give nothing |
| Extra fix: B's level line is a ratio of means | **accepted** | My own figures from the committed rows (19, 21, 22 Oct: live `RV_s` against the squared close-to-close returns from `warmup_closes.csv`): daily ratios 1.23, 9.91, 4.09; median 4.09, mean 5.08; ratio of means 2.34, as the builder says. A day's close proxy is one squared return, so it is noisy and can come close to 0. A mean or median of daily ratios is then dominated by quiet-close days and overstates the gap. The ratio of the means estimates the level ratio consistently (reasoning only, standard). The W8 drift line keeps a median of daily ratios. That is acceptable: both of its sides are intraday measures of the same day, near 1 and low in noise (0.96-1.01) |

- **Note for the desk (some evidence, 3 days only):** the live intraday `RV_s` ran at about 2.3 times the close-proxy level on 19-22 Oct. Three days cannot separate a measure gap from chance (single squared returns). It is the line that yardstick B prints, so the level gap will be watched, not assumed.
