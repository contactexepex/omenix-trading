# Judge 129: M1 story text, weather as a scored forecaster: `story/m1-weather-forecaster` 438b8bcec84e5529501a3f43dd8a52c1d244a1d7 (quality rule 1, text only; judge A)

**Number note.** M1 has no response file yet, so I used 129, the next free judge number.

**What I checked:**
- `docs/stories/M-weather.md`, the only change from main 36d2db8;
- response 94's study (`research/2026-10-14-weekly-weather/`);
- T1's weather section (`fno/cards/weather.py`);
- DESK_DECISIONS 15 Oct: "Weather thresholds accepted" and "4 A".

All of it under the owner's 15 Oct rules: real cases only, and "would this change a buy/sell signal, a trade or a stop
decision?".

## The orchestrator's four points (real paths)

**1. The point-in-time 15:00 reading: SOUND.**
- Live v0 reads closes up to `d-1`, plus events announced on or before `d` and dated `d+1..d+5`.
- `VixScaledWeather` uses VIX(`d-1`) for `s_d`, and the same lag for every window session (`s_t` = VIX(`t-1`), target
  `ln(close(t+1)/close(t))`). Each window session must be resolved before the cutoff, through G7's outcomes. The
  forecast and its history are therefore built the same way, with no look-ahead.
