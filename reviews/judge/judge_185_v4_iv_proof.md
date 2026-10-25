# Judge 185: v4 implied-volatility proof (GO item 3): `story/v4-iv-proof` d6c834cc (lane 1, test for the freeze)

Judge B. A16/G8 builder. This is the patched-to-raise proof promised in response 157 revision 2 (ChatGPT review 119).
It adds one new test file, `tests/forecast_v4/test_iv_never_used.py`.

## Checks
- **What it does.** One real day (2026-10-15) goes through the real composition roots twice:
  - G7: `build_v4_forecasts(...).records`;
  - M1: `build_weather_days().day`;
  - G8: `build_scoring()` over every question, then `report_json`.

  The second run has `ImpliedVolModel.__init__`/`implied_vol`, `Black76.price`/`underlying`,
  `PanelAtmIv30.__init__`/`estimate` and `AtmIv30Feature.value` replaced by a raise. The outputs compare equal.
  `Black76` subclasses `ImpliedVolModel`, so constructing it is caught too.
- **It is reached and not empty.** A second test shows that `Black76()` and `PanelAtmIv30(...)` raise under the patch.
  The main test asserts that G7 has rows and the weather has v4 rows.
- **My plant.** A `Black76().underlying(...)` call inside G7's `records` (`capture.py`) fails the test. The builder's
  plant was in the weather (M1), so together the G7 and M1 paths are both shown to be guarded.
- **The other half (a grep).** The patch catches calls only, not a stored implied-volatility value read from data. A
  grep of `fno/forecast_v4_rules/`, `fno/weather/` and `fno/forecast_scoring/v4/` finds no `iv`, `iv30`, `atm_iv` or
  `implied` at all. `forecast_v4/units.py`'s `implied_vol` is V4's unit arithmetic, with no estimator. Together they
  are strong evidence that no live v4 output uses implied volatility today.
- **Gates.** The test passes (2 passed, about 10 s, offline, reading committed files only).

## Notes (not blocking)
1. The builder's stated limit is right. V4 (RV5 against weekly ATM IV) uses IV by design and has no code yet. When it
   is built, this proof must leave V4 out, and V4's freeze record must byte-check `iv30.py` and `implied_vol.py`.
2. The guard `plain["g8"]["questions"]` is always true (the report lists every question). The G7 and weather guards
   carry the "not empty" check. Asserting that V6a or V6b is scored would be stronger. Optional.

**Verdict: PASS for d6c834cc.** It belongs in the freeze code. Merge it when `main` is green.
