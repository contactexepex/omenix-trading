# Judge 202: M2 story text, weather alerts and the price of calm (quality rule 1; judge E)

Date: 15 Oct 2026 (UTC). Branch `story/m2-weather-alerts` at **e12240628d0117cf925c4fe987114e9ae136b54b**
(`docs/stories/M-weather.md` M2; claims response 188; register row). Text only.

## Verdict: PASS (story text); 3 notes for the code round

| Check | Status | Evidence (mine) |
|---|---|---|
| Requirements covered | MET | Design 2.3 ("a Slack alert on any upgrade to RED"): the daily upgrade is in; the intraday one goes to LM1 (Out). Design 6.5: DANGER class, a first line saying what to do, a record of the condition with its snapshot and sent times, the owner-delay line, SYSTEM for data problems. REPLAN M2's two parts: (a) built, (b) a port with no number before R1. Each is in Scope or Out with a reason. Few requirements, all mapped, so no separate gap table is needed |
| Reads M1 only through `for_day`; `fno/weather/` untouched | MET | `WeatherRecords.for_day` (`fno/weather/records.py:28`) and `previous_regular` (`fno/weather/wiring.py:82`) exist. `live_colours_before` returns colours without their days, as the text says. `LIVE` and `BACKFILL` are in `fno/forecast_v4_rules/records.py:17` |
| Times against O1 | MET | O1's branch (`story/o1-daily-run`) has `weather` among `LIVE_STEPS`, gated by `daily.live_from.weather` (null), and its story records the `weather_alert` step right after `weather`. The capture refuses from `V4_CAPTURE_START` = 14:30 (`fno/forecast_v4/terms.py:85`), so the alert goes out before 14:30, well before the 15:12 deadline and the card after 15:15. Not via the card, correctly: the card is too late |
| Privacy | MET | The public record holds `drivers.us_move: "private"` only (my read of `research/forecasts/v4/weather/2026/2026-10-14.json`); the real flag is in Drive (`fno/weather/capture.py:47`). M2 reads only the public record; criterion 4 plants a private flag |
| Cannot fire twice on a rerun | MET | An alert record is written once after a sent alert, and a second run says "already alerted". A not-sent attempt writes nothing, so a hand rerun can send it. O1 skips a recorded step on a same-day rerun. Criterion 5 |
| Data failure never shown as danger | MET | `not scored` gives one SYSTEM line naming the missing probability entries, never DANGER |
| Duplicates or contradictions | none | No other story alerts on RED (M1 builder's agreement; my grep of `fno/` finds no RED alert). The price of calm is a port only; R1 owns its source |

## Notes for the code round (not blocking)

1. **The record's real field names.**
   - The text says `p_big_1d` and `p_big_5d`. The record holds
     `probabilities[<operative>].v6_abs_move_2pct_next_session` and `...within_5_sessions` (with `status` and
     `value`), and `drivers.v0_inputs.<name>.{value, reaches}` and `drivers.events_next_5_sessions`.
   - The message must also skip `drivers.us_move` even though it reads "private". Criterion 4's test should assert
     that the key is absent, not only that the Drive plant is.
2. **One duplicate path to state as a Known limit (no code; owner's simplicity rule).** If Slack accepts the alert but
   the alert record's commit then fails, O1's same-day rerun in a fresh container sends it again.
3. **Going live depends on G10's start.** On `main` the capture refuses from 14:30, and today's routine starts at
   14:33 (CLAUDE.md), so `weather`, and with it M2, can only produce live records once the routine moves to G10's
   14:05 start. That belongs to O1 and G10 at go-live; set `daily.live_from.weather` only after it.

**Verdict: PASS for e12240628d0117cf925c4fe987114e9ae136b54b** (story text). Code after O1 merges, as the text says.

---

## Addendum 1 (judge E): f52207f3, the three notes added: PASS

- **Text only.** `git diff origin/main...f52207f3` touches `docs/stories/M-weather.md` only (+8/-2). The other commits
  in the range are `main` merged in.
- **Note 1:** the message reads `probabilities[<operative>].v6_abs_move_2pct_next_session` and
  `...within_5_sessions`, with `probabilities.base_rate` beside them. Criterion 4 now plants a value in the record's
  `drivers.us_move` and in Drive's fake, and requires both to be absent. Matches.
- **Note 2:** a Known limit records that a commit failure after Slack accepted the alert means a hand rerun sends it
  again. Matches.
- **Note 3:** a Known limit records that M2 goes live only after G10's 14:05 start, with `live_from.weather` set after
  it. Matches.

**Verdict: PASS for f52207f3** (story text). It may merge.
