# Judge 401: T1c story text, the card shows the market weather from M1's record (story/t1c-card-weather at 2538c8cd)

**Verdict: PASS on the story text, with 1 minor finding for the code round. Lane 1** (what the owner sees about a
trade). Number claimed with O12's tool.

## Checked myself (strong evidence)
- The card prints "Weather: not yet scored (M1 pending)" on every day (`fno/cards/weather.py:11`): a real defect that
  O11 found.
- `WeatherRecords.path` exists (`fno/weather/records.py:25`), so the path has one source.
- `WeatherColour.NOT_SCORED = "not scored"` (`fno/weather/constants.py:20`): imported, not copied.
- The real record `research/forecasts/v4/weather/2026/2026-10-14.json`:
  - holds `colour` GREEN, `operative` `weather_vix_v1`, `proof`, the `probabilities` of the base rate, v0 and v1 per
    question (0.02 and 0.088 against base rates 0.0267 and 0.104), `v0_colour` AMBER, and `label`
    `backfill_exploratory`;
  - those are exactly the fields the design reads.
- The owner rules the lines quote:
  - "Missing weather blocks new trades" (owner "4 A", `docs/DESK_DECISIONS.md` line 136, "fails closed, like RED");
  - RED blocking new entries (weather thresholds, line 108; M1's `NOT_SCORED` comment, "blocks new trades like RED").
- Privacy: the design never shows `drivers` (criterion 6), consistent with the weather privacy decision (16 Oct: the
  inputs' levels may be shown, but thresholds and private flags are not).

## Assessment
- **Complete for its scope.** Every record state has a line:
  - none, unreadable, or another day: "no reading" plus "no new trades";
  - not scored: "not scored" plus "no new trades";
  - GREEN, AMBER or RED with its chances, base rates, v0 and proof; RED adds its line; back-fills are labelled.
- **Fails closed, never invents a colour.**
- **Simple:** one adapter behind the existing `WeatherSource` port, one wiring line, and dead code removed.
- The out-of-scope items each have an owner: the entry-gate block (its own story), the status reading the weather (T1
  slice B), intraday (LM1).

## Minor 1 (code round)
**The committed back-fill records have no `v0_status`.** M1 writes `v0_status` since today (`fno/weather/day.py:86`),
but the committed records of 13-14 Oct do not have the key (I listed their keys). The design's "Checklist v0: not
scored (<v0_status's reason>)" must handle an older record whose `v0_colour` is "not scored" and has no `v0_status`:
show "not scored (no reason recorded)", never raise. Add it to the boundary tests.
