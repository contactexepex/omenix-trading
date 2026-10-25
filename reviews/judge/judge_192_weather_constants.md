# Judge 192: weather constants split: `story/x-weather-constants` d6724d3a (lane 1)

Judge B. Requested by the E2c builder, with the orchestrator's go. The aim is to bring `fno/constants.py` under the
350-line limit so E4c fits.

## Checks
- **The move is whole and unchanged (89ad2175).** I compared every removed line of `fno/constants.py` with the new
  `fno/weather/constants.py`: all 19 are present, byte for byte.
- **No caller left on the old path.** A grep for every moved name finds no import from `fno.constants` and no
  attribute use. `fno/constants.py` goes from 348 to 329 lines.
- **The method hash (bfbec082).** `weather/constants.py` is added to M1's `METHOD_FILES`. `method_sha256(fno)` uses
  the same algorithm as before (SHA-256 of the files' joined bytes), now named and testable.
  - The new test changes `WEATHER_RED_FLOORS` in a copy and sees the hash change.
  - My plant, dropping the file from `METHOD_FILES`, fails 1 weather test.
  - This closes a real gap the builder states plainly: M1's thresholds were never in its method hash.
- **No code compares method hashes** (grep: no `method_sha256 ==` or `!=` in `fno/`). New live records simply carry a
  new hash, and past records keep theirs.
- **Gates** on d6724d3a (with `main` ace20240 merged), FNO_SLACK_BOT_TOKEN unset: **6,124 passed, 0 failed**. Ruff and
  imports are clean. Weather and learning tests: 97 passed.

## Note for the v4 freeze (not blocking here)
Response 157's byte-check list names M1's `METHOD_FILES` as six weather files. `weather/constants.py` is now a seventh
and must be in the freeze's byte-checked list. It decides the colours and thresholds of V6's rules forecaster. Tell the
A16/G8 builder to add it to the checklist before the freeze commit.

**Verdict: PASS for d6724d3a.**
