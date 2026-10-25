# Judge 231: P2, the re-pin to contract 2.10.0, `weather_history` chances and the `forecast_history` page

Head `story/p2-contract-2-9` at 9c8c41adfe6e1bfcbcc22c2a2358b394fb8c7037 (P2 builder 013xqaNTCbSBytKgqpfaYFqZ;
claims: response 234, addenda 1 and 2). It supersedes 75133fc3 and fe47474b, which were skipped on the
orchestrator's request. Lane 1: it publishes pages and moves the pinned contract. Judge D, 16 Oct 2026.

**PASS.**

| Criterion | Result | Evidence |
|---|---|---|
| The pin is the judged 2.10.0 contract | MET | `pin.json` names dashboard 38dfee63 and contract version 2.10.0. Every one of the 37 pinned `api/` files is byte-identical to `git archive 38dfee6 api` (`diff -rq` lists only the unpinned README, catalog, paths and .gitkeep). `git diff 38dfee6 f4f7f40 -- api` is empty, so the pin also matches dashboard main. |
| `weather_history` chances are read from the record, never computed | MET | `chances()` calls the existing `figure()`, which returns `value` when `status == "ok"` and None otherwise. The operative model is `WEATHER_OPERATIVE_MODEL` (weather_vix_v1) and the yardstick is `base_rate`. The test re-reads each of the 2,409 record files and compares all four fields per row. The real data has 2,010 non-ok entries, all with `value: null`, so the null path is exercised. Still never sent: `reaches`, `us_move`, `v0_inputs`, `drivers` (test). This follows the owner's decision ad562ca1. |
| `forecast_history` points are G4's own figures | MET | Each point is (`as_of`, `primary.scored`, `primary.mean_brier`) taken from one committed report under `research/forecasts/scores/`. A point needs `scored >= 1`. The test re-derives every point from the three real reports. |
| Live and back-fill never join | MET | `live_1500_proxy` maps to `live` and `close_proxy` to `backfill_exploratory`. The mode is part of the series key. A live series' `backfill_sha256` is None by construction (test). |
| No series spans a back-fill rebuild | MET | The back-fill series key includes the report's `inputs.backfill_sha256`. The sort is stable on (forecaster, mode), so a later file comes after the earlier one. The planted-rebuild test (a fourth report with a new hash) gives two series: the old three points and the new one. **My mutation:** dropping the hash from the key fails two tests (the rebuild test and the one-series-per-key test). All three real reports carry the same hash, 5b9d4306…, of the frozen `backfill_v1.csv.gz`, which was last changed on 13 Oct. |
| A bad report stops the build, named | MET | `ScoreReportsReader` parses every file dated on or before the session, and a file that fails to parse raises. A missing folder gives the empty page (test). |
| No duplicate of other work (WORK_REGISTER) | MET | The row is P2a-h's own and is updated; it adds one BlockBuilder and one reader in the existing composition root, `fno/market_read_models/wiring.py`. |
| Gates on the exact SHA | MET | `pytest -q -n auto` 6931 passed (with the Slack token unset), ruff check and format clean, check_imports clean. |
| Trial merge with main | MET | It merges cleanly with main (WORK_REGISTER and reviews README auto-merged). 6940 passed. |

**Notes (not blocking):**
- The two real-data tests key series by (question, label, forecaster), without the hash. On the first real back-fill
  rebuild they will fail even though the page is right. The back-fill is frozen, and a rebuild needs a recorded
  decision, so this is a loud failure on a rare event, not a wrong page. Add the hash to their key when touching them.
- `open_risk_cap` is in the pinned paper-trades schema but no page builds `paper_trades` yet. P2c must fill it from
  `profile.open_risk_cap_rs` (already read in the wiring for the home books), never typed (judge 224 addendum 3).
- My second mutation (reading `value` without the status guard) left the tests green, because non-ok entries
  already carry `value: null` in all 2,409 records. The guard is a belt-and-braces check, not an untested path.

## Addendum 1: head 808fee92 (pin commit moved to dashboard main f4f7f40)

**PASS.** `git diff 9c8c41ad 808fee92` changes only `pin.json`'s `commit` (38dfee63 to
f4f7f404537d0d31f1dd4a3f2539550e101515b5, the full SHA of dashboard main) and response 234 addendum 3. The file hashes
and `contract_version` 2.10.0 are unchanged. `git diff 38dfee6 f4f7f40 -- api` is empty, so the pinned bytes are still
main's. A trial merge with trading main (acbb4cef) merges cleanly: `pytest -n auto` 6940 passed, ruff clean,
check_imports clean.

## Addendum 2: head 5f9457e1 (the note on the real-data tests acted on)

**PASS.** `git diff 808fee92 5f9457e1` touches only `tests/market_read_models/test_forecast_history_page.py` and
response 234 addendum 4. Both real-data tests now key each series by (question, label, forecaster, backfill_sha256),
with None for live, so a real rebuild no longer collides two series. The page code is unchanged. On 5f9457e1 the
file's 4 tests pass and ruff check and format are clean.