- Criteria 4 and 11 carry the look-ahead tests. Criterion 9 makes the capture write nothing after 15:00.
- These inputs reach the repository the evening before (O6's daily closes, e.g. 911555d for 15 Oct). A late O6 run
  gives "missing", which blocks, as the owner chose.

**2. v0's 396 colours from committed files: VERIFIED myself, 396 of 396.**
- I ran response 94's own `weather()` from `study.py` over today's committed `research/data/nifty-panel/warmup_closes.csv`
  and `research/data/events/events.csv`, for every row of `trades.json`.
- Result: **0 mismatches**. Counts: 157 GREEN, 137 AMBER, 102 RED, as the story says.
- Criterion 1 is therefore reachable from committed files today.
- One point for the code round: the study evaluates on the day before entry with events in `(entry, expiry]`, and the
  story's *as of close* mode must use exactly that rule (`study.py:142,163`), not the live mode's `d+1..d+5`.

**3. No US value or flag reaches the repository: SOUND as written, with one line to add (note 2).**
- The cue is read only through A17b's `CueReader`.
- The flag goes to the private Drive part only, and the public record says "US move: private".
- Criterion 7 has a test that greps every repository file, and a no-Drive case where the public record is still
  written.
- Not stated: that the command's printed output never shows the flag. The capture will run on a schedule at v4's
  freeze, so its log is a real output path. See note 2.

**4. "4 A" against T1's card: CONSISTENT.**
- On `main`, `fno/cards/weather.py` shows "Weather: not yet scored (M1 pending)" with "No new trades while the weather
  reading is missing (owner rule)". That fails closed.
- M1's `not scored` blocks "like RED", the same rule.
- M1 leaves T1 unchanged, and enforcement at the desk's entry gate is Out (no strategy is approved).
- So the card keeps blocking after M1 merges, until the follow-up T1 change reads `WeatherRecords.for_day`. That is the
  fail-closed side, consistent with "4 A".

## A real-data check of the model (exploratory, some evidence)

I computed `VixScaledWeather` with the story's rule over the committed history, using regular sessions only and
windows of 750, ending before the cutoff, with at least 500 sessions. I applied the owner's thresholds, with the base
rates from the same windows. This is my approximation of the rule, not the built code. Colours per year:

| Year | GREEN | AMBER | RED |
|---|---|---|---|
| 2019 | 206 | 12 | 12 |
| 2020 | 115 | 50 | 85 |
| 2021 | 217 | 30 | 0 |
| 2022 | 230 | 16 | 1 |
| 2023 | 245 | 0 | 0 |
| 2024 | 226 | 13 | 6 |
| 2025 | 235 | 8 | 4 |
| 2026 to 14 Oct | 160 | 20 | 13 |

- RED runs at 0-5% in normal years. The 250-session RED share passes 15% only around the 2020 crash: its maximum is 34%,
  and 16% of the 250-session windows are above 15%. Today's share is 5.2%, and the last five sessions are GREEN.
- So `over_alarming` would mark the crash and little else.
- That supports decision 71's reason: v0 was RED on 26% of response 94's weeks. This is exploratory, on the spent
  period, as the story itself labels the back-fill.

## Other checks

- **Thresholds.** RED is `max(0.10, 2.5 × b1)` / `max(0.35, 2.5 × b5)`, and AMBER is `max(0.06, 1.5 × b1)` /
  `max(0.20, 1.5 × b5)`. These are exactly the owner's accepted figures (DESK_DECISIONS 15 Oct, line 108).
- **Rule 9** is stated, with the owner's test. Decision 71 is marked for the owner to confirm.
- **Engineering.** The design has one strategy interface and one composition root, and reuses G7 and A17b with no
  copy. The dependency on G7's code is stated, and the code waits for it.

## Notes (one line each; none changes a probability, colour or block, so none is a finding)

1. Define `d-1` and `t-1` as the previous **regular** session, as V6 counts. A muhurat or a special Saturday session,
   both real yearly cases, then never supplies the VIX close.
2. Criterion 7: also "the command's printed output never shows the US flag or value". The capture's log will be a
   scheduled job's output.
3. Criterion 1: the *as of close* mode uses the study's event window `(entry, expiry]` from the day before entry, as
   `study.py` does.

### Verdict: PASS for 438b8bcec84e5529501a3f43dd8a52c1d244a1d7 (story text)

- **No should-fix.**
- **v0's reproduction is verified from committed files** (396 of 396). The point-in-time rule and the private-flag rule
  are sound, and "4 A" is consistent with T1's card.
- **The three notes** are one-line text additions.
- **Next:** ChatGPT's rule-9 review. The code waits for G7's merge.

## Addendum 1 (15 Oct 2026): M1 code at a47e529b43ed3cbb0266fb785bfb1acf313a8172 (code 4a317be plus main; claims `response_139_m1-weather.md`, renumbered from 137)

**Gates, run myself on the exact SHA:**
- `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q`: **5504 passed**;
- `tests/weather`: 67 passed;
- `ruff check fno tests tools`, `ruff format --check fno tests tools` and `python tools/check_imports.py`: clean.

**Merge with origin/main 22c4bb0.** `git merge-tree` finds one conflict, in `reviews/claude/README.md`, the index rows.
Keep both; no code conflicts.

### Real-path checks I ran myself

1. **The probabilities, recomputed independently.** I wrote my own implementation from the story's rule: regular
   sessions only, `s_t` = VIX of the previous regular session, a 750-session window resolved before the cutoff, and
   2%. I ran it on the committed `warmup_closes.csv` and compared every figure with the built `WeatherDays`.

   | Day | p1 | p5 | b1 | b5 | Colour (model / v0) |
   |---|---|---|---|---|---|
   | 15 Oct 2026 (today) | 0.022667 | 0.096 | 0.026667 | 0.104 | GREEN / AMBER |
   | 14 Oct 2026 | 0.02 | 0.088 | 0.026667 | 0.104 | GREEN / AMBER |
   | 4 Jun 2024 (election result) | 0.068 | 0.294667 | 0.029333 | 0.112 | AMBER / RED |
   | 23 Mar 2020 (crash) | 0.554667 | 0.985333 | 0.033333 | 0.096 | RED / RED |

   - **All 16 figures are equal** to six decimals.
   - **The colour by hand, 4 Jun 2024.** It is not RED: `p1` 0.068 < max(0.10, 2.5 × 0.0293) = 0.10, and `p5` 0.2947
     < max(0.35, 0.28). It is AMBER: 0.068 ≥ max(0.06, 0.044).
   - **The claims' "today GREEN, p1 0.0227, v0 AMBER" reproduces.**
2. **Look-ahead.** I rebuilt `WeatherDays` with every close × 1.07 and every VIX × 2 from 1 Oct 2026 on:
   - the forecasts and colours for 30 Sep and **1 Oct** are unchanged (1 Oct uses closes up to 30 Sep);
   - 2 Oct changes, as it should.
3. **v0's 396 days.** `test_as_of_close_reproduces_all_396_colours_of_response_94` runs in the suite and passes. My own
   run of `study.py` gave 396 of 396 (the text round).
4. **Privacy.**
   - The private document is `{"day", "us_move"}`, written only through `store.put` to the Drive derived area.
   - The public record's driver is `"us_move": "private"`.
   - `capture_weather`'s printed lines are the colour line, the row count and "private part (NOT) saved". A Drive error
     is named by type only.
   - The CLI never prints the flag.
   - The branch commits no weather record.

### The orchestrator's six choices

| Choice | Ruling | Why |
|---|---|---|
| Stale closes → refused, so missing, so trades blocked | **Right** | If O6's closes do not end at the previous regular session, the model would use an older VIX for "today". Refusing is the owner's "4 A" fail-closed rule, and the line names both dates. Real path: a late O6 run; it blocks until the next capture |
| The event window counting a Sunday Budget | **Right** | `d < event ≤ 5th regular session after d` takes 1 Feb 2026's Sunday budget session (A7 lists it as a special session). A budget lands on the next regular session's prices, which is why it is a v0 event |
| 1e-12 in the colour comparison only | **Right** | `1.5 × 0.20 = 0.30000000000000004` is real floating-point error. Shares move in steps of 1/750 ≈ 1.3e-3, so 1e-12 cannot lift a share that is truly under. It is confined to `colour.py` |
| `made_at` in UTC | **Right** | The story says "UTC with offset". `astimezone(UTC).isoformat()` gives `+00:00` |
| `method_sha256` over G7's `series.py`, `baselines.py`, G6's `terms.py` and five weather files | **Right, with one gap (note 1)** | It covers the arithmetic. Two inputs of v0's colour are outside it: `forecast_v4/sessions.py` (`next_scored_sessions`, the event horizon) and `weather/wiring.py` (`HORIZON = 5` and the scheduled-event filter). An edit there would move v0's probabilities without a new method hash |
| A 6-line copy of G7's `_prefix_hashes` | **Accept** | Moving it would change G7's hashed `capture.py`, and with it G7's method identity, for 6 lines. That costs more than the duplicate. It is audit hashing only, never a probability |

### Notes (one line each; none changes a probability, colour or block)

1. Add `forecast_v4/sessions.py` and `weather/wiring.py` to `METHOD_FILES`, or move `HORIZON` and the event filter into a
   hashed file, so the method hash covers every input of v0's colour.
2. `capture_weather` computes the day's values twice (`colours(d)` for the RED share, then `day()`). That is a
   performance point only.

### Verdict: PASS for a47e529b43ed3cbb0266fb785bfb1acf313a8172

- **What holds:**
  - the probabilities are reproduced independently on four real days (16 of 16);
  - look-ahead is clean;
  - v0 reproduces 396 of 396;
  - the US flag is Drive-only and never printed;
  - all six choices are sound.
- **Two notes only.** ChatGPT's rule-9 review was made on the text (review 106).
- **Merge:** keep both README rows.

## Addendum 2 (15 Oct 2026): merge check, b29ac33a8e334aac40dfff00948aa6548a19e78b (`--no-ff` of 223de56 onto c16ca37)

| Check | Result |
|---|---|
| Branch since my PASS (a47e529..223de56) | Note 1 is applied: `METHOD_FILES` adds `weather/wiring.py` and `forecast_v4/sessions.py`, with a test in `test_privacy_and_point_in_time.py`. The response file is renumbered. Everything else is main merged in. Accepted: it is exactly note 1 |
| Recomputed merge equals the merge commit | **MET, with a stated resolution.** `git merge-tree --write-tree c16ca37 223de56` gives ea224fb… with one conflict (`reviews/claude/README.md`). The merge's tree 8b05f8a… differs from it only in that README's resolution and the rename `response_138_m1-weather.md` → `response_139` (138 was taken). Both are lane 3 |
| Branch files identical | **MET.** `fno/weather/`, `tests/weather/`, `fno/cli.py`, `fno/constants.py` and `docs/stories/M-weather.md` are identical in 223de56 and b29ac33 |
| CI on `main` | **NOT MET, and not caused by M1.** Every `checks` run on `main` since **72ffc31 (09:11 UTC, the R2 merge)** fails at collection: `research/2026-10-15-r2-stock-options-results/r2study/reading.py:9` has `from itertools import batched`, which exists only from Python 3.12, and CI runs Python 3.11 (`.github/workflows/checks.yml:23`). Locally (3.13) it passes, which is why the gates of every story since looked green. Run 38731620537 (f97a901) shows the error |

**For the orchestrator:**
- **The root cause:** R2's `reading.py` uses a 3.12-only standard-library function, while CI and the declared Python are
  3.11.
- **The fix,** one of:
  - replace `batched` with a 3-line generator in `reading.py`;
  - or decide the project's Python version and change CI to it.

  Either way, re-run CI on `main`. Every merge since 72ffc31 has gone in on red CI, and that has to be visible.
- **Rule 8** (`weather capture` after the cutoff writes nothing, as designed) is accepted. My independent recompute in
  addendum 1 is the real-data record.

### Merge check: MET for M1's own parts; main's CI is red for an R2 cause, reported above

M1 is done once main's CI is green again on a tree containing b29ac33. I will confirm that when the R2 fix lands.

## Addendum 3 (15 Oct 2026): M1 merge check closed

- **CI on `main` is green on trees containing b29ac33.** `checks` run 38743169675 on c791051 succeeded, as did
  38743349971 (8aca45d) and 38743424608 (73b488a).
- **What fixed it:** the Python 3.13 change (judge 137, merged at 7d98370) and the lane-2 test fixes in c791051.
- Addendum 2's other two checks were already MET.

**M1 is done.**

## Addendum (judge C, 15 Oct 2026): decision 71's wording at 70ffff1dd6190a826215ad741892a1586811555b

`story/m1-decision71-text` is one commit on `main` 65ec7c76: 3 files, 5 lines, text and a comment only. It is lane 1
because of its path.

| Check | Status | Evidence |
|---|---|---|
| The owner's confirmation exists | MET | `docs/DESK_DECISIONS.md:173`, 15 Oct 2026: "**Market weather: the model's colour (weather_vix_v1) is operative, labelled not yet proven** (owner: \"New model, 'unproven'\")", confirming decision 71 with the fall-back to v0 |
| No value changes | MET | `fno/constants.py:317` drops only "(owner to confirm)" from the comment. `WEATHER_OPERATIVE_MODEL = WEATHER_MODEL_VIX` and `WEATHER_OPERATIVE_PROVEN = False` are unchanged |
| No method hash moves | MET | M1's `METHOD_FILES` (`fno/weather/wiring.py:28-32`) lists weather/*, `forecast_v4_rules/series.py`, `baselines.py` and `forecast_v4/terms.py`, `sessions.py`; `fno/constants.py` is not among them |
| Text | MET | `M-weather.md:72` and `:252-254` and `response_139:17` now say "owner confirmed, 15 Oct 2026 (docs/DESK_DECISIONS.md)" |

The builder's gates (5,565 passed) are accepted without a rerun: no code value changed.

**Verdict: PASS for 70ffff1dd6190a826215ad741892a1586811555b.**
