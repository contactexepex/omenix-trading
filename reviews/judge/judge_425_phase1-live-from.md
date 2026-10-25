# Judge 425: phase-1 go-live config (story/phase1-live-from at f37d4869)

**Verdict: PASS (lane 1: schedules and outside services). Merge before 14:33 IST on 22 Oct.**

The change sets `daily.live_from` to "2026-10-22" for `price_distribution`, `price_distribution_scores`,
`price_ranges`, `price_range_scores` and `lab_close`. Everything else stays off: margin_check, weather, forecasts_v4,
card, and E8's `owner_timing_fills`, which has no key at all and so reads None. This is exactly the owner's decision
(DESK_DECISIONS c58788bc: points 1 and 2; E8 off until the first paper approval).

## Checked myself (strong evidence)
- **Gates:** on f37d4869 merged with today's `main` (37864b1b, no conflicts), one run per the owner's new rule:
  - 8,941 passed, 17 xfailed;
  - `ruff check` clean; 1,658 files formatted;
  - imports clean; record scan clean (7,306 files).
- **No test weakened.**
  - The 6 changed tests keep their not-live assertions word for word. They now build from
    `tests/daily/live_dates.py::without_live_dates`, which clears every date, so the rule is tested on its own.
  - `test_steps` pins the five dates to 22 Oct and the rest to None.
  - Moving `lab_close` to 23 Oct fails that pin test.
  - Judge 423's distinct-dates test now starts from the cleared config, so it stays meaningful.
- **Checklist:**
  1. O11's go-live replay is on `main` at 87bd21ce; no `missing("FL1-1")` xfail is left.
  2. `DAILY_RUN_STEPS` ends: card, price_distribution, price_distribution_scores, price_ranges,
     price_range_scores, candles, lab_close. Both score steps run before the lab.
  3. The A7 calendar says 21, 22 and 23 Oct are regular sessions.
  4. `warmup_closes.csv` has 21 Oct's row (22,811.35).
  5. G13b's back-fill (EOD and 3 pm), its BANKNIFTY close table and a scores file have Drive receipts on `main`.
     G13's back-fill was rerun under the new method SHA, as judge 416.1 required.
  6. Criterion 7 is met (judge 422, ruling at 8ad3f959).
- **No false "missing" alerts on day 1.** `lab_close` with `issues_from` = 22 Oct expects no forecast issued before
  that day. 22 Oct's report therefore says "none expected" for its own targets and alerts nothing; the first real
  seal check is for 23 Oct's N1 (judge 422 note on a6396ac3).

## Watch on 22 Oct (not blocking; reasoning only)
- **G13b's score step time on a fresh container's empty cache has not been measured** (judge 423 minor 2; G13's took
  38 s). If it passes O1's 600 s limit, the step fails and is alerted once. `lab_close` then says "scores not ready",
  never a wrong match. Read its time from `journal/runs/2026-10-22.json`.
- **The first 15:45 report holds only today's sealed ranges and an empty scoreboard.** The first N1
  target is 23 Oct (issued 22 Oct), and its close is archived that evening, so the first match appears in the 26 Oct
  report.
  That is the owner's one-session lag, not a fault. Tell the owner, so no one expects a match on 22 or 23 Oct.
