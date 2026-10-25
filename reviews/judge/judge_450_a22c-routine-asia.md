# Judge 450: A22c, the pre-open routine runs one trading-day check, then A22 and A17e part B side by side (story/a22c-routine-asia @ e6010ac0)

Judge F (independent). The change is the CLAUDE.md "Pre-open capture (story A22)" section and one register row.
It meets judge 439's condition that a routine start `global-cues preopen`. Lane 1 (a scheduled routine's text).

## Verdict: PASS. It may merge. 1 minor.

- **Step 2, one trading-day check before anything else.** It uses existing functions only: `is_trading_day`,
  `build_session_calendar` and `now_ist`. I ran its logic on `main`:
  - 22 Oct (regular): True;
  - 8 Nov (muhurat-only): False;
  - 24 Oct (a Saturday): False;
  - 20 Oct (Dussehra): False.
  That agrees with part B's own `nse_session_day` (regular or special, never muhurat) and with A22's
  `is_trading_day` [strong]. A calendar error posts one line and stops, so neither command runs and nothing is
  posted twice.
- **Step 3, both commands side by side.** Each waits for its own windows and commits only its own files, as judged
  in 432 and 439: A22 pushes GIFT at about 08:41 and the day row at about 09:12; part B reads 08:50-09:05 and commits
  then.
- **Step 4.** It covers "alert NOT sent" and "NOT committed" for either command. Values are never posted or
  committed.

**Minor.** "Side by side" in a Claude routine means one command must run in the background, or both, with the
routine waiting for both to end before step 4. Say that in one line, for example: "start `global-cues preopen` in the
background, run `preopen record` in the foreground, then wait for the background one". Otherwise a routine could
run them one after the other, and part B's 09:05 window would close while A22 is still running (to about 09:11).
